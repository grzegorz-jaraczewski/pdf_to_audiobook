from google.cloud import texttospeech


_client: texttospeech.TextToSpeechClient | None = None


def _get_client():
    """
    Return a lazily initialized singleton instance of
    google.cloud.texttospeech.TextToSpeechClient.

    The client is created only once per process and reused for subsequent
    calls to avoid repeated initialization overhead and unnecessary
    connection setup.

    This function is process-local and not intended to provide cross-process
    pooling. Thread safety relies on the Google Cloud client implementation,
    which is designed to be reused across requests.

    Returns:
        texttospeech.TextToSpeechClient: Initialized TTS client instance.
    """
    global _client
    if _client is None:
        _client = texttospeech.TextToSpeechClient()

    return _client



def synthesize_text_to_bytes(text: str, language_code: str = "en-US", voice_name: str | None = None) -> bytes:
    """
    Generate MP3 audio bytes from text using Google Cloud TTS.

    This function is infrastructure-agnostic.
    It does NOT write to disk and does NOT depend on Django.
    """
    client = _get_client()

    synthesis_input = texttospeech.SynthesisInput({'text': text})

    voice_params = texttospeech.VoiceSelectionParams({
        'language_code': language_code,
        'name': voice_name,
    })

    audio_config = texttospeech.AudioConfig({
        'audio_encoding': texttospeech.AudioEncoding.MP3,
    })

    response = client.synthesize_speech({
        'input': synthesis_input,
        'voice': voice_params,
        'audio_config': audio_config,
    })

    return response.audio_content
