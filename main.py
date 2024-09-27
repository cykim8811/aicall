from pyVoIP.VoIP import VoIPPhone, CallState

from rtzr import RTZRClient

import wave
import dotenv
import time
import os


dotenv.load_dotenv()

PASSWORD = os.environ.get("PASSWORD")

def answer(call):
    try:
        f = wave.open('./GREETINGS.wav', 'rb')
        data = f.readframes(f.getnframes())
        f.close()

        call.answer()
        call.write_audio(data)

        time.sleep(3)
        while call.state == CallState.ANSWERED:
            data = call.read_audio()
            print(len(data))

    except Exception as e:
        print(e)
    finally:
       print("Hangup call")
       call.hangup()


vp = VoIPPhone(
    'london1.voip.ms', 5060, '420319_ai', 
    PASSWORD, callCallback=answer
)
vp.start()
print(vp._status)
input("Press any key to exit the VOIP phone session.")
vp.stop()
