# 🎬 AI YouTube Shorts & TikTok Generator

An automated, end-to-end Python production pipeline that generates highly engaging, viral-ready YouTube Shorts and TikToks. This tool handles everything from LLM scriptwriting to neural voiceover synthesis, intelligent Pixabay B-roll footage discovery, dynamic 9:16 subtitle rendering, and audio ducking composition.

---

## ✨ Features

* **AI Scriptwriting & Scene B-Roll Tagging:** Integrates with Google Gemini API (`google-genai` & `google-generativeai`) to generate compelling viral scripts and 3 distinct scene-specific visual queries (`HOOK_QUERY`, `BODY_QUERY`, `CTA_QUERY`).
* **Dedicated Project Archiving (`outputs/`):** Automatically creates a clean, dated project folder (`outputs/YYYYMMDD_HHMMSS_<slug>/`) storing the generated video, metadata, voiceover, subtitles, script, and raw background footage. Never overwrites past projects.
* **Intelligent Multi-Scene Pixabay Discovery:** Searches and downloads 3 distinct 9:16 portrait/HD background clips matching the narrative beat of each scene, with randomized candidate diversity to prevent repetitive footage across videos.
* **Proportional Scene Pacing:** Evenly allocates and trims each background video to synchronize directly with the spoken narrative (Hook, Body, CTA), ensuring every scene transition is visually impactful.
* **Interactive CLI & Custom Arguments:** Run interactively or supply arguments directly (`--topic`, `--voice`, `--bg-count`, `--output`, `--music`, `--font-size`).
* **Automated YouTube SEO Metadata:** Produces viral English titles with `#shorts`, 2-sentence descriptions with hashtags, and SEO search tags.
* **High-Quality Neural TTS:** Uses `edge-tts` (`en-US-ChristopherNeural`, `en-GB-RyanNeural`, etc.) for deep, professional, and natural-sounding voiceovers.
* **Ultra-Dynamic Captions (TikTok Style):** Breaks down speech into 1-2 punchy words with enlarged high-contrast typography (88-96px Impact/Arial Bold, uppercase, drop shadow) centered in the 9:16 safe zone.
* **Smart Audio Mixing & Ducking:** Automatically loops or trims `bg_music.mp3`, applying volume ducking (12%) beneath the voiceover.
* **Modular Architecture:** Fully decoupled modules for configuration, LLM script generation, media downloading, speech synthesis, and video composition.

---

## 🏛️ Project Architecture

```
youtube-shorts-generator/
├── src/
│   └── shorts_generator/
│       ├── __init__.py           # Package exports & version
│       ├── config.py             # Global constants, paths, and environment settings
│       ├── utils.py              # Slugify, subtitle parser, cue chunking, and VTT tools
│       ├── script_generator.py   # Gemini LLM orchestration, scene queries, and SEO metadata
│       ├── downloader.py         # Pixabay Video API client with 9:16 aspect ratio scoring
│       ├── tts_engine.py         # Edge-TTS voice synthesis & SubMaker timing generator
│       ├── video_compositor.py   # MoviePy 1.x & 2.x compositing, typography, and audio ducking
│       └── pipeline.py           # End-to-end ShortsPipeline orchestrator
├── tests/
│   ├── __init__.py
│   ├── test_utils.py             # Tests for slugification, cue chunking, and subtitles
│   ├── test_config.py            # Tests for configuration defaults and dimensions
│   └── test_script_parser.py     # Tests for script tags, scene queries, and voiceover isolation
├── .github/
│   └── workflows/
│       └── ci.yml                # Automated CI matrix across Python 3.10, 3.11, 3.12
├── main.py                       # CLI entrypoint and backward-compatible module wrapper
├── pyproject.toml                # Project packaging metadata and build definitions
├── requirements.txt              # Production dependencies
└── README.md                     # Documentation
```

---

## 🚀 Tech Stack

* **Python 3.10+**
* **MoviePy** (Video processing, crop transformation & compositing)
* **Google GenAI SDK** (`google-genai` & `google-generativeai`)
* **edge-tts / asyncio** (Asynchronous neural text-to-speech)
* **Pixabay Video API & requests** (Automated background footage discovery)

---

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

---

## 🎬 Usage

### Interactive Mode
```bash
python main.py
```
Prompts for a topic interactively in the terminal.

### Custom Arguments
```bash
python main.py --topic "How AI is revolutionizing software development" --voice en-US-ChristopherNeural --output final_shorts.mp4
```

### CLI Options

| Flag | Description | Default |
|---|---|---|
| `-t`, `--topic` | Video topic or prompt | Interactive prompt / Default |
| `-v`, `--voice` | Edge-TTS voice model | `en-US-ChristopherNeural` |
| `-c`, `--bg-count` | Number of Pixabay background clips | `3` |
| `-o`, `--output` | Final video file name | `final_shorts.mp4` |
| `-m`, `--music` | Path to background music | `bg_music.mp3` |
| `--font-size` | Subtitle typography font size | `96` |
| `--non-interactive` | Disable interactive prompts | `False` |

---

## 🧪 Running Tests

To run the unit test suite locally:
```bash
python -m unittest discover tests -v
```

All tests run without requiring external network connections or active API keys.

---

## 📄 License

This project is licensed under the MIT License.