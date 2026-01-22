from pathlib import Path
from pydub import AudioSegment

def assemble_chunks_to_pdf(job_id: int, chunks):
    output_path = Path(f'media/audio/job_{job_id}/audiobook.m4b')
    combined = AudioSegment.empty()

    for chunk in chunks.order_by('index'):
        audio_path = Path(chunk.audio_file.path)
        combined += AudioSegment.from_file(audio_path, format='mp3')

    combined.export(output_path, format='ipod')
    return output_path
