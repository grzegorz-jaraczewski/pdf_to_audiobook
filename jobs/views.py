from django.shortcuts import render, redirect, get_object_or_404

from .models import Job

def upload_pdf(request):
    """
    Handle PDF file uploads and create a new Job instance.

    If the request method is POST and a file named 'pdf_file' is provided,
    a new Job object is created with the uploaded PDF, and the user is
    redirected to the job detail page. Otherwise, renders the upload form.

    Args:
        request (HttpRequest): The incoming HTTP request object.

    Returns:
        HttpResponse: Redirects to the job detail page on successful upload,
                      or renders the upload form template for GET requests.
    """
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        job = Job.objects.create(pdf_file=request.FILES['pdf_file'])
        return redirect('job_detail', job_id=job.id)

    return render(request, 'jobs/upload.html')

def job_detail(request, job_id):
    """
    Display the details of a specific Job.

    Retrieves the Job object with the given ID and renders the job detail
    template. If no Job exists with the given ID, raises a 404 error.

    Args:
        request (HttpRequest): The incoming HTTP request object.
        job_id (int): ID of the Job to display.

    Returns:
        HttpResponse: Renders the job detail template with the Job context.
    """
    job = get_object_or_404(Job, id=job_id)
    return render(request, 'jobs/job_detail.html', {"job": job})
