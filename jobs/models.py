from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone

from jobs.services.audio_assembler import assemble_chunks_to_pdf


class Job(models.Model):
    class Status(models.TextChoices):
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

    def update_status_from_chunks(self):
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
        if self.assembled_at is not None:
            return False
        if not self.chunks.exists():
            return False

        return not self.chunks.exclude(status=Chunk.Status.COMPLETED).exists()

    def assemble(self):
        if not self.can_assemble():
            raise RuntimeError(f"Job {self.id} cannot be assembled: chunks not ready")

        with transaction.atomic():
            self.status = self.Status.COMPLETED
            self.assembled_at = timezone.now()
            self.save(update_fields=['status', 'assembled_at'])

        completed_chunks = self.chunks.filter(status=Chunk.Status.COMPLETED).order_by("index")
        assemble_chunks_to_pdf(self.id, completed_chunks)

    def __str__(self):
        return f"Job #{self.id} - {self.status}"


class Chunk(models.Model):
    class Status(models.TextChoices):
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
    started_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    retry_count = models.PositiveIntegerField(default=0, null=False, blank=False)
    max_retries = models.PositiveIntegerField(default=3, null=False, blank=False)

    class Meta:
        unique_together = ('job', 'index')
        ordering = ['index']

    def chunk_audio_upload_path(instance, filename):
        return f'audio/job_{instance.job.id}/chunk_{instance.index}.mp3'

    audio_file = models.FileField(upload_to=chunk_audio_upload_path, blank=True)

    def mark_processing(self):
        """
        Transition chunk from PENDING to PROCESSING.
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
        Transition chunk from PROCESSING to COMPLETED.
        Requires a valid audio_file.
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
        Transition chunk from PROCESSING to FAILED.
        Requires an error message explaining the failure.
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

    def is_runnable(self) -> bool:
        return (self.status == self.Status.PENDING
                and not self.audio_file
                and self.retry_count < self.max_retries)

    @classmethod
    def recover_stuck_chunks(cls, timeout: timedelta = timedelta(minutes=1)):
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


    def __str__(self):
        return f'Chunk {self.index} of Job {self.job_id}'
