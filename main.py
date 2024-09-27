from pyVoIP.VoIP import VoIPPhone, CallState
from rtzr import RTZRClient
import wave
import dotenv
import time
import os
import threading
import asyncio

import numpy as np
from scipy import signal

dotenv.load_dotenv()

PASSWORD = os.environ.get("PASSWORD")

f = wave.open('./GREETINGS.wav', 'rb')
greeting_audio = f.readframes(f.getnframes())
f.close()


def convert_audio(data, original_rate=8000, target_rate=16000):
    # Convert bytes to numpy array
    audio = np.frombuffer(data, dtype=np.int8)
    
    # Resample from 8kHz to 16kHz
    number_of_samples = round(len(audio) * float(target_rate) / original_rate)
    audio_resampled = signal.resample(audio, number_of_samples)
    
    # Convert from 8-bit to 32-bit
    audio_32bit = audio_resampled.astype(np.float32)
    
    return audio_32bit.tobytes()

def run_reader(call, queue):
    while call.state == CallState.ANSWERED:
        data = call.read_audio()
        if data:
            queue.append(data)

async def transcriber(call, queue):
    client = RTZRClient()
    await client.start()
    while call.state == CallState.ANSWERED:
        if len(queue) > 0:
            data = queue.pop(0)
            converted_data = convert_audio(data)
            await client.stream(converted_data)
        else:
            await asyncio.sleep(0.01)

def answer(call):
    call.answer()
    call.write_audio(greeting_audio)
    time.sleep(5)

    queue = []
    reader = threading.Thread(target=run_reader, args=(call, queue))
    reader.start()

    asyncio.run(transcriber(call, queue))

    call.hangup()

vp = VoIPPhone(
    'london1.voip.ms', 5060, '420319_ai', 
    PASSWORD, callCallback=answer
)
vp.start()
print(vp._status)
input("Press any key to exit the VOIP phone session.")
vp.stop()