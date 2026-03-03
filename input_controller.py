from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
# =========================
# INPUT CONTROLLER
# =========================
class InputController:

    def __init__(self, app):
        self.app = app

    def handle(self, event):

        
        app=self.app
        o = app.overlay
        store = app.store

        if event.key() == Qt.Key.Key_Delete:

            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                QApplication.quit()
                return

            o.is_locked = not o.is_locked
            o.update()
            return

        if event.key() == Qt.Key.Key_Escape:
            app.refresh()
            return

        if event.key() == Qt.Key.Key_Tab:
            app.font_color = QColor(255,255,255) if app.font_color==QColor(0,0,0) else QColor(0,0,0)
            store.color = app.font_color
            store.rebuild_cache()
            o.update()
            return

        if event.key()==Qt.Key.Key_M and event.modifiers()&Qt.KeyboardModifier.ControlModifier:
            app.toggle_model()
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

            if not app.llm_controller.llm.is_vision:
                print("Switch to vision mode first")
                return

            path = app.media.capture_screen(len(store.input_blocks))
           
            if path:
                store.input_blocks.append({"type":"image","value":path})
                o.update()
            return

        if event.key()==Qt.Key.Key_V and event.modifiers()&Qt.KeyboardModifier.ControlModifier:

            path = app.media.paste_image(len(store.input_blocks))
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
            if app.audio.listening:
                app.audio.stop()
            else:
                app.audio.start()

            o.update()
            return

        if self.app.loading or not self.app.is_working:
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
            input_text = store.current_text+store.next_text
            if input_text.strip():
                store.input_blocks.append({"type":"text","value":input_text})
                store.current_text=""
                store.next_text=""

            app.call_llm()
            return

        text = event.text()
        if text.isprintable():
            store.current_text += text

        o.update()

    def release(self,event):
        
        if event.key() == Qt.Key.Key_F8 and not event.isAutoRepeat():
            if self.app.audio.listening:
                self.app.audio.stop()
            else:
                self.app.audio.start()

            self.app.overlay.update()
            return