
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


premade_promt = ""
for key, text in premade_text.items():
    premade_promt += f"  - {text}\n"


"""
premade outputs에 있는 문장을 사용할 수 있으며 권장된다. 이 때, 텍스트에 해당 키를 $KEY 형식으로 응답하면 된다.
ex)
고객: 잇몸이 아파서 연락드렸어요.
출력: 네 고객님. 예약을 도와드릴까요?
고객: 예약은 언제 가능할까요?
출력: $RESERVATION
"""

system_prompt = """

# 정보
[스탠다드 치과(Standard Dental Clinic)]
## 의료진 목록
 - 잠실본점 / 보철과 전문의 / 연제웅 대표원장
 - 경기이천점 / 보철과 전문의 / 장현민 대표원장
 - 잠실본점 / 구강외과 전문의 / 홍동환 대표원장
 - 잠실본점 / 교정과 전문의 / 서지희 대표원장
 - 부천점 / 통합치의학과 전문의 / 김성룡 대표원장
 - 잠실본점, 경기이천점 / 교정과 전문의 / 서보연 대표원장
 - 잠실본점 / 보존과 전문의 / 이윤희 대표원장
 - 잠실본점 / 보철과 전문의 / 정지원 대표원장
 - 잠실본점 / 통합치의학과 전문의 / 김의현 대표원장
 - 부천점 / - / 김소은 대표원장
 - 부천점 / 치과보철과 전문의 / 김정훈 대표원장
 - 경기이천점 / 통합치의학과 전문의 / 경시환 대표원장
 - 경기이천점 / 치주과 전문의 / 예상현 대표원장

## 진료시간
- 월/화/목 : AM 9:30-PM 09:00(야간진료)
- 토요일 : AM 9:30-PM 02:00
- 수/금 : AM 9:30-PM 07:00

점심시간 : PM 01:00-PM 02:30

※토요일은 점심시간 없이 진료합니다.
※일요일&공휴일은 휴진입니다.

## 주소
스탠다드 치과 잠실본점 : 서울시 송파구 송파대로 562 웰리스타워 9층(잠실역 7번 출구 스타벅스, 국민은행 건물)

## 연락처
대표자 : 홍동환 외 1인 | 사업자등록번호 : 542-19-00336
TEL : 02-6485-2828 | FAX : 02-6485-2829


# 역할
- 스탠다드 치과(Standard Dental Clinic)의 AI 접수원. 환자의 전화에 응대하는 역할을 한다.
- 어떤 상황에서도 친절하고 정확한 답변을 제공한다.
- 항상 존댓말을 사용하며, 공손하고 전문적인 태도를 유지한다.
- 환자의 증상이나 상황에 공감을 표현한다.
- 간결하고 명확하게 대화하지만, 필요한 정보는 빠짐없이 전달한다.
- 고객의 음성은 STT를 통해 텍스트로 변환되어 들어온다. 고로 인식 단계에서 약간의 오류가 있을 수 있다.
ex) 어 금리 불편해요 -> 어금니가 불편해요


# 필수 사항
## 예약
- 환자가 예약을 원할 경우, 불편한 증상을 먼저 물어봐야 한다.
- 증상에 대해 간단히 설명하고, 빠른 진료의 필요성을 언급한다.
- 환자의 선호 요일을 먼저 물어본다. 그 이후 시간대를 확인한다.
- 원하는 시간대가 이미 예약이 찼을 경우, 다른 시간대를 제안한다.

## 개인정보 수집
- 예약 확정 전, 다음 정보를 수집해야 한다.
    - 성함
    - 연락처
    - 예약 시간
    - 생년월일
    - 실비보험 여부
    - 주소

- 연락처 확인 시, '지금 전화하신 번호가 연락처가 맞으신가요?'라고 물어본다.

## 예약 확정
- 모든 정보를 수집한 후, 예약 일시를 다시 확인한다.
- 예약 확인 문자 발송을 안내한다.

## 예약 후
- 추가 문의사항이 있는지 물어본다.
- 추가 문의사항이 없을 경우, '감사합니다. 스탠다드치과의원 잠실본점이었습니다. 좋은 하루 되세요. (통화 종료)'라고 말한다.
- (통화 종료) 문구를 포함해야 한다.

## premade outputs
premade outputs에 있는 문장을 그대로 포함하여, 또는 단독으로 사용하는 것은 최적화된 대화를 위해 권장된다.

""" + premade_promt + """
"""


def run_tts(conversation, call, input_queue, halt, tts_hangup):
    play_tts(call, "안녕하세요, 스탠다드치과의원 잠실본점입니다. 무엇을 도와드릴까요?")
    while len(halt) == 0 and len(tts_hangup) == 0:
        if len(input_queue) > 0:
            value = input_queue.pop(0)
            handle_input(conversation, call, value, tts_hangup)
        else:
            time.sleep(0.1)

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)


premade_audio = {
    key: MP3Player(f"premade_audio/{key}.wav")
    for key, text in premade_text.items()
}

premade_audio['WAIT'] = MP3Player("premade_audio/WAIT.wav")

def handle_input(conversation, call, value, tts_hangup):
    conversation.append({"role": "user", "content": value})
    message = anthropic_client.messages.create(
        system=system_prompt,
        max_tokens=1024,
        messages=conversation,
        model="claude-3-5-sonnet-20240620",
        # model="claude-3-haiku-20240307",
        # model="claude-instant-1.2",
    )
    conversation.append({"role": "assistant", "content": message.content})
    play_tts(call, message.content[0].text)
    if len(message.content) == 0 or "(통화 종료)" in message.content[0].text:
        print("통화 종료")
        time.sleep(5)
        tts_hangup.append(1)
        exit()

def play_tts(call, text):
    for key, premade in premade_text.items():
        # if premade == text:
        #     text = "{" + key + "}"
        text = text.replace(premade, "{" + key + "}")
    # if '$' in text:
    #     key = text.split('$')[1].split(' ')[0].replace('\n', '')
    #     print('AI(cached):', premade_text[key])
    #     premade_audio[key].play(call)
    # else:
    #     # premade_audio['WAIT'].play()
    #     print('AI:', text)
    #     play_voice_clova(call, text)
    text_split = text.replace("{", "$").replace("}", "$").split('$')
    while len(text_split) > 0:
        if len(text_split[0]) > 0 and text_split[0].replace(' ', '') != '':
            print('AI:', text_split[0])
            play_voice_clova(call, text_split[0])
        if len(text_split) > 1:
            key = text_split[1]
            print('AI(cached):', premade_text[key])
            premade_audio[key].play(call)
        text_split = text_split[2:]

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
    audio = audio.set_frame_rate(8000)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(1)

    wav_bytes = io.BytesIO()
    audio.export(wav_bytes, format="wav")
    wav_bytes.seek(0)
    
    call.write_audio(wav_bytes.getvalue())
    

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
        "speed": "0",
        "text": text
    }

    response = requests.post(url, headers=headers, data=data)

    play_mp3_bytes(call, response.content)