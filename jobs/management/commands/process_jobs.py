from pathlib import Path
from django.core.management.base import BaseCommand
from jobs.models import Job, Chunk
from jobs.services.audio_assembler import assemble_chunks_to_pdf
from jobs.services.chunker import chunk_text
from jobs.services.pdf_extractor import extract_text_from_pdf
from jobs.services.tts_service import synthesize_text_to_file


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
                    try:
                        output_path = Path(chunk.audio_file.field.upload_to(chunk, 'audio.mp3'))
                        synthesize_text_to_file(chunk.text, output_path)
                        chunk.audio_file.name = str(output_path.relative_to(Path().resolve()))
                        chunk.status = Chunk.Status.COMPLETED
                        chunk.save()

                    except Exception as exc:
                        chunk.status = Chunk.Status.FAILED
                        chunk.error_message = str(exc)
                        chunk.save()

                except Exception as exc:
                    job.status = Job.Status.FAILED
                    job.error_message = str(exc)
                    job.save()

            job.update_status_from_chunks()
            self.stdout.write(f'Job {job.id}: {pending_chunks.count()} chunks remaining.')

            if job.chunks.filter(status=Chunk.Status.PENDING).count() == 0:
                assemble_chunks_to_pdf(job.id, job.chunks.all())
