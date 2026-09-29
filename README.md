# 🎬 AI YouTube Shorts Generator

An automated, end-to-end Python pipeline that generates highly engaging, viral-ready YouTube Shorts and TikToks. This tool handles everything from scriptwriting via LLM to voiceover generation, dynamic subtitle rendering, and audio mixing.

## ✨ Features
* **AI Scriptwriting:** Integrates with the Google Gemini API to generate compelling, viral hooks and 30-second scripts in English.
* **High-Quality TTS:** Uses `edge-tts` (en-US-ChristopherNeural) for deep, professional, and natural-sounding voiceovers.
* **Dynamic Captions (SubMaker):** Automatically generates and synchronizes word-by-word subtitles with high-contrast styling (white text, thick black stroke) optimized for the 9:16 safe zone.
* **Smart Audio Mixing:** Automatically detects `bg_music.mp3`, applies audio ducking (12% volume), and loops or trims the track to fit the video length.
* **Auto-Formatting:** Ensures the final output is strictly 1080x1920 (9:16 aspect ratio) at 24 FPS, auto-cropping or looping background videos as needed.

## 🚀 Tech Stack
* **Python 3.10+**
* **MoviePy** (Video processing & compositing)
* **Google Generative AI (Gemini 1.5 Flash)** (Script generation)
* **edge-tts / asyncio** (Asynchronous text-to-speech)

## 🛠️️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/atillacam/youtube-shorts-generator.git](https://github.com/atillacam/youtube-shorts-generator.git)
   cd youtube-shorts-generator