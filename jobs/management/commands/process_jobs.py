from django.core.management.base import BaseCommand
from jobs.models import Job


class Command(BaseCommand):
    help = 'Process pending PDF-to-audiobook jobs'

    def handle(self, *args, **options):
        jobs = Job.objects.filter(status=Job.Status.PENDING)

        for job in jobs:
            self.stdout.write(f'Processing job {job.id}...')
            job.status = Job.Status.PROCESSING
            job.save()

            try:
                # Placeholder for real processing
                self.stdout.write(f'Job {job.id}: processing complete')
                job.status = Job.Status.COMPLETED
                job.save()

            except Exception as exc:
                job.status = Job.Status.FAILED
                job.error_message = str(exc)
                job.save()
