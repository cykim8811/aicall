
import time
import anthropic
import os
import dotenv

from elevenlabs.client import ElevenLabs
from elevenlabs import play, stream
# from elevenlabs.client import DEFAULT_VOICE

from premade import premade_text

dotenv.load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVEN_API_KEY")

eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

import requests
def play_voice_clova(text):
    url = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": "na1f63oq4t",
        "X-NCP-APIGW-API-KEY": "CLW9sHE8QiSnam17WpON1ysTlMwRjdaeBTZoLQu4",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "speaker": "nara",
        "speed": "-2",
        "text": text
    }

    response = requests.post(url, headers=headers, data=data)
    return response.content

premade_audio = {
    key: play_voice_clova(text)
    for key, text in premade_text.items()
}

# save to /premade_audio
for key, audio in premade_audio.items():
    with open(f"premade_audio/{key}.mp3", "wb") as f:
        f.write(audio)