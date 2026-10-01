# 🎬 AI YouTube Shorts Generator

An automated, end-to-end Python pipeline that generates highly engaging, viral-ready YouTube Shorts and TikToks. This tool handles everything from scriptwriting via LLM to voiceover generation, dynamic subtitle rendering, and audio mixing.

## ✨ Features
* **AI Scriptwriting:** Integrates with Google Gemini API (`google-genai` & `google-generativeai`) to generate compelling, viral hooks and 30-second scripts with automatic background search query tagging.
* **Interactive CLI & Custom Arguments:** Run interactively or supply arguments directly (`--topic`, `--voice`, `--bg-count`, `--output`, `--music`).
* **Automated YouTube SEO Metadata:** Automatically produces viral title with `#shorts`, 2-sentence description with hashtags, and SEO tags exported to `*_metadata.json`.
* **Dynamic Multi-Video Background:** Automatically queries the Pixabay Video API for thematic vertical/HD clips, downloads distinct video clips (`bg_1.mp4`, `bg_2.mp4`, `bg_3.mp4`), and concatenates them seamlessly into an engaging dynamic background.
* **High-Quality TTS:** Uses `edge-tts` (`en-US-ChristopherNeural`, `en-GB-RyanNeural`, etc.) for deep, professional, and natural-sounding voiceovers.
* **Ultra-Dynamic Captions (TikTok Style):** Automatically breaks down speech into 1-2 punchy words with enlarged high-contrast typography (88-96px Impact/Arial Bold, uppercase, drop shadow) centered in the 9:16 vertical safe zone for maximum viewer retention.
* **Smart Audio Mixing:** Automatically detects `bg_music.mp3`, applies audio ducking (12% volume), and loops or trims the track to fit the video length.
* **Auto-Formatting & Resilient Fallbacks:** Strictly normalizes background clips to 1080x1920 (9:16 aspect ratio) at 24 FPS with center-crop and loop/trim matching the voiceover duration, falling back gracefully if fewer clips are available.

## 🚀 Tech Stack
* **Python 3.10+**
* **MoviePy** (Video processing & compositing)
* **Google GenAI SDK** (`google-genai` & `google-generativeai`)
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
   
   * **Interactive Mode:**
     ```bash
     python main.py
     ```
     Prompts for topic interactively in terminal.

   * **With Custom Arguments:**
     ```bash
     python main.py --topic "The psychological trick behind optical illusions" --voice en-US-ChristopherNeural --output illusions.mp4
     ```

   * **CLI Options:**
     | Flag | Description | Default |
     |---|---|---|
     | `-t`, `--topic` | Video topic or prompt | Interactive prompt / Default |
     | `-v`, `--voice` | Edge-TTS voice model | `en-US-ChristopherNeural` |
     | `-c`, `--bg-count` | Number of Pixabay background clips | `3` |
     | `-o`, `--output` | Final video file name | `final_shorts.mp4` |
     | `-m`, `--music` | Path to background music | `bg_music.mp3` |
     | `--font-size` | Subtitle typography font size | `96` |
     | `--non-interactive` | Disable interactive prompts | `False` |

   The pipeline outputs both the finished video (`final_shorts.mp4`) and SEO metadata (`final_shorts_metadata.json`).