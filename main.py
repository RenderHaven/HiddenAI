# =========================
# IMPORTS
# =========================
import sys
import base64

from PyQt6.QtWidgets import QWidget,QApplication
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF, QObject
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QCursor, QGuiApplication,
    QTextLayout, QTextOption, QTextDocument,
    QTextCharFormat, QTextCursor, QPixmap,QPen
)

from llm import LLM, LLMController
from audio import AudioEngine,AudioController
from input_controller import InputController
from dotenv import load_dotenv
import os

load_dotenv()


# =========================
# MESSAGE STORE
# =========================
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

# =========================
# OVERLAY UI
# =========================
class Overlay(QWidget):

    def __init__(self):
        super().__init__()

        # runtime flags
        self.is_working = True
        self.error_note = None

        # call initializer
        self.initialize()


    def initialize(self):

        # =========================
        # TOKENS
        # =========================
        vision_token = os.getenv("VISION_TOKEN")

        if not vision_token:
            self.is_working = False
            self.error_note = "VISION_TOKEN not found in environment"

        # =========================
        # LLM MODELS
        # =========================
        self.text_llm = LLM(token=vision_token)
        self.vision_llm = LLM(token=vision_token,is_vision=True)
        self.llm_controller = LLMController(self.text_llm)

        # =========================
        # AUDIO ENGINE
        # =========================
        engine = None

        try:
            engine = AudioEngine("models/vosk-model-small-en-us-0.15")
            engine.chunk_ready.connect(self.on_audio_chunk)
            print("[AUDIO] Engine initialized ✅")

        except Exception as e:
            print("[AUDIO] Failed to initialize ❌")
            print("[AUDIO] Reason:", e)

        self.audio = AudioController(engine)

        # =========================
        # MEDIA + STORE
        # =========================
        self.media = MediaManager()

        self.font_color = QColor(255, 255, 255)
        self.font_normal = QFont("Monospace", 14)
        self.font_bold = QFont("Monospace", 14)
        self.font_bold.setBold(True)

        self.store = MessageStore(self.font_normal, self.font_color, 500)
        self.input_controller = InputController(self)

        self.llm_controller.finished.connect(self.llm_finished)

        # =========================
        # UI STATE
        # =========================
        self.is_locked = False
        self.loading = False
        self.spinner_frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        self.spinner_index = 0
        self.scroll_offset = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.bottom = 0
        self.resize(520, 420)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        self.move(self.screen_width - 540, self.screen_height - 280)

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_mouse_position)
        self.timer.start(50)

        self.hide()


    def refresh(self):
        """
        Completely reinitialize app state.
        """
        self.store.clear()

        # Optional: stop old timer to avoid duplicates
        if hasattr(self, "timer"):
            self.timer.stop()

        # Reinitialize everything
        self.initialize()

        self.update()
    
    def toggle_model(self):
        if self.llm_controller:
            self.llm_controller.llm=self.vision_llm if self.llm_controller.llm==self.text_llm else self.text_llm
        self.update()
        
    # =========================
    # AUDIO UPDATE
    # =========================
    def on_audio_chunk(self, text):

        if self.store.current_text:
            self.store.current_text += " "

        self.store.current_text += text

        self.update()

    # =========================
    # LLM CALL
    # =========================
    def call_llm(self):

        if not self.store.input_blocks:
            return

        self.loading=True
        self.update()

        self.llm_controller.send(self.store.messages,self.store.input_blocks)

        self.store.input_blocks=[]
        self.store.current_text=""

    def llm_finished(self,result):

        self.loading=False

        if isinstance(result,list):
            result=result[0].get("text","")

        self.store.add_assistant(result)
        self.update()

    # =========================
    # INPUT EVENTS
    # =========================
    def keyPressEvent(self,event):
        self.input_controller.handle(event)

    def keyReleaseEvent(self,event):
        self.input_controller.release(event)

    # =========================
    # DRAW HELPERS
    # =========================
    def build_layout(self, text, font):
        layout = QTextLayout(text, font)

        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(option)

        layout.beginLayout()

        y = 0
        content_width = self.width() - 20   # same width you use in paintEvent

        while True:
            line = layout.createLine()
            if not line.isValid():
                break

            line.setLineWidth(content_width)   # ⭐ THIS enables multiline
            line.setPosition(QPointF(0, y))
            y += line.height()

        layout.endLayout()

        return layout

    def draw_layout(self,painter,layout,x,y,width):

        layout.beginLayout()
        height=0

        while True:
            line=layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            line.setPosition(QPointF(x,y+height))
            height+=line.height()

        layout.endLayout()
        layout.draw(painter,QPointF(0,0))
        return height

    # =========================
    # PAINT
    # =========================
    def paintEvent(self,event):

        painter=QPainter(self)
        painter.setPen(self.font_color)

        if self.is_locked:
            painter.setFont(self.font_normal)

            lock_text = "<runing>"

            # ⭐ bottom-right padding
            margin_x = 12
            margin_y = 10

            # measure text width so it hugs right side
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(lock_text)
            text_height = fm.height()

            x = self.width() - text_width - margin_x
            y = self.height() - margin_y

            painter.drawText(x, y, lock_text)

            return

        content_width=self.width()-20
        y=25-self.scroll_offset

        mode_tag="[VISION]" if self.llm_controller.llm.is_vision else "[TEXT]"

        audio_tag = "+[AUDIO]" if self.audio.engine is not None else ""
        title_layout = self.build_layout(
            f"HiddenAI {mode_tag}{audio_tag}",
            self.font_normal
        )
        y+=self.draw_layout(painter,title_layout,10,y,content_width)+10

        ai_index=0

        for msg in self.store.messages:

            if msg["role"]=="user":
                layout=self.build_layout("> "+msg["content"],self.font_bold)
                y+=self.draw_layout(painter,layout,10,y,content_width)+6
            else:
                doc=self.store.markdown_docs[ai_index]
                painter.save()
                painter.translate(10,y)
                doc.drawContents(painter)
                painter.restore()
                y+=doc.size().height()+6
                ai_index+=1

        # INPUT BLOCKS
        for block in self.store.input_blocks:

            if block["type"]=="text":
                layout=self.build_layout("> "+block["value"],self.font_bold)
                y+=self.draw_layout(painter,layout,10,y,content_width)+4

            elif block["type"]=="image":

                prefix=self.build_layout("> ",self.font_bold)
                self.draw_layout(painter,prefix,10,y,content_width)

                pixmap=QPixmap(block["value"])

                if not pixmap.isNull():

                    scaled=pixmap.scaledToWidth(275,
                        Qt.TransformationMode.SmoothTransformation)

                    painter.drawPixmap(QPointF(30,y),scaled)
                    y+=scaled.height()+6

        
        if not self.is_working:
            layout=self.build_layout(self.error_note,self.font_bold)
            y+=self.draw_layout(painter,layout,10,y,content_width)+6
        # 🤖 LLM LOADING
        elif self.loading:

            spinner = self.spinner_frames[self.spinner_index]
            
            layout = self.build_layout(spinner, self.font_normal)
            y += self.draw_layout(painter, layout, 10, y, content_width)

        # ⌨️ NORMAL INPUT
        else:

            input_text = ">" + self.store.current_text + self.store.next_text

            input_layout = self.build_layout(
                input_text,
                self.font_bold
            )

            # ⭐ save layout info for cursor layer
            self._cursor_layout = input_layout

            y += self.draw_layout(painter, input_layout, 10, y, content_width)

            

            painter.save()
            pen = QPen(self.font_color)
            pen.setWidth(2)  
            painter.setPen(pen)

            layout = self._cursor_layout

            # caret index = after current_text
            cursor_index = len(">" + self.store.current_text)

            # find which wrapped line contains the cursor
            line = layout.lineForTextPosition(cursor_index)

            # get X inside that line
            cursor_x ,_= line.cursorToX(cursor_index)

            # Y inside layout
            cursor_y = line.y()
            

            # convert to widget coordinates
            draw_x = cursor_x
            draw_y = cursor_y

            # draw vertical caret
            painter.drawLine(
                int(draw_x),
                int(draw_y),
                int(draw_x),
                int(draw_y + line.height())
            )

            painter.restore()
        
        self.bottom=y



    # =========================
    def check_mouse_position(self):

        pos=QCursor.pos()
        trigger_margin=10

        in_corner=(pos.x()>=self.screen_width-trigger_margin and
                   pos.y()>=self.screen_height-trigger_margin)

        if in_corner:
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.setFocus()
                
        else:
            if self.isVisible():
                self.hide()


# =========================
# RUN APP
# =========================
app=QApplication(sys.argv)
overlay=Overlay()
sys.exit(app.exec())