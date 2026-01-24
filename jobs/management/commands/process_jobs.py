from pathlib import Path
from django.core.management.base import BaseCommand
from django.db.models import Q
from jobs.models import Job, Chunk
from jobs.services.audio_assembler import assemble_chunks_to_pdf
from jobs.services.chunker import chunk_text
from jobs.services.pdf_extractor import extract_text_from_pdf
from jobs.services.tts_service import synthesize_text_to_file
from pdf_to_audiobook import settings


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
                    relative_path = chunk.audio_file.field.upload_to(chunk, 'audio.mp3')
                    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
                    synthesize_text_to_file(chunk.text, absolute_path)

                    chunk.audio_file.name = relative_path
                    chunk.status = Chunk.Status.COMPLETED
                    chunk.save()

                except Exception as exc:
                    chunk.status = Chunk.Status.FAILED
                    chunk.error_message = str(exc)
                    chunk.save()

            job.update_status_from_chunks()
            self.stdout.write(f'Job {job.id}: {pending_chunks.count()} chunks remaining.')

            failed_chunk = job.chunks.filter(status=Chunk.Status.FAILED).first()
            if failed_chunk:
                job.status = Job.Status.FAILED
                job.error_message = (
                    f'Chunk {failed_chunk.index} failed: {failed_chunk.error_message}'
                )
                job.save()

            if job.chunks.filter(status=Chunk.Status.PENDING).exists():
                return # not ready

            if job.chunks.filter(status=Chunk.Status.FAILED).exists():
                return # already handled above

            if job.chunks.filter(Q(audio_file__isnull=True) | Q(audio_file="")).exists():
                return # safety

            assemble_chunks_to_pdf(job.id, job.chunks.all())
            job.status = Job.Status.COMPLETED
            job.save()
