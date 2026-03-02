from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
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
            o.refresh()
            return

        if event.key() == Qt.Key.Key_Tab:
            o.font_color = QColor(255,255,255) if o.font_color==QColor(0,0,0) else QColor(0,0,0)
            store.color = o.font_color
            store.rebuild_cache()
            o.update()
            return

        if event.key()==Qt.Key.Key_M and event.modifiers()&Qt.KeyboardModifier.ControlModifier:
            o.toggle_model()
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

            if not o.llm_controller.llm.is_vision:
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

        if o.loading or not o.is_working:
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