# 🎬 AI YouTube Shorts Generator

An automated, end-to-end Python pipeline that generates highly engaging, viral-ready YouTube Shorts and TikToks. This tool handles everything from scriptwriting via LLM to voiceover generation, dynamic subtitle rendering, and audio mixing.

## ✨ Features
* **AI Scriptwriting:** Integrates with Google Gemini API to generate compelling, viral hooks and 30-second scripts in English, with automatic background search query tagging.
* **Dynamic Multi-Video Background:** Automatically queries the Pixabay Video API for thematic vertical/HD clips, downloads 3 distinct video clips (`bg_1.mp4`, `bg_2.mp4`, `bg_3.mp4`), and concatenates them seamlessly into an engaging dynamic background.
* **High-Quality TTS:** Uses `edge-tts` (`en-US-ChristopherNeural`) for deep, professional, and natural-sounding English voiceovers.
* **Ultra-Dynamic Captions (TikTok Style):** Automatically breaks down speech into 1-2 punchy words with enlarged high-contrast typography (88px Arial Bold, white text, 5px black outline) centered in the 9:16 vertical safe zone for maximum viewer retention.
* **Smart Audio Mixing:** Automatically detects `bg_music.mp3`, applies audio ducking (12% volume), and loops or trims the track to fit the video length.
* **Auto-Formatting & Resilient Fallbacks:** Strictly normalizes background clips to 1080x1920 (9:16 aspect ratio) at 24 FPS with center-crop and loop/trim matching the voiceover duration, falling back gracefully if fewer clips are available.

## 🚀 Tech Stack
* **Python 3.10+**
* **MoviePy** (Video processing & compositing)
* **Google Generative AI (Gemini 1.5 Flash)** (Script generation)
* **edge-tts / asyncio** (Asynchronous text-to-speech)
* **Pixabay Video API & requests** (Automated background footage discovery)

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/atillacam/youtube-shorts-generator.git
   cd youtube-shorts-generator
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables (.env):**
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   PIXABAY_API_KEY=your_pixabay_api_key_here
   ```

4. **Run the generator:**
   ```bash
   python main.py
   ```
   The final generated video will be exported as `final_shorts.mp4`.