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
ENCODING = pb.DecoderConfig.AudioEncoding.MULAW
BYTES_PER_SAMPLE = 2

f = wave.open('./GREETINGS.wav', 'rb')
greeting_audio = f.readframes(f.getnframes())
f.close()

import numpy as np
from scipy import signal

def mulaw_decode(mulaw_data):
    mu = 255
    y = mulaw_data.astype(float)
    y = 2 * (y / 255) - 1
    x = np.sign(y) * (1 / mu) * ((1 + mu)**abs(y) - 1)
    return x

def convert_audio(mulaw_chunk):
    # Step 1: Decode mu-law to linear PCM
    pcm_data = mulaw_decode(np.frombuffer(mulaw_chunk, dtype=np.uint8))
    
    # Step 2: Upsample from 8kHz to 16kHz
    resampled_data = signal.resample(pcm_data, len(pcm_data) * 2)
    
    # Step 3: Convert to 16-bit PCM
    pcm_16bit = (resampled_data * 32767).astype(np.int16)
    
    return pcm_16bit.tobytes()

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

    def transcribe_streaming_grpc(self, call, config):
        base = GRPC_SERVER_URL
        with grpc.secure_channel(
            base, credentials=grpc.ssl_channel_credentials()
        ) as channel:
            stub = pb_grpc.OnlineDecoderStub(channel)
            cred = grpc.access_token_call_credentials(self.token)

            def req_iterator():
                yield pb.DecoderRequest(streaming_config=config)
                # with FileStreamer("rec.wav") as f:
                #     while True:
                #         buff = f.read(size=DEFAULT_BUFFER_SIZE)
                #         if buff is None or len(buff) == 0:
                #             break
                #         yield pb.DecoderRequest(audio_content=buff)
                print("reading audio1")
                while call.state == CallState.ANSWERED:
                    print("reading audio2")
                    buff = call.read_audio(DEFAULT_BUFFER_SIZE)
                    print(buff)
                    if buff is None or len(buff) == 0:
                        break
                    yield pb.DecoderRequest(audio_content=buff)

            req_iter = req_iterator()
            resp_iter = stub.Decode(req_iter, credentials=cred)
            for resp in resp_iter:
                resp: pb.DecoderResponse
                for res in resp.results:
                    print(
                        "[online-grpc] final:{}, text:{}".format(
                            res.is_final, res.alternatives[0].text
                        )
                    )

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
    client.transcribe_streaming_grpc(call, config)

    call.hangup()

vp = VoIPPhone(
    'london1.voip.ms', 5060, '420319_ai', 
    PASSWORD, callCallback=answer
)
vp.start()
print(vp._status)
input("Press any key to exit the VOIP phone session.")
vp.stop()