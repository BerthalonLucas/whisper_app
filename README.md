# Whisper Voice Transcription App

A real-time voice transcription desktop application powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (large-v3 model). Record audio with a hotkey and have it automatically transcribed and pasted at your cursor position.

## Features

- **Real-time voice recording** — toggle recording with a keyboard shortcut
- **Automatic transcription** — uses the Whisper large-v3 model via faster-whisper
- **Auto-paste** — transcribed text is automatically inserted at your cursor position
- **GPU acceleration** — automatically detects and uses CUDA when available
- **Visual indicators** — on-screen overlays show recording and transcription status
- **Accent support** — full support for accented characters (French, etc.)
- **Re-inject** — re-paste the last transcription with a shortcut

## Requirements

- Python 3.9+
- Windows (uses Windows-specific GUI overlays and hotkeys)
- A microphone
- (Optional) NVIDIA GPU with CUDA for faster transcription

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/BerthalonLucas/whisper_app.git
   cd whisper_app
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Install CUDA support** for GPU acceleration — install [PyTorch with CUDA](https://pytorch.org/get-started/locally/) or ensure `ctranslate2` can detect your GPU.

## Usage

### Run the application

```bash
python app.py
```

Or use the provided batch file on Windows:

```bash
launch_whisper.bat
```

### Keyboard shortcuts

| Shortcut             | Action                                  |
|----------------------|-----------------------------------------|
| `Ctrl + F9`          | Start / Stop recording                  |
| `Ctrl + Shift + F9`  | Re-paste the last transcription         |
| `Ctrl + F10`         | Quit the application                    |

### Transcribe an audio file

You can also transcribe an existing audio file from the command line:

```bash
python transcribe.py path/to/audio.wav
```

## How it works

1. Press `Ctrl + F9` to start recording — a red **● REC** indicator appears on screen.
2. Press `Ctrl + F9` again to stop — the audio is sent to the Whisper model for transcription.
3. A blue progress overlay shows transcription status.
4. Once complete, the transcribed text is automatically pasted at your current cursor position.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
