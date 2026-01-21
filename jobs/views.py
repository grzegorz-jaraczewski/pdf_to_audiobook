from django.shortcuts import render
from django.conf import settings
import os

def upload_pdf(request):
    message = ''
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        pdf_file = request.FILES['pdf_file']
        upload_path = os.path.join(settings.MEDIA_ROOT, 'uploads', pdf_file.name)
        with open(upload_path, 'wb+') as destination:
            for chunk in pdf_file.chunks():
                destination.write(chunk)
        message = f'File "{pdf_file.name}" uploaded successfully.'
    return render(request, 'jobs/upload.html', {'message': message})
