# HiddenAI

HiddenAI is a lightweight, multimodal AI overlay for Linux. It provides a non-intrusive way to interact with Large Language Models (LLMs) directly from your desktop, supporting text queries, vision tasks (screen/image analysis), and voice input.

## Features

- **Minimalist Overlay**: Frameless, transparent UI that hides when not in use.
- **Multimodal Support**: Toggle between standard text LLMs and Vision-capable models.
- **Voice Input**: Integrated STT (Speech-to-Text) using the Vosk engine.
- **Visual Context**: Easily share your screen or clipboard images with the AI for analysis.
- **CLI Controller**: Simple command-line interface to manage the background process.

## Installation

1. **Setup Dependencies**: Ensure you have a Python virtual environment and the required packages installed.
   ```bash
   pip install -r requirements.txt
   ```
2. **Install CLI**: Use the provided install script to link the `hiddenAI` command to your local bin.
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
3. **Download Video/Audio Models**: Ensure the required Vosk model is placed in `models/vosk-model-small-en-us-0.15`.

## Configuration

Create a `.env` file in the project root with your API tokens:

```env
HF_TOKEN=your_huggingface_token
VISION_TOKEN=your_openrouter_token
```

## Usage

Manage the application using the `hiddenAI` command:

- `hiddenAI start`: Launch the overlay in the background.
- `hiddenAI stop`: Stop the running instance.
- `hiddenAI status`: Check the current status.
- `hiddenAI logs`: View live output logs.

### Interacting with the Overlay

The overlay is triggered by moving your mouse to the **bottom-right corner** of your screen. It will automatically hide when your mouse leaves the area.

#### Key Bindings

| Key | Action |
|-----|--------|
| `Ctrl + M` | Toggle between **[TEXT]** and **[VISION]** modes |
| `F8` | Start/Stop microphone (Voice Input) |
| `Ctrl + S` | Capture primary screen (Vision mode only) |
| `Ctrl + V` | Paste image or text from clipboard |
| `Enter` | Send current query to AI |
| `Tab` | Toggle font color (White/Black) |
| `Escape` | Clear chat history |
| `Up / Down` | Scroll through chat |
| `Delete` | Lock/Unlock overlay position |
| `Shift + Delete` | Quit the application |

## Technical Stack

- **GUI**: PyQt6
- **STT**: Vosk / Sounddevice
- **LLM API**: HuggingFace Router & OpenRouter
- **Environment**: Python 3.x
