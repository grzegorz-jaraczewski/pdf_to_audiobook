from django.db import models
from pathlib import Path


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

    def update_status_from_chunks(self):
        total = self.chunks.count()
        completed = self.chunks.filter(status=Job.Status.COMPLETED).count()
        failed = self.chunks.filter(status=Job.Status.FAILED).count()

        if completed == total and total > 0:
            self.status = Job.Status.COMPLETED
        elif failed > 0 and completed + failed == total:
            self.status = Job.Status.FAILED
        else:
            self.status = Job.Status.PROCESSING

        self.save()


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
        default=Status.PENDING,
    )

    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('job', 'index')
        ordering = ['index']

    def chunk_audio_upload_path(instance, filename):
        return f'audio/job_{instance.job.id}/chunk_{instance.index}.mp3'

    audio_file = models.FileField(upload_to=chunk_audio_upload_path, blank=True)


    def __str__(self):
        return f'Chunk {self.index} of Job {self.job_id}'


