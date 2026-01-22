from django.shortcuts import render, redirect, get_object_or_404

from .models import Job

def upload_pdf(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        job = Job.objects.create(pdf_file=request.FILES['pdf_file'])
        return redirect('job_detail', job_id=job.id)

    return render(request, 'jobs/upload.html')

def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, 'jobs/job_detail.html', {"job": job})
