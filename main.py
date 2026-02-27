# =========================
# IMPORTS
# =========================
import sys
import base64

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF, QObject
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QCursor, QGuiApplication,
    QTextLayout, QTextOption, QTextDocument,
    QTextCharFormat, QTextCursor, QPixmap,QPen
)

from llm import LLM, VisionLLM
from audio import AudioEngine

from dotenv import load_dotenv
import os
load_dotenv()

# =========================
# LLM WORKER (UNCHANGED)
# =========================
class LLMWorker(QThread):
    finished_signal = pyqtSignal(str)

    def __init__(self, llm, messages):
        super().__init__()
        self.llm = llm
        self.messages = messages

    def run(self):
        result = self.llm.generate(self.messages)
        self.finished_signal.emit(result)


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
# LLM CONTROLLER
# =========================
class LLMController(QObject):

    finished = pyqtSignal(str)

    def __init__(self, text_llm, vision_llm):
        super().__init__()
        self.text_llm = text_llm
        self.vision_llm = vision_llm
        self.llm = text_llm
        self.is_vision_mode = False

    def toggle_model(self):
        self.is_vision_mode = not self.is_vision_mode
        self.llm = self.vision_llm if self.is_vision_mode else self.text_llm

    def send(self, messages, input_blocks):

        display_lines = []
        for b in input_blocks:
            display_lines.append(b["value"] if b["type"] == "text" else "[image] ")

        messages.append({
            "role": "user",
            "content": "\n".join(display_lines)
        })

        content_blocks = []

        for block in input_blocks:

            if block["type"] == "text":
                content_blocks.append({"type": "text", "text": block["value"]})

            elif block["type"] == "image":

                with open(block["value"], "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")

                content_blocks.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                })

        api_messages = []

        for msg in messages[:-1]:
            api_messages.append({
                "role": msg["role"],
                "content": [{"type": "text", "text": msg["content"]}]
            })

        api_messages.append({
            "role": "user",
            "content": content_blocks
        })

        self.worker = LLMWorker(self.llm, api_messages)
        self.worker.finished_signal.connect(self.finished.emit)
        self.worker.start()


# =========================
# INPUT CONTROLLER
# =========================
class InputController:

    def __init__(self, overlay):
        self.overlay = overlay

    def handle(self, event):

        o = self.overlay
        store = o.store

        if event.key() == Qt.Key.Key_Delete:

            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                QApplication.quit()
                return

            o.is_locked = not o.is_locked
            o.update()
            return

        if event.key() == Qt.Key.Key_Escape:
            store.clear()
            o.scroll_offset = 0
            o.update()
            return

        if event.key() == Qt.Key.Key_Tab:
            o.font_color = QColor(255,255,255) if o.font_color==QColor(0,0,0) else QColor(0,0,0)
            store.color = o.font_color
            store.rebuild_cache()
            o.update()
            return

        if event.key()==Qt.Key.Key_M and event.modifiers()&Qt.KeyboardModifier.ControlModifier:
            o.llm_controller.toggle_model()
            o.update()
            return

        if event.key()==Qt.Key.Key_Up:
            if(o.scroll_offset>0):
                o.scroll_offset -= o.height()//2
                o.update()
            return

        if event.key()==Qt.Key.Key_Down:
            if(o.bottom>o.height()//3):
                o.scroll_offset += o.height()//2
                o.update()
            return

        if event.key()==Qt.Key.Key_S and event.modifiers()&Qt.KeyboardModifier.ControlModifier:

            if not o.llm_controller.is_vision_mode:
                print("Switch to vision mode first")
                return

            path = o.media.capture_screen(len(store.input_blocks))
            store.input_blocks.append({"type":"image","value":path})
            o.update()
            return

        if event.key()==Qt.Key.Key_V and event.modifiers()&Qt.KeyboardModifier.ControlModifier:

            path = o.media.paste_image(len(store.input_blocks))

            if path:
                store.input_blocks.append({"type":"image","value":path})
                o.update()
                return

            text = QGuiApplication.clipboard().text()
            if text:
                store.current_text += text
                o.update()
                return

        if event.key() == Qt.Key.Key_F8 and not event.isAutoRepeat():
            if o.audio.listening:
                o.audio.stop()
            else:
                o.audio.start()

            o.update()
            return

        if o.loading:
            return

        if event.key()==Qt.Key.Key_Left:
            if store.current_text:
                store.next_text = store.current_text[-1] + store.next_text
                store.current_text = store.current_text[:-1]
                o.update()
            return

        if event.key()==Qt.Key.Key_Right:
            if store.next_text:
                store.current_text += store.next_text[0]
                store.next_text = store.next_text[1:]
                o.update()
            return

        if event.key()==Qt.Key.Key_Backspace:

            if store.current_text:
                store.current_text = store.current_text[:-1]
            elif store.input_blocks:
                store.input_blocks.pop()

            o.update()
            return

        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):

            if store.current_text.strip():
                store.input_blocks.append({"type":"text","value":store.current_text+store.next_text})
                store.current_text=""
                store.next_text=""

            o.call_llm()
            return

        text = event.text()
        if text.isprintable():
            store.current_text += text

        o.update()

    def release(self,event):

        o=self.overlay

        
        if event.key() == Qt.Key.Key_F8 and not event.isAutoRepeat():
            if o.audio.listening:
                o.audio.stop()
            else:
                o.audio.start()

            o.update()
            return


