from pyVoIP.VoIP import VoIPPhone, CallState

import grpc
import json
import time
import wave
import dotenv
import time
import os
import threading
import asyncio
import logging
from io import DEFAULT_BUFFER_SIZE

import vito_stt_client_pb2 as pb
import vito_stt_client_pb2_grpc as pb_grpc

import numpy as np
from scipy import signal
from requests import Session

dotenv.load_dotenv()

PASSWORD = os.environ.get("PASSWORD")
API_BASE = "https://openapi.vito.ai"
GRPC_SERVER_URL = "grpc-openapi.vito.ai:443"
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

SAMPLE_RATE = 8000
ENCODING = pb.DecoderConfig.AudioEncoding.LINEAR16
BYTES_PER_SAMPLE = 2

f = wave.open('./GREETINGS.wav', 'rb')
greeting_audio = f.readframes(f.getnframes())
f.close()

def convert_audio(chunk):
    output_bytes = bytearray()
    for byte in chunk:
        sample_16bit = (byte - 128) * 256
        output_bytes.extend(sample_16bit.to_bytes(2, byteorder='little', signed=True))
    return bytes(output_bytes)

import tempfile
from pydub import AudioSegment
class FileStreamer:
    def __init__(self, file):
        file_name = os.path.basename(file)
        i = file_name.rindex(".")
        audio_file_8k_path = (
            os.path.join(tempfile.gettempdir(), file_name[:i])
            + "_"
            + str(SAMPLE_RATE)
            + ".wav"
        )
        self.filepath = audio_file_8k_path
        audio = AudioSegment.from_file(file=file, format=file[i + 1 :])
        audio = audio.set_frame_rate(SAMPLE_RATE)
        audio = audio.set_channels(1)
        audio.export(audio_file_8k_path, format="wav")
        self.file = open(audio_file_8k_path, "rb")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()
        os.remove(self.filepath)

    def read(self, size):
        if size > 1024 * 1024:
            size = 1024 * 1024
        time.sleep(size / (SAMPLE_RATE * BYTES_PER_SAMPLE))
        content = self.file.read(size)
        return content

class RTZROpenAPIClient:
    def __init__(self, client_id, client_secret):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self.client_id = client_id
        self.client_secret = client_secret
        self._sess = Session()
        self._token = None

    @property
    def token(self):
        if self._token is None or self._token["expire_at"] < time.time():
            resp = self._sess.post(
                API_BASE + "/v1/authenticate",
                data={"client_id": self.client_id, "client_secret": self.client_secret},
            )
            resp.raise_for_status()
            self._token = resp.json()
        return self._token["access_token"]
    
    def send_audio(self, call, queue):
        while call.state == CallState.ANSWERED:
            audio = call.read_audio()
            if audio is None:
                break
            queue.append(audio)

    def transcribe_streaming_grpc(self, call, config):
        base = GRPC_SERVER_URL
        with grpc.secure_channel(
            base, credentials=grpc.ssl_channel_credentials()
        ) as channel:
            stub = pb_grpc.OnlineDecoderStub(channel)
            cred = grpc.access_token_call_credentials(self.token)

            def req_iterator():
                yield pb.DecoderRequest(streaming_config=config)
                try:
                    queue = []
                    input_thread = threading.Thread(target=self.send_audio, args=(call, queue))
                    input_thread.start()
                    while call.state == CallState.ANSWERED:
                        time.sleep(1/50)
                        if len(queue) == 0:
                            buff = b"\x00" * 160
                        else:
                            buff = queue.pop(0)
                        buff = convert_audio(buff)
                        yield pb.DecoderRequest(audio_content=buff)
                        # 오디오 데이터를 파일에 저장
                        self.save_audio_chunk(buff)
                    input_thread.join()
                except Exception as e:
                    print(e)
            
            from output_stream import run_tts
            input_queue = []
            halt_tts = []
            tts_hangup = []
            tts_thread = threading.Thread(target=run_tts, args=(call, input_queue, halt_tts, tts_hangup))
            tts_thread.start()

            req_iter = req_iterator()
            resp_iter = stub.Decode(req_iter, credentials=cred)
            for resp in resp_iter:
                resp: pb.DecoderResponse
                for res in resp.results:
                    if res.is_final:
                        print("User:", res.alternatives[0].text)
                        input_queue.append(res.alternatives[0].text)
            
            halt_tts.append(True)
            tts_thread.join()

    def save_audio_chunk(self, chunk):
        if not hasattr(self, 'audio_file'):
            self.audio_file = wave.open(f'recorded_audio_{int(time.time())}.wav', 'wb')
            self.audio_file.setnchannels(1)
            self.audio_file.setsampwidth(2)
            self.audio_file.setframerate(SAMPLE_RATE)
        
        self.audio_file.writeframes(chunk)

    def close_audio_file(self):
        if hasattr(self, 'audio_file'):
            self.audio_file.close()
            del self.audio_file

def answer(call):
    call.answer()
    call.write_audio(greeting_audio)
    time.sleep(5)

    config = pb.DecoderConfig(
        sample_rate=SAMPLE_RATE,
        encoding=ENCODING,
        use_itn=True,
        use_disfluency_filter=False,
        use_profanity_filter=False,
    )

    client = RTZROpenAPIClient(CLIENT_ID, CLIENT_SECRET)
    try:
        client.transcribe_streaming_grpc(call, config)
    finally:
        client.close_audio_file()

    call.hangup()

vp = VoIPPhone(
    'london1.voip.ms', 5060, '420319_ai', 
    PASSWORD, callCallback=answer
)
vp.start()
print(vp._status)
input("Press any key to exit the VOIP phone session.")
vp.stop()