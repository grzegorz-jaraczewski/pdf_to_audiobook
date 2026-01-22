from pathlib import Path
from django.core.management.base import BaseCommand
from jobs.models import Job, Chunk
from jobs.services.chunker import chunk_text
from jobs.services.pdf_extractor import extract_text_from_pdf


class Command(BaseCommand):
    help = 'Process pending PDF-to-audiobook jobs'

    def handle(self, *args, **options):
        jobs = Job.objects.filter(status=Job.Status.PENDING)

        for job in jobs:
            self.stdout.write(f'Processing Job {job.id}...')

            if not job.chunks.exists():
                pdf_path = Path(job.pdf_file.path)
                full_text = extract_text_from_pdf(pdf_path)
                chunks = chunk_text(full_text)

                for index, text in chunks:
                    Chunk.objects.create(
                        job=job,
                        index=index,
                        text=text,
                    )

            # Process pending chunks
            pending_chunks = job.chunks.filter(status=Chunk.Status.PENDING)

            for chunk in pending_chunks:
                self.stdout.write(f'Processing Chunk {chunk.index} of Job {job.id}...')
                chunk.status = Chunk.Status.PROCESSING
                chunk.save()

                try:
                    # Placeholder for real TTS
                    chunk.status = Chunk.Status.COMPLETED
                    chunk.save()

                except Exception as exc:
                    job.status = Job.Status.FAILED
                    job.error_message = str(exc)
                    job.save()

            job.update_status_from_chunks()
            self.stdout.write(f'Job {job.id}: {pending_chunks.count()} chunks remaining.')
