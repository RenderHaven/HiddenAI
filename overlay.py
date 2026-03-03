from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import (
    QPainter, QCursor, QGuiApplication,
    QTextLayout, QTextOption,
    QPixmap, QPen
)

class Overlay(QWidget):

    def __init__(self, app):
        super().__init__()

        self.app = app

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.resize(520, 420)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        self.move(self.screen_width - 540, self.screen_height - 280)

        self.scroll_offset = 0

        self.spinner_frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        self.spinner_index = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_mouse_position)
        self.timer.start(50)

        self.hide()

    # =========================
    # INPUT FORWARD
    # =========================
    def keyPressEvent(self, event):
        self.app.input_controller.handle(event)

    def keyReleaseEvent(self, event):
        self.app.input_controller.release(event)

    def clear_cache(self):
        self.scroll_offset =0
    # =========================
    # LAYOUT BUILDER
    # =========================
    def build_layout(self, text, font):
        layout = QTextLayout(text, font)
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(option)

        layout.beginLayout()
        y = 0
        width = self.width() - 20

        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            line.setPosition(QPointF(0, y))
            y += line.height()

        layout.endLayout()
        return layout

    def draw_layout(self, painter, layout, x, y, width):
        layout.beginLayout()
        height = 0

        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            line.setPosition(QPointF(x, y + height))
            height += line.height()

        layout.endLayout()
        layout.draw(painter, QPointF(0, 0))
        return height

    # =========================
    # PAINT
    # =========================
    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setPen(self.app.font_color)

        if self.app.is_locked:
            painter.setFont(self.app.font_normal)
            painter.drawText(self.width()-100, self.height()-10, "<running>")
            return

        content_width = self.width() - 20
        y = 25 - self.scroll_offset

        # TITLE
        model_name = self.app.llm_controller.llm.name
        mode_tag = "[VISION]" if self.app.llm_controller.llm.is_vision else "[TEXT]"
        audio_tag = "+[AUDIO]" if self.app.audio.engine else ""

        title_layout = self.build_layout(
            f"HiddenAI [{model_name}] {mode_tag}{audio_tag}",
            self.app.font_normal
        )

        y += self.draw_layout(painter, title_layout, 10, y, content_width) + 10

        painter.drawLine(QPointF(10, y), QPointF(self.width()-10, y))
        y += 15

        # MESSAGES
        ai_index = 0

        store=self.app.store
        
        
        for msg in store.messages:

            if msg["role"] == "user":
                layout = self.build_layout("> " + msg["content"], self.app.font_bold)
                y += self.draw_layout(painter, layout, 10, y, content_width) + 6

            else:
                doc = store.markdown_docs[ai_index]
                painter.save()
                painter.translate(10, y)
                doc.drawContents(painter)
                painter.restore()
                y += doc.size().height() + 6
                ai_index += 1


        # INPUTS

        y=self.draw_inputs(y,painter,content_width)

        if self.app.loading:
            spinner = self.spinner_frames[self.spinner_index]
            layout = self.build_layout(spinner, self.app.font_normal)
            y += self.draw_layout(painter, layout, 10, y, content_width)
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
            QTimer.singleShot(100, self.update)
        else:
            input_text = ">" + store.current_text + store.next_text

            input_layout = self.build_layout(
                input_text,
                self.app.font_bold
            )

            # ⭐ save layout info for cursor layer
            self._cursor_layout = input_layout

            y += self.draw_layout(painter, input_layout, 10, y, content_width)

            painter.save()
            self.draw_cursor(painter)
            painter.restore()

        self.bottom = y

    def draw_cursor(self,painter):
        store=self.app.store
        pen = QPen(self.app.font_color)
        pen.setWidth(2)
        painter.setPen(pen)

        layout = self._cursor_layout

        # caret index = after current_text
        cursor_index = len(">" + store.current_text)

        # find which wrapped line contains the cursor
        line = layout.lineForTextPosition(cursor_index)

        # get X inside that line
        cursor_x, _ = line.cursorToX(cursor_index)

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
        pass

    def draw_inputs(self,y,painter,content_width):

        for block in self.app.store.input_blocks:

            if block["type"] == "text":
                layout = self.build_layout(
                    "> " + block["value"],
                    self.app.font_bold
                )

                y += self.draw_layout(
                    painter,
                    layout,
                    10,
                    y,
                    content_width
                ) + 4

            elif block["type"] == "image":

                # Draw "> " prefix
                prefix = self.build_layout(
                    "> ",
                    self.app.font_bold
                )

                self.draw_layout(
                    painter,
                    prefix,
                    10,
                    y,
                    content_width
                )

                pixmap = QPixmap(block["value"])

                if not pixmap.isNull():

                    scaled = pixmap.scaledToWidth(
                        275,
                        Qt.TransformationMode.SmoothTransformation
                    )

                    painter.drawPixmap(
                        QPointF(30, y),
                        scaled
                    )

                    y += scaled.height() + 6
        return y
    # =========================
    # MOUSE CORNER TRIGGER
    # =========================
    def check_mouse_position(self):
        pos = QCursor.pos()
        margin = 10

        in_corner = (
            pos.x() >= self.screen_width - margin and
            pos.y() >= self.screen_height - margin
        )

        if in_corner:
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.setFocus()
        else:
            if self.isVisible():
                self.hide()