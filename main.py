from pyVoIP.VoIP import VoIPPhone, CallState
from rtzr import RTZRClient
import wave
import dotenv
import time
import os
import threading

dotenv.load_dotenv()

PASSWORD = os.environ.get("PASSWORD")

f = wave.open('./GREETINGS.wav', 'rb')
greeting_audio = f.readframes(f.getnframes())
f.close()

def run_reader(call):
    while call.state == CallState.ANSWERED:
        data = call.read_audio()
        if data:
            call.write_audio(data)
            print(">", end="", flush=True)

def answer(call):
    call.answer()
    call.write_audio(greeting_audio)
    time.sleep(5)

    reader = threading.Thread(target=run_reader, args=(call,))
    reader.start()

    while call.state == CallState.ANSWERED:
        time.sleep(1)

    call.hangup()

vp = VoIPPhone(
    'london1.voip.ms', 5060, '420319_ai', 
    PASSWORD, callCallback=answer
)
vp.start()
print(vp._status)
input("Press any key to exit the VOIP phone session.")
vp.stop()