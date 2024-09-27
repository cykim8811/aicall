from pydub import AudioSegment
import io

class MP3Player:
    def __init__(self, path):
        self.path = path

    def play(self, call):
        # MP3 파일 로드
        audio = AudioSegment.from_mp3(self.path)
        
        # 8000Hz로 리샘플링
        audio = audio.set_frame_rate(8000)
        
        # 모노로 변환 (필요한 경우)
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # 8비트 PCM으로 변환
        audio = audio.set_sample_width(1)
        
        # 바이트 스트림으로 변환
        buffer = io.BytesIO()
        audio.export(buffer, format="raw")
        
        # 오디오 데이터 쓰기
        call.write_audio(buffer.getvalue())