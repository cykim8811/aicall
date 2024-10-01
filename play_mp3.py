from pydub import AudioSegment
import io

import wave

class MP3Player:
    def __init__(self, path):
        self.path = path
        f = wave.open(self.path, 'rb')
        self.audio = f.readframes(f.getnframes())
        f.close()

    def play(self, call):
        call.write_audio(self.audio)