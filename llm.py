import requests


# =========================
# HF ROUTER LLM (TEXT ONLY RIGHT NOW)
# =========================
class LLM:
    def __init__(self, token: str):
        self.url = "https://router.huggingface.co/v1/chat/completions"

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        self.system_prompt = (
            "You are a helpful assistant. your name is vikram. "
            "Keep responses short, clear, and straight to the point. "
            "Dont use emojis."
        )

        self.model = "mistralai/Mistral-7B-Instruct-v0.2:together"

        self.is_vision = False

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
                return "Error calling HuggingFace router."

            data = r.json()
            return data["choices"][0]["message"]["content"]

        except Exception as e:
            print("[LLM EXCEPTION]", e)
            return "LLM request failed."


# =========================
# ⭐ MULTIMODAL VISION LLM (OPENAI-COMPATIBLE)
# =========================
class VisionLLM:
    def __init__(self, token: str):
        # You can change provider later without touching overlay
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.is_vision = True

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "HiddenAI"
        }

        self.system_prompt = (
            "You are a helpful assistant. your name is vikram. "
            "Keep responses short, clear, and straight to the point. "
            "Dont use emojis."
        )

        # ⭐ Vision capable model
        self.model = "gpt-4o-mini"

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
                print("[VISION LLM ERROR]", r.text)
                return "Vision API error."

            data = r.json()
            return data["choices"][0]["message"]["content"]

        except Exception as e:
            print("[VISION LLM EXCEPTION]", e)
            return "Vision LLM failed."