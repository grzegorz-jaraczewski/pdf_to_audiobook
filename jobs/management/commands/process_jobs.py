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
        recovered_job_ids = Chunk.recover_stuck_chunks()
        if recovered_job_ids:
            print(f"Recovered chunks from jobs: {recovered_job_ids}")

        for job_id in recovered_job_ids:
            job = Job.objects.get(id=job_id)
            job.update_status_from_chunks()

        jobs = Job.objects.filter(
            Q(status=Job.Status.PENDING) | Q(status=Job.Status.PROCESSING)
        )

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
                if chunk.audio_file:
                    chunk.mark_completed()
                    continue

                self.stdout.write(f'Processing Chunk {chunk.index} of Job {job.id}...')
                chunk.mark_processing()

                try:
                    relative_path = chunk.audio_file.field.upload_to(chunk, 'audio.mp3')
                    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
                    synthesize_text_to_file(chunk.text, absolute_path)

                    chunk.audio_file.name = relative_path
                    chunk.mark_completed()

                except Exception as exc:
                    chunk.mark_failed(str(exc))

            job.update_status_from_chunks()

            completed_chunks = job.chunks.filter(status=Chunk.Status.COMPLETED)
            if job.status == Job.Status.COMPLETED and all(c.audio_file for c in completed_chunks):
                assemble_chunks_to_pdf(job.id, completed_chunks)
            else:
                continue
