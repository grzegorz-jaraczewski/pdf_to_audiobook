from datetime import timedelta

from django.core.files.base import ContentFile
from django.db import models, transaction
from django.utils import timezone

from jobs.services.audio_assembler import merge_mp3_chunks


class Job(models.Model):
    """
    Represents a PDF-to-audiobook job.

    Attributes:
        pdf_file: Uploaded PDF to process.
        status: Current job status (Pending, Processing, Completed, Failed).
        error_message: Description of any chunk or job errors.
        assembled_at: Timestamp when the job audio was fully assembled.
        output_file: Final combined audio file (MP3) of all chunks.

    Methods:
        update_status_from_chunks(): Updates job status based on chunk statuses.
        can_assemble(): Returns True if all chunks are complete and job can be assembled.
        assemble(): Combines completed chunk audio into a single output file.
    """
    class Status(models.TextChoices):
        """
        Defines possible processing states of a Job.

        Choices:
            PENDING: Job is waiting to be processed.
            PROCESSING: Job is currently being processed.
            COMPLETED: Job has been successfully processed and audio is ready.
            FAILED: Job processing failed after max retries.
        """
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    pdf_file = models.FileField(upload_to='uploads/')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assembled_at = models.DateTimeField(null=True, blank=True)
    output_file = models.FileField(upload_to='audio/jobs/%Y/%m/%d/', null=True, blank=True)

    def update_status_from_chunks(self):
        """
        Recalculates the job's status from its chunks.

        - PENDING if no chunks exist.
        - FAILED if any chunk failed (error from first failed chunk is used).
        - COMPLETED if all chunks are completed.
        - PROCESSING otherwise.

        Saves changes to the database.
        """
        total = self.chunks.count()
        completed = self.chunks.filter(status=Chunk.Status.COMPLETED).count()
        failed = self.chunks.filter(status=Chunk.Status.FAILED)

        if total == 0:
            self.status = self.Status.PENDING
            self.error_message = ""

        elif failed.exists():
            self.status = self.Status.FAILED
            self.error_message = failed.order_by('index').first().error_message

        elif completed == total:
            self.status = self.Status.COMPLETED
            self.error_message = ""

        else:
            self.status = self.Status.PROCESSING
            self.error_message = ""

        self.save()
        return

    def can_assemble(self):
        """
        Determine if the job is ready for final audio assembly.

        Returns True if:
          - assembled_at is None
          - All chunks exist and have status COMPLETED

        Returns False otherwise.
        """
        if self.assembled_at is not None:
            return False
        if not self.chunks.exists():
            return False

        return not self.chunks.exclude(status=Chunk.Status.COMPLETED).exists()

    def assemble(self):
        """
        Atomically merge all completed chunk audio into a single MP3 file.

        - Uses select_for_update to prevent concurrent assembly.
        - Skips if job already assembled or not ready.
        - Saves the output to output_file and updates status/assembled_at.

        Safe to call repeatedly or from multiple workers.
        """
        with transaction.atomic():
            job = Job.objects.select_for_update().get(pk=self.pk)

            if job.output_file:
                return

            if job.assembled_at is not None:
                return

            if not job.can_assemble():
                return

            completed_chunks = job.chunks.filter(status=Chunk.Status.COMPLETED).order_by("index")
            audio_bytes = merge_mp3_chunks(completed_chunks)

            job.output_file.save(
                f"job_{job.id}.mp3",
                ContentFile(audio_bytes),
                save=False,
            )
            job.status = job.Status.COMPLETED
            job.assembled_at = timezone.now()
            job.save(update_fields=['status', 'assembled_at', 'output_file'])

    def __str__(self):
        """
        Human-readable representation of the job.
        Format: "Job {index} - status".
        """
        return f"Job #{self.id} - {self.status}"


