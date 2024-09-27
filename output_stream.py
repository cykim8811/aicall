
import time
import anthropic
import os
import dotenv
import io
import pydub.playback as sa
from pydub import AudioSegment


from elevenlabs.client import ElevenLabs
from elevenlabs import stream

from play_mp3 import MP3Player
from premade import premade_text

dotenv.load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVEN_API_KEY")

system_prompt = """
너는 선샤인 치과의 직원이다. 환자의 전화에 응대하는 역할을 하는 것이 목적이다.
고객의 대화는 STT를 통해 인식되어 들어온다. 따라서 약간의 오류가 있을 수 있다.
premade outputs에 있는 문장을 사용할 수 있으며 권장된다. 이 때, 텍스트에 해당 키를 $KEY 형식으로 응답하면 된다.
ex)
고객: 예약은 언제 가능할까요?
출력: $RESERVATION

예약을 위해서는 성함, 연락처가 필요하다. 고객이 예약을 원한다면, 성함과 연락처를 꼭 알아야 한다.

## premade outputs
"""
for key, text in premade_text.items():
    system_prompt += f"${key}: {text}\n"

conversation = [
    {"role": "user", "content": "(전화 시작)"},
    {"role": "assistant", "content": "안녕하세요, 선샤인 치과입니다. 무엇을 도와드릴까요?"}
]

def run_tts(call, input_queue, halt, tts_hangup):
    play_tts(call, "$GREETINGS")
    while len(halt) == 0:
        if len(input_queue) > 0:
            value = input_queue.pop(0)
            handle_input(call, value, tts_hangup)
        else:
            time.sleep(0.1)

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)


premade_audio = {
    key: MP3Player(f"premade_audio/{key}.mp3")
    for key, text in premade_text.items()
}

premade_audio['WAIT'] = MP3Player("premade_audio/WAIT.mp3")

def handle_input(call, value, tts_hangup):
    conversation.append({"role": "user", "content": value})
    message = anthropic_client.messages.create(
        system=system_prompt,
        max_tokens=1024,
        messages=conversation,
        model="claude-3-haiku-20240307",
        # model="claude-instant-1.2",
    )
    conversation.append({"role": "assistant", "content": message.content})
    if len(message.content) == 0 or "$HANGUP" in message.content[0].text:
        tts_hangup.append(1)
        exit()
    play_tts(call, message.content[0].text)

def play_tts(call, text):
    # for key, premade in premade_text.items():
    #     if premade == text:
    #         text = f"${key}"
    if '$' in text:
        key = text.split('$')[1].split(' ')[0].replace('\n', '')
        print('AI(cached):', premade_text[key])
        premade_audio[key].play(call)
    else:
        # premade_audio['WAIT'].play()
        print('AI:', text)
        play_voice_clova(call, text)

def play_voice_eleven(text):
    audio_stream = eleven_client.generate(
        text=text,
        voice="Jina",
        model="eleven_turbo_v2_5",
        stream=True
    )
    stream(audio_stream)

from pydub.playback import play
def play_mp3_bytes(call, mp3_bytes):
    audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
    # play(audio)
    call.write_audio(audio.raw_data)

import requests
def play_voice_clova(call, text):
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

    play_mp3_bytes(call, response.content)