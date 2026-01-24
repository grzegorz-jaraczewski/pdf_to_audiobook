# PDF to Audiobook Converter
## Overview
This is a personal web tool to convert PDF documents into audiobooks.
Currently, the project supports:
* Uploading PDFs via a web interface
* Saving uploaded files to a local media/uploads/ folder
* Environment configuration via .env for safe storage of secrets (Django secret key, Google Cloud credentials)

Future phases will include:
* Text-to-Speech conversion using Google Cloud TTS
* Handling large PDFs and long audiobooks
* Resumable processing jobs
* Export to M4B audiobook format

## Features Implemented (Phase 1 - Completed)
- Upload PDF files through the Django admin interface
- Automatic text extraction from PDF
- Text chunking for TTS processing
- Google Cloud TTS integration (supports large PDFs, resumable jobs)
- Audio chunks saved under `media/audio/job_<id>/`
- Resumable jobs after failure
- Audiobooks generated in **M4B format**
- Simple admin view of jobs and chunks with status tracking

## Project Structure
```
pdf_to_audiobook/
├── manage.py
├── config/
│   ├── settings.py
│   └── urls.py
├── jobs/
│   ├── views.py
│   ├── urls.py
│   └── templates/jobs/upload.html
├── media/
│   └── uploads/
├── .env
├── .gitignore
└── google-credentials.json  # excluded from git
```
* ```jobs/``` — temporary app handling PDF uploads
* ```media/``` — storage for uploaded files
* ```.env``` — environment variables (not committed)
* ```google-credentials.json``` — Google Cloud TTS credentials (excluded from git)


## Environment Configuration
1. Create a .env file in the project root:
```
DJANGO_SECRET_KEY=<your-generated-secret-key>
DEBUG=True
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google-credentials.json
MEDIA_ROOT=/absolute/path/to/project/media
```
2. Ensure .env and google credentials are added to .gitignore:
```
.env
google-credentials.json
```

## Dependency Management (uv)
This project uses uv instead of pip.
1. Create and activate virtual environment
```aiignore
uv venv
source .venv/bin/activate
```
2. Install dependencies
```aiignore
uv pip install django python-dotenv
```
Additional dependencies will be added in later phases.

## Running the Project
1. Start the Django development server:
```
python manage.py runserver
```
2. Open a browser and navigate to:
```
http://127.0.0.1:8000/upload/
```
3. Upload a PDF file to test the upload flow. Files will appear under media/uploads/.

## Notes / Best Practices
* Keep google-credentials.json secure; never commit it to git.
* Use absolute paths for GOOGLE_APPLICATION_CREDENTIALS and MEDIA_ROOT.
* The current upload page is temporary and intended for infrastructure testing only.
* Phase 2 will implement job tracking, resumable processing, and TTS conversion.

## Next Steps (Phase 2)
Planned improvements include:
- Retry failed chunks
- Parallel chunk processing
- Drag-and-drop uploads
- Multiple voices/languages
- Metadata support for audiobooks
- Web API for automated uploads
- Dockerization and tests

## License
This is a personal project, use and modify as desired. Keep API credentials private.