from pathlib import Path
from pydub import AudioSegment
from io import BytesIO

def assemble_chunks_to_pdf(job_id: int, chunks):
    output_path = Path(f'media/audio/job_{job_id}/audiobook.m4b')
    combined = AudioSegment.empty()

    for chunk in chunks.order_by('index'):
        audio_path = Path(chunk.audio_file.path)
        combined += AudioSegment.from_file(audio_path, format='mp3')

    combined.export(output_path, format='ipod')
    return output_path

def merge_mp3_chunks(chunks) -> bytes:
    """
    Merge chunk audio files (in order) into a single MP3.
    Returns final audiobook as bytes.
    """
    combined = AudioSegment.empty()
    for chunk in chunks:
        chunk.audio_file.open()
        segment = AudioSegment.from_file(chunk.audio_file.path, format='mp3')
        combined += segment
        chunk.audio_file.close()

    buffer = BytesIO()
    combined.export(buffer, format='mp3')

    return buffer.getvalue()
