import queue
import json
import sounddevice as sd

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from vosk import Model, KaldiRecognizer

# =========================
# AUDIO CONTROLLER
# =========================
class AudioController:

    def __init__(self, engine=None):
        self.engine = engine
        self.listening = False
        self.available = engine is not None

        if not self.available:
            print("🎤 AUDIO: engine not available")

    def start(self):

        if not self.available:
            print("🎤 AUDIO: not working")
            return

        try:
            self.engine.start()
            self.listening = True
        except Exception as e:
            print("🎤 AUDIO START FAILED:", e)
            self.available = False

    def stop(self):

        if not self.available:
            return

        try:
            self.engine.stop()
            self.listening = False
        except Exception as e:
            print("🎤 AUDIO STOP FAILED:", e)
            self.available = False

class AudioEngine(QObject):

    # ⭐ emitted whenever a speech chunk is ready
    chunk_ready = pyqtSignal(str)

    def __init__(self, model_path):
        super().__init__()

        print("AUDIO: init engine")

        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)

        self.audio_queue = queue.Queue()
        self.stream = None
        self.recording = False

        # ⭐ internal timer to process queue automatically
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self._process_queue)

    # 🎤 mic callback (runs in audio thread)
    def _callback(self, indata, frames, time, status):
        self.audio_queue.put(bytes(indata))

    # ▶️ start recording
    def start(self):

        if self.recording:
            return

        print("AUDIO: start mic")

        self.stream = sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )

        self.stream.start()
        self.recording = True

        # ⭐ start automatic processing
        self.process_timer.start(30)

    # ⏹ stop recording
    def stop(self):

        if not self.recording:
            return

        print("AUDIO: stop mic")

        # stop timer first so no concurrent processing
        self.process_timer.stop()

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        # ⭐ VERY IMPORTANT — flush remaining audio
        self._process_queue()   # process everything already queued

        # ⭐ get FINAL recognizer result
        try:
            final = json.loads(self.recognizer.FinalResult())
            text = final.get("text", "")

            if text:
                print("AUDIO FINAL:", text)
                self.chunk_ready.emit(text)

        except Exception as e:
            print("AUDIO FINAL ERROR:", e)

        # ⭐ clear leftover queue safely
        while not self.audio_queue.empty():
            self.audio_queue.get()

        # ⭐ reset recognizer for next session
        self.recognizer.Reset()

        self.recording = False

    # 🧠 internal queue processor (NO RETURN VALUE)
    def _process_queue(self):

        while not self.audio_queue.empty():

            data = self.audio_queue.get()

            if self.recognizer.AcceptWaveform(data):

                result = json.loads(self.recognizer.Result())
                text = result.get("text", "")

                if text:
                    print("AUDIO CHUNK:", text)

                    # ⭐ push text to UI automatically
                    self.chunk_ready.emit(text)

