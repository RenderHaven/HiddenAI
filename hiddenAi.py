from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QFont,QTextDocument,QTextCursor,QTextCharFormat,QGuiApplication
from llm import LLMController,OpenRouterLLM
from audio import AudioEngine, AudioController
from input_controller import InputController
from overlay import Overlay


class MessageStore:

    def __init__(self, font, color, width):
        self.messages = []
        self.markdown_docs = []
        self.input_blocks = []
        self.current_text = ""
        self.next_text=""

        self.font = font
        self.color = color
        self.width = width

    def clear(self):
        self.messages = []
        self.markdown_docs = []
        self.input_blocks = []
        self.current_text = ""
        self.next_text=""
    
    def clear_input(self):
        self.input_blocks = []
        self.current_text = ""
        self.next_text=""

    def rebuild_cache(self):
        self.markdown_docs = []

        for msg in self.messages:
            if msg["role"] != "assistant":
                continue

            doc = QTextDocument()
            doc.setDefaultFont(self.font)
            doc.setMarkdown(msg["content"])
            doc.setTextWidth(self.width)

            cursor = QTextCursor(doc)
            cursor.select(QTextCursor.SelectionType.Document)

            fmt = QTextCharFormat()
            fmt.setForeground(self.color)
            cursor.mergeCharFormat(fmt)

            self.markdown_docs.append(doc)

    def add_assistant(self, text):
        self.messages.append({"role": "assistant", "content": text})
        self.rebuild_cache()




# =========================
# MEDIA MANAGER
# =========================
class MediaManager:

    def capture_screen(self, index):
        screen = QGuiApplication.primaryScreen()
        pixmap = screen.grabWindow(0)
        path = f"/tmp/overlay_capture_{index}.png"
        pixmap.save(path, "PNG")
        return path

    def paste_image(self, index):

        clipboard = QGuiApplication.clipboard()

        if clipboard.mimeData().hasImage():

            image = clipboard.image()

            if not image.isNull():

                path = f"/tmp/overlay_paste_{index}.png"
                image.save(path, "PNG")
                return path

        return None

class HiddenAiApp(QApplication):

    def __init__(self,argv,llms):
        super().__init__(argv)

        self.llms = llms

        # =========================
        # CONTROLLERS
        # =========================
        self.llm_controller = LLMController(self.llms)
        self.media = MediaManager()

        # =========================
        # AUDIO
        # =========================
        engine = None
        try:
            engine = AudioEngine("models/vosk-model-small-en-us-0.15")
            engine.chunk_ready.connect(self.on_audio_chunk)
            print("[AUDIO] Engine initialized ✅")
        except Exception as e:
            print("[AUDIO] Failed ❌", e)

        self.audio = AudioController(engine)

        # =========================
        # STATE
        # =========================
        self.is_locked = False
        self.loading = False
        self.is_working = True
        self.error_note = None
        
        

        # =========================
        # STORE
        # =========================
        self.font_color = QColor(255, 255, 255)
        self.font_normal = QFont("Monospace", 14)
        self.font_bold = QFont("Monospace", 14)
        self.font_bold.setBold(True)

        self.store = MessageStore(self.font_normal, self.font_color, 500)

        # =========================
        # UI
        # =========================
        self.overlay = Overlay(self)
        self.input_controller = InputController(self)

        self.llm_controller.finished.connect(self.llm_finished)

    # =========================
    # LLM
    # =========================
    def call_llm(self):
        if not self.store.input_blocks:
            return

        

        self.llm_controller.send(self.store.messages, self.store.input_blocks)

        display_lines = []
        for b in self.store.input_blocks:
            if b["type"] == "text":
                display_lines.append(b["value"])
            else:
                display_lines.append("[image]")

        self.store.messages.append({
            "role": "user",
            "content": "\n".join(display_lines)
        })


        self.store.clear_input()

        self.loading = True
        self.overlay.update()

        

    def llm_finished(self, result):
        self.loading = False

        if isinstance(result, list):
            result = result[0].get("text", "")

        self.store.add_assistant(result)
        self.overlay.update()

    def toggle_model(self):
        self.llm_controller.toggle_model()
        self.overlay.update()

    # =========================
    # AUDIO
    # =========================
    def on_audio_chunk(self, text):
        if self.store.current_text:
            self.store.current_text += " "

        self.store.current_text += text
        self.overlay.update()

    # =========================
    # RESET
    # =========================
    def refresh(self):
        self.store.clear()
        self.overlay.clear_cache()
        self.overlay.update()
