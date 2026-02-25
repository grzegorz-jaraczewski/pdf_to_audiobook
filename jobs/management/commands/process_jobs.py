from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from jobs.models import Job, Chunk
from jobs.services.chunker import chunk_text
from jobs.services.pdf_extractor import extract_text_from_pdf
from jobs.services.tts_service import synthesize_text_to_bytes


class Command(BaseCommand):
    help = 'Process pending PDF-to-audiobook jobs'

    def handle(self, *args, **options):
        recovered_job_ids = Chunk.recover_stuck_chunks()
        recovered_jobs = Job.objects.filter(id__in=recovered_job_ids)
        for job in recovered_jobs:
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

            while True:
                with transaction.atomic():
                    chunk = Chunk.claim_next_chunk(job)
                    if not chunk:
                        print("Done")
                        break

                    chunk.mark_processing()

                self.stdout.write(f'Processing Chunk {chunk.index} of Job {job.id}...')

                try:
                    audio_bytes = synthesize_text_to_bytes(chunk.text)

                    chunk.audio_file.save(
                        f"chunk_{chunk.index}.mp3",
                        ContentFile(audio_bytes),
                        save=False,
                    )
                    chunk.mark_completed()

                except Exception as exc:
                    chunk.mark_failed(str(exc))

            job.update_status_from_chunks()
            try:
                job.assemble()
            except RuntimeError as exc:
                self.stdout.write(f"Job {job.id} not ready for assembly")
