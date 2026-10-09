# 🎬 AI YouTube Shorts Generator

An automated, end-to-end Python pipeline that generates highly engaging, viral-ready YouTube Shorts and TikToks. This tool handles everything from scriptwriting via LLM to voiceover generation, dynamic subtitle rendering, and audio mixing.

## ✨ Features
* **AI Scriptwriting & Scene B-Roll Tagging:** Integrates with Google Gemini API (`google-genai` & `google-generativeai`) to generate compelling viral scripts and 3 distinct scene-specific visual queries (`HOOK_QUERY`, `BODY_QUERY`, `CTA_QUERY`).
* **Dedicated Project Archiving (`outputs/`):** Automatically creates a clean, dated project folder (`outputs/YYYYMMDD_HHMMSS_<slug>/`) storing the generated video, metadata, voiceover, subtitles, script, and raw background footage. Never overwrites past projects.
* **Intelligent Multi-Scene Pixabay Discovery:** Automatically searches and downloads 3 distinct 9:16 portrait/HD background clips matching the exact narrative beat of each scene, with randomized diversity to prevent repetitive footage across videos.
* **Proportional Scene Pacing:** Evenly allocates and trims each background video to synchronize directly with the spoken narrative (Hook, Body, CTA), ensuring every scene transition is visually impactful.
* **Interactive CLI & Custom Arguments:** Run interactively or supply arguments directly (`--topic`, `--voice`, `--bg-count`, `--output`, `--music`).
* **Automated YouTube SEO Metadata:** Produces viral English titles with `#shorts`, 2-sentence descriptions with hashtags, and SEO search tags.
* **High-Quality TTS:** Uses `edge-tts` (`en-US-ChristopherNeural`, `en-GB-RyanNeural`, etc.) for deep, professional, and natural-sounding voiceovers.
* **Ultra-Dynamic Captions (TikTok Style):** Breaks down speech into 1-2 punchy words with enlarged high-contrast typography (88-96px Impact/Arial Bold, uppercase, drop shadow) centered in the 9:16 safe zone.
* **Smart Audio Mixing & Ducking:** Automatically loops or trims `bg_music.mp3`, applying volume ducking (12%) beneath the voiceover.

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