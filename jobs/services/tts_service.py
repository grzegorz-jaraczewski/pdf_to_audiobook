from pathlib import Path
from google.cloud import texttospeech

def synthesize_text_to_file(text: str, output_path: Path, voice_name="en-GB-Standard-B", speaking_rate=1.0):
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput({'text': text})
    voice = texttospeech.VoiceSelectionParams({
        'language_code': "en-US",
        'name': voice_name,
    })

    audio_config = texttospeech.AudioConfig({
        'audio_encoding': texttospeech.AudioEncoding.MP3,
        'speaking_rate': speaking_rate,
    })

    response = client.synthesize_speech({
        'input': synthesis_input,
        'voice': voice,
        'audio_config': audio_config,
    })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as out:
        out.write(response.audio_content)
