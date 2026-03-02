import requests

from PyQt6.QtCore import QObject, pyqtSignal,QThread


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
# LLM CONTROLLER
# =========================
class LLMController(QObject):

    finished = pyqtSignal(str)

    def __init__(self, llm):
        super().__init__()
        self.llm = llm

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
# ⭐ MULTIMODAL VISION LLM (OPENAI-COMPATIBLE)
# =========================
class LLM:
    def __init__(self, token: str,is_vision:bool=False,model:str="gpt-4o-mini"):
        # You can change provider later without touching overlay
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.is_vision = is_vision

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        self.system_prompt = (
            "You are a helpful assistant. your name is vikram. "
            "Keep responses short, clear, and straight to the point. "
            "Dont use emojis."
        )

        # ⭐ Vision capable model
        self.model = model

    
    def generate(self, messages: list) -> str:

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": self.system_prompt}],
                },
                *messages,
            ],
            "stream": False,
        }

        try:
            r = requests.post(self.url, headers=self.headers, json=payload, timeout=60)

            if r.status_code != 200:
                print("[LLM ERROR]", r.text)
                return "API error."

            data = r.json()
            return data["choices"][0]["message"]["content"]

        except Exception as e:
            print("[LLM EXCEPTION]", e)
            return "LLM failed."