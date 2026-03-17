import os
from dotenv import load_dotenv
import sys
load_dotenv()
from hiddenAi import HiddenAiApp
from overlay import Overlay
from llm import OpenRouterLLM

if __name__ == "__main__":
    llms=[
    OpenRouterLLM(token=os.getenv("OPENROUTER_TOKEN"),name="OpenRouterLLM Text"),
    OpenRouterLLM(is_vision=True,token=os.getenv("OPENROUTER_TOKEN"),name="OpenRouterLLM Vision")
    ]
    
    app = HiddenAiApp(sys.argv,llms)
    app.overlay=Overlay(app)
    sys.exit(app.exec())