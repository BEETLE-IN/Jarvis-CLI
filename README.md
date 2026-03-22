# J.A.R.V.I.S. CLI
### *Just A Rather Very Intelligent System*

![JARVIS Banner](assets/banner.png)

Welcome to **J.A.R.V.I.S. CLI**, a professional-grade virtual assistant inspired by Tony Stark's legendary AI. This assistant combines advanced Large Language Models (LLMs) with high-quality real-time speech-to-text and text-to-speech capabilities to bring the Iron Man experience to your terminal.

---

## 🎙️ Real JARVIS Voice
This project is equipped with the **Real JARVIS Voice**, meticulously crafted through advanced voice cloning. It captures the polite, witty, and formal tone of the original cinematic AI, ensuring every response feels authentic.

---

## ✨ Features

- **Dual Interaction Modes**: Seamlessly switch between **Text** and **Voice** input.
- **Intelligent Brain**: Powered by **Groq Llama 3.1 8B** for lightning-fast, witty, and context-aware responses.
- **Real JARVIS TTS**: High-fidelity speech synthesis using the **Pocket TTS** engine.
- **Speech Recognition**: Utilizes **OpenAI Whisper** for high-accuracy voice transcription.
- **System Automation**:
  - **App Control**: Open/Close any installed Windows application (e.g., VS Code, Chrome, Spotify).
  - **Web Commands**: Open specific websites in preferred browsers.
  - **File Operations**: Create, delete, read, and manage files/folders on Desktop or local drives.
  - **Conversation Memory**: Remembers your previous interactions within the session.
- **Dynamic CLI UI**: Beautiful ASCII art and colored terminal output for a premium experience.

---

## 🚀 Setup Instructions

### 1. Prerequisites
- **Python**: 3.10 or higher.
- **System Tools**: 
  - `FFmpeg` (Required for audio processing). Ensure it's in your system PATH.
  - `winsound` (Default on Windows).

### 2. Installation
Clone the repository and install the core dependencies:

```bash
pip install groq sounddevice scipy speech_recognition openai-whisper
```
*Note: `pocket-tts` can be run directly using `uvx` without manual installation.*

### 3. Environment Configuration
- **Groq API Key**: Obtain your key from [Groq Cloud](https://console.groq.com/) and set it as an environment variable:
  ```powershell
  $env:GROQ_API_KEY = "your_key_here"
  ```
- **FFmpeg Path**: Ensure the `ffmpeg_path` variable in `jarvis.py` points to your local FFmpeg installation.

---

## 🖥️ Running the Project

To experience the full capability of JARVIS, follow these two steps:

### Step 1: Start the Pocket TTS Server
The text-to-speech engine runs most efficiently as a standalone server. This project recommends using `uv` for seamless execution:

```bash
uvx pocket-tts serve
```
*This command will automatically download and start the local TTS server at `http://localhost:8000`. Keep this window open.*

### Step 2: Initialize JARVIS
In your main terminal, run the following command:

```bash
python jarvis.py
```

---

## 🛠️ Usage
- **Type `mode`**: Toggles between text and voice input.
- **Say "Switch to voice"**: Activates the microphone.
- **Automation Examples**:
  - *"Open YouTube and search for Stark Industries."*
  - *"Create a new folder named 'Lab_Data' on my desktop."*
  - *"Close VS Code."*
- **Exit**: Just say *"exit"* or press `Ctrl + C` to put JARVIS on standby.

---

## 📄 License
This project is created for educational and fan-appreciation purposes. Enjoy your personal AI assistant!