class Chunk(models.Model):
    """
    Represents a chunk of text from a PDF-to-audiobook job.

    Attributes:
        job: ForeignKey to the parent Job.
        index: Sequential position of the chunk within the job.
        text: Text content of the chunk.
        status: Current processing status (Pending, Processing, Completed, Failed).
        error_message: Description of any error encountered.
        started_at: Timestamp when processing started.
        retry_count: Number of retries attempted.
        max_retries: Maximum allowed retries for this chunk.
        audio_file: Generated audio for the chunk (MP3).

    Methods:
        mark_processing(): Mark chunk as PROCESSING and set started_at.
        mark_completed(): Mark chunk as COMPLETED (requires audio_file).
        mark_failed(error_message): Mark chunk as FAILED or retry if under max_retries.
        recover_stuck_chunks(timeout): Reset stuck chunks to PENDING and return affected job IDs.
        claim_next_chunk(job): Atomically claim the next PENDING chunk for a job.
    """
    class Status(models.TextChoices):
        """
        Defines possible processing states of a Chunk.

        Choices:
            PENDING: Chunk is waiting to be processed.
            PROCESSING: Chunk is currently being processed.
            COMPLETED: Chunk has been successfully processed and audio is ready.
            FAILED: Chunk processing failed after max retries.
        """
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='chunks',
    )

    index = models.PositiveIntegerField()
    text = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    retry_count = models.PositiveIntegerField(default=0, null=False, blank=False)
    max_retries = models.PositiveIntegerField(default=3, null=False, blank=False)
    audio_file = models.FileField(upload_to="audio/chunks/%Y/%m/%d/", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["job", "index"], name="unique_chunk_per_job")
        ]
        ordering = ['index']
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["job", "index"])
        ]

    def chunk_audio_upload_path(instance, filename):
        """
        Return the upload path for a Chunk's audio file.

        The file will be stored under a directory for its parent Job,
        named as `chunk_<index>.mp3`.

        :param instance: Chunk instance
        :param filename: Original filename (ignored)
        :return: Relative path for storing the audio file
        """
        return f'audio/job_{instance.job.id}/chunk_{instance.index}.mp3'

    def mark_processing(self):
        """
        Transition the chunk from PENDING to PROCESSING.

        Sets started_at to current time and clears previous error_message.
        Raises ValueError if the chunk is not currently PENDING.
        Saves changes to the database.
        """
        if self.status != self.Status.PENDING:
            raise ValueError(
                f"Cannot mark Chunk {self.id} as PROCESSING from status {self.status}."
            )
        self.status = self.Status.PROCESSING
        self.error_message = ""
        self.started_at = timezone.now()
        self.save(update_fields=["status", "error_message", "started_at", "updated_at"])

    def mark_completed(self):
        """
        Transition the chunk from PROCESSING to COMPLETED.

        Requires a valid audio_file. Clears error_message.
        Raises ValueError if chunk is not PROCESSING or audio_file is missing.
        Saves changes to the database.
        """
        if self.status != self.Status.PROCESSING:
            raise ValueError(
                f"Cannot mark Chunk {self.id} as COMPLETED from status {self.status}."
            )

        if not self.audio_file:
            raise ValueError(
                f"Cannot mark Chunk {self.id} as COMPLETED without audio_file."
            )
        self.status = self.Status.COMPLETED
        self.error_message = ""
        self.save(update_fields=["status", "error_message", "updated_at", "audio_file"])

    def mark_failed(self, error_message: str):
        """
        Mark the chunk as FAILED or retry as PENDING based on retry_count.

        - If retries remaining, sets status back to PENDING.
        - If max retries exceeded, sets status to FAILED and stores the error message.
        Raises ValueError if attempting to fail from an invalid state or missing error message.
        Saves changes to the database.
        """
        self.retry_count += 1

        if self.retry_count < self.max_retries:
            if self.status != self.Status.PROCESSING:
                raise ValueError(
                    f"Cannot mark Chunk {self.id} as FAILED from status {self.status}."
                )
            self.status = self.Status.PENDING
            self.error_message = ""
        else:
            if not error_message:
                raise ValueError(
                    f"Cannot mark Chunk {self.id} as FAILED without an error message {self.error_message}."
                )
            self.status = self.Status.FAILED
            self.error_message = error_message

        self.save(update_fields=["status", "error_message", "updated_at", "audio_file", "retry_count"])

    @classmethod
    def recover_stuck_chunks(cls, timeout: timedelta = timedelta(minutes=1)):
        """
        Reset chunks that have been PROCESSING longer than `timeout` to PENDING or FAILED.

        - Increments retry_count for each stuck chunk.
        - Marks as FAILED if retry_count exceeds max_retries.
        Returns a set of affected job IDs.
        """
        job_ids = set()

        stuck_chunks = cls.objects.filter(
            status=cls.Status.PROCESSING,
            started_at__lt=timezone.now() - timeout,
        )

        for chunk in stuck_chunks:
            job_id = chunk.job.id
            chunk.retry_count += 1
            if chunk.retry_count < chunk.max_retries:
                chunk.status = cls.Status.PENDING
            else:
                chunk.status = cls.Status.FAILED
                chunk.error_message = f"Cannot recover Chunk {chunk.id}. Last error: {chunk.error_message or 'None'}"

            chunk.save(update_fields=["status", "error_message", "updated_at", "retry_count"])
            job_ids.add(job_id)
            print(f"Recovered Chunk with id {chunk.id} of Job {job_id}")

        return job_ids

    @classmethod
    def claim_next_chunk(cls, job):
        """
        Atomically claim the next available PENDING chunk for the given job.

        Uses select_for_update with skip_locked to avoid race conditions
        in concurrent workers. Only returns chunks with retry_count below max_retries.
        Returns the Chunk instance or None if none available.
        """
        return (
            cls.objects.select_for_update(
                skip_locked=True
            ).filter(
                job=job,
                status=cls.Status.PENDING,
                retry_count__lt=models.F("max_retries"),
            ).order_by("index").first()
        )


    def __str__(self):
        """
        Human-readable representation of the chunk.
        Format: "Chunk {index} of Job {job_id}".
        """
        return f'Chunk {self.index} of Job {self.job_id}'
