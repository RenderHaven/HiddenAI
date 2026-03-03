import requests
import base64
from PyQt6.QtCore import QObject, pyqtSignal, QThread


# =========================
# LLM WORKER
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

    def __init__(self, llms):
        super().__init__()
        if not llms:
            raise ValueError("LLM list cannot be empty")

        self.llms = llms
        self.crt_indx = 0
        self.llm = self.llms[self.crt_indx]

        self.system_prompt = (
            "You are a helpful assistant. Your name is Vikram. "
            "Keep responses short, clear, and straight to the point. "
            "Use Markdown for formatting."
        )

        self.worker = None

    def toggle_model(self):
        self.crt_indx = (self.crt_indx + 1) % len(self.llms)
        self.llm = self.llms[self.crt_indx]
        print(f"[MODEL SWITCHED] -> {self.llm.name}")

    def send(self, messages, input_blocks):

        content_blocks = []

        for block in input_blocks:

            if block["type"] == "text":
                content_blocks.append({
                    "type": "text",
                    "text": block["value"]
                })

            elif block["type"] == "image":

                if not self.llm.is_vision:
                    self.finished.emit("Current model does not support images.")
                    return

                try:
                    with open(block["value"], "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")

                    content_blocks.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64}"
                        }
                    })

                except Exception as e:
                    self.finished.emit("Failed to read image.")
                    return

        api_messages = [{
            "role": "system",
            "content": [{
                "type": "text",
                "text": self.system_prompt
            }]
        }]

        for msg in messages[:-1]:
            api_messages.append({
                "role": msg["role"],
                "content": [{
                    "type": "text",
                    "text": msg["content"]
                }]
            })

        api_messages.append({
            "role": "user",
            "content": content_blocks
        })

        # Clean previous worker safely
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()

        self.worker = LLMWorker(self.llm, api_messages)
        self.worker.finished_signal.connect(self.finished.emit)
        self.worker.start()


# =========================
# BASE LLM
# =========================
class BaseLLM:
    def __init__(self):
        self.is_vision = False
        self.name = "BaseLLM"

    def generate(self, messages: list) -> str:
        raise NotImplementedError


# =========================
# OPENROUTER LLM
# =========================
class OpenRouterLLM(BaseLLM):

    def __init__(self,
                 is_vision: bool = False,
                 token: str = None,
                 model: str = "gpt-4o-mini",
                 name: str = "OpenRouterLLM"):

        super().__init__()

        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.is_vision = is_vision
        self.name = name
        self.token = token
        self.model = model

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def generate(self, messages: list) -> str:

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        try:
            r = requests.post(
                self.url,
                headers=self.headers,
                json=payload,
                timeout=60
            )

            if r.status_code != 200:
                print("[LLM ERROR]", r.text)
                return f"API error: {r.status_code}"

            data = r.json()

            if "choices" not in data:
                print("[INVALID RESPONSE]", data)
                return "Invalid API response."

            return data["choices"][0]["message"]["content"]

        except requests.Timeout:
            return "Request timed out."

        except Exception as e:
            print("[LLM EXCEPTION]", e)
            return "LLM failed."