# =========================
# OVERLAY UI
# =========================
class Overlay(QWidget):

    def __init__(self):
        super().__init__()

        hf_token = os.getenv("HF_TOKEN")
        vision_token = os.getenv("VISION_TOKEN")

        if not hf_token:
            raise RuntimeError("HF_TOKEN not found in environment")

        if not vision_token:
            raise RuntimeError("VISION_TOKEN not found in environment")

        self.text_llm = LLM(token=hf_token)
        self.vision_llm = VisionLLM(token=vision_token)

        engine = None

        try:
            engine = AudioEngine("models/vosk-model-small-en-us-0.15")
            engine.chunk_ready.connect(self.on_audio_chunk)
            print("[AUDIO] Engine initialized ✅")

        except Exception as e:
            print("[AUDIO] Failed to initialize ❌")
            print("[AUDIO] Reason:", e)

        self.audio = AudioController(engine)
        self.media = MediaManager()
        self.llm_controller = LLMController(self.text_llm,self.vision_llm)

        self.font_color = QColor(255,255,255)
        self.font_normal = QFont("Monospace",14)
        self.font_bold = QFont("Monospace",14)
        self.font_bold.setBold(True)

        self.store = MessageStore(self.font_normal,self.font_color,500)
        self.input_controller = InputController(self)

        self.llm_controller.finished.connect(self.llm_finished)

        self.is_locked = False
        self.loading=False
        self.spinner_frames=["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        self.spinner_index=0
        self.scroll_offset=0

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|
                            Qt.WindowType.WindowStaysOnTopHint|
                            Qt.WindowType.Tool)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.bottom=0
        self.resize(520,420)

        screen=QGuiApplication.primaryScreen().availableGeometry()
        self.screen_width=screen.width()
        self.screen_height=screen.height()
        self.move(self.screen_width-540,self.screen_height-280)


        self.timer=QTimer()
        self.timer.timeout.connect(self.check_mouse_position)
        self.timer.start(50)

        self.hide()

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

        mode_tag="[VISION]" if self.llm_controller.is_vision_mode else "[TEXT]"

        audio_tag = "+[AUDIO]" if self.audio.engine is not None else ""
        title_layout = self.build_layout(
            f"AI Overlay Running {mode_tag}{audio_tag}",
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

        
        
        # 🤖 LLM LOADING
        if self.loading:

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