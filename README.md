# PDF to Audiobook Converter
## Overview
PDF to Audiobook Converter is a Django-based backend system that converts PDF documents 
into fully assembled audiobooks using Google Cloud Text-to-Speech.

The system is designed with:
* Persistent job and chunk storage
* Concurrency-safe processing
* Crash recovery and resumability
* Idempotent audio assembly
* Storage-backed media handling

This project demonstrates a production-style background processing architecture built 
with Django ORM and transactional guarantees.

## Core Architecture
The system processes PDFs using a multi-stage pipeline:
- PDF upload
- Text extraction
- Text chunking
- Chunk-level TTS synthesis
- Persistent storage of chunk audio
- Atomic final audio assembly

Each processing unit is represented by:
* Job - represents a full PDF-to-audiobook conversion
* Chunk - represents a portion of text processed independently

The design ensures:
* Safe concurrent workers via ```select_for_update(skip_locked=True)```
* Retry logic with bounded ```max_retries```
* Recovery of stuck processing tasks
* Idempotent job assembly
* Crash-safe resume capability

## Implemented features
* PDF upload via Django
* Automatic PDF text extraction
* Deterministic text chunking
* Google Cloud Text-to-Speech integration
* Chunk-level audio persistence
* Retry mechanism with failure handling
* Recovery of stuck chunks
* Transaction-safe chunk claiming
* Atomic final MP4 assembly
* Status tracking (Pending, Processing, Completed, Failed)
* Concurrency-safe processing pipeline

## Project Structure
```
pdf_to_audiobook/
├── manage.py
├── config/
│   ├── settings.py
│   └── urls.py
├── jobs/
│   ├── services/
│   │   ├── audio_assembler.py
│   │   ├── chunker.py
│   │   ├── pdf_extractor.py
│   │   └── tts_service.py
│   ├── templates/jobs/upload.html
│   ├── admin.py    
│   ├── models.py   
│   ├── urls.py
│   └── views.py
├── media/
│   ├── audio/
│   ├── intermediate/
│   ├── output/
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
This project uses uv for dependency management.
1. Create and activate virtual environment
```aiignore
uv venv
source .venv/bin/activate
```
2. Install dependencies
```aiignore
uv add django python-dotenv google-cloud-texttospeech
```

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

## Design Principles Demonstrated
* Idempotent operations
* Transactional integrity
* Concurrency control with row-level locking
* Crash recovery
* Persistent media storage
* Clear separation of orchestration and services
* Deterministic state transitions

## Project Status
This project is considered feature-complete as a backend processing system.
It serves as:
* A learning project for advanced Django architecture
* A reference implementation of transactional background processing
* A foundation for future API or UI expansion

No further development is currently planned.

## License
Personal project.
Use and modify as needed.
Keep API credentials private.