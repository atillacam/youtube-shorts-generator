"""Google Gemini LLM script generation, scene tagging, and YouTube SEO metadata."""

import json
import re
from typing import Optional

from .config import GEMINI_API_KEY, DEFAULT_GEMINI_MODELS

# Support both new google-genai and classic google-generativeai SDKs
try:
    from google import genai
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False
    try:
        import google.generativeai as genai
    except ImportError:
        genai = None

if GEMINI_API_KEY and not HAS_NEW_GENAI and genai is not None:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        pass


def call_gemini(prompt: str, candidate_models: Optional[list[str]] = None) -> str:
    """Sends generation request to Gemini API with automatic model fallback chain."""
    if candidate_models is None:
        candidate_models = DEFAULT_GEMINI_MODELS

    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY ortam değişkeni bulunamadı. Lütfen .env dosyasını doldurun."
        )

    last_error = None
    if HAS_NEW_GENAI:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            for model_name in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    if response and response.text:
                        return response.text
                except Exception as e:
                    last_error = e
                    continue
        except Exception as e:
            last_error = e
    elif genai is not None:
        for model_name in candidate_models:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text
            except Exception as e:
                last_error = e
                continue
    else:
        raise RuntimeError("Google GenAI kütüphanesi bulunamadı. Lütfen 'pip install google-genai' kurun.")

    raise RuntimeError(f"Gemini API yanıt üretemedi: {last_error}")


def generate_shorts_script(topic: str) -> str:
    """Generates 30-second hyper-retention Shorts script and 3 visual scene search queries."""
    prompt = f"""
You are an elite viral content creator specializing in hyper-retention YouTube Shorts and TikToks.

Write the script entirely in English, keeping the tone aggressive, urgent, and mysterious. Do not include any Turkish words.

Topic: {topic}

Write the script using ultra-short, punchy sentences. Eliminate all filler words. Every single sentence must trigger curiosity. Keep the total spoken text around 60-75 words for a highly energetic, fast-paced 30-second delivery.

The script MUST follow this exact 3-part structure:
1. [0-3s] Hook: An electrifying, scroll-stopping statement or shocking question that violently grabs attention within the first 2 seconds. Make it bold, provocative, or alarming to shock the viewer.
2. [3-25s] Body: 2-3 rapid-fire, jaw-dropping facts delivered with extreme momentum and zero fluff. Every word must hit hard.
3. [25-30s] Call to Action (CTA): A sharp, psychological cliffhanger or controversial question demanding viewers to comment and subscribe before it is too late.

For each section, you MUST strictly use this exact format:
- Visual: [Brief description of fast-paced visual scene or footage]
- Voiceover: [The exact words spoken by the narrator]

CRITICAL RULES:
- Write exclusively in English.
- Voiceover lines must contain ONLY spoken dialogue. Never include bracketed directions, emojis, asterisks, or sound effect markers inside Voiceover lines.
- Keep sentences short (3-8 words per sentence). Speak with intensity and pace.

At the very end of your response, provide exactly 3 tailored English search queries for Pixabay video footage (one for each section: Hook, Body, CTA). Each query should consist of 2 to 4 highly visual, topic-specific keywords describing real footage (NOT generic words like just 'dark'):
HOOK_QUERY: [2-4 English keywords for Hook visual, e.g. 'coding screen terminal' or 'shocked human face']
BODY_QUERY: [2-4 English keywords for Body visual, e.g. 'artificial intelligence server' or 'matrix digital data']
CTA_QUERY: [2-4 English keywords for CTA visual, e.g. 'futuristic robot cyberpunk' or 'countdown digital timer']
"""
    return call_gemini(prompt)


def extract_scene_search_queries(script: str, topic: str = "") -> list[str]:
    """Extracts 3 scene-specific video search queries from script with intelligent fallbacks."""
    queries = []
    for tag in ["HOOK_QUERY", "BODY_QUERY", "CTA_QUERY"]:
        match = re.search(rf"{tag}\s*:\s*\[?([^\r\n\]]+)\]?", script, re.IGNORECASE)
        if match:
            clean_q = match.group(1).strip()
            if clean_q:
                queries.append(clean_q)

    # Fallback to single SEARCH_QUERY if available
    if len(queries) < 3:
        m_single = re.search(r"SEARCH_QUERY\s*:\s*\[?([^\r\n\]]+)\]?", script, re.IGNORECASE)
        if m_single:
            base_q = m_single.group(1).strip()
            while len(queries) < 3:
                queries.append(base_q)

    # Topic-derived fallback keywords
    if not queries:
        clean_topic = re.sub(r"[^a-zA-Z0-9\s]", " ", topic).strip()
        words = [w for w in clean_topic.split() if len(w) > 3]
        base = " ".join(words[:2]) if words else "technology"
        queries = [f"{base} visual", f"{base} network", f"{base} cinematic"]

    while len(queries) < 3:
        queries.append(queries[-1] if queries else "cinematic technology")

    return queries[:3]


def extract_search_query(script: str, default: str = "technology") -> str:
    """Backward compatibility wrapper returning single primary search keyword."""
    queries = extract_scene_search_queries(script)
    return queries[0] if queries else default


def extract_voiceover(script: str) -> str:
    """Extracts only pure spoken narrator dialogue from generated script."""
    prefix = r"(?:^|\n)\s*(?:[-*•#\d\.\(\)]+\s*)?(?:\*\*|\*)?(?:Voiceover|Voice-over|Narration|Voice|Seslendirme|Dış\s*Ses|Ses|Metin)(?:\*\*|\*)?\s*:\s*"
    delimiter = r"(?=(?:\n\s*(?:[-*•#\d\.\(\)]+\s*)?(?:\*\*|\*)?(?:Visual|Visuals|Scene|Video|Voiceover|Voice-over|Narration|Voice|Hook|Body|CTA|Call\s*to\s*Action|SEARCH_QUERY|IMAGE_PROMPT|Image_Prompt|Image|Görsel|Seslendirme|Dış\s*Ses|Kanca|Gövde|Kapanış|Sahne|\d+[\.\)])|\Z))"
    pattern = prefix + r"(.*?)" + delimiter

    matches = re.findall(pattern, script, flags=re.IGNORECASE | re.DOTALL)

    voiceover_parts = []
    for m in matches:
        cleaned = m.strip()
        if cleaned:
            voiceover_parts.append(cleaned)

    if not voiceover_parts:
        lines = script.splitlines()
        ignore_prefixes = (
            "visual", "visuals", "scene", "video", "footage", "b-roll",
            "hook", "body", "cta", "call to action", "note:", "title:",
            "search_query", "image_prompt", "image prompt", "image:", "image",
            "görsel", "kanca", "gövde", "kapanış", "sahne", "ekran", "not:"
        )
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if re.match(r"^\[?\d+[-–]\d+\s*s[en]*\]?", stripped, re.IGNORECASE):
                continue

            cleaned_prefix = re.sub(r"^[\*\-\d\.\s\[\]]+", "", stripped).lower()
            if any(cleaned_prefix.startswith(tag) for tag in ignore_prefixes):
                continue

            match_vo = re.match(r"^[\*\-\s]*(?:Voiceover|Voice-over|Narration|Voice|Seslendirme|Dış\s*Ses|Ses|Metin)\s*:\s*(.*)", stripped, re.IGNORECASE)
            if match_vo:
                voiceover_parts.append(match_vo.group(1).strip())
            else:
                voiceover_parts.append(stripped)

    full_text = " ".join(voiceover_parts)
    full_text = re.sub(
        r"[\(\[][^\)\]]*(?:camera|visual|zoom|effect|sfx|music|sound effect|smile|cut|scene|b-roll|footage|kamera|görsel|zoom|efekt|müzik|ses efekti|gülümse|kesme|sahne)[^\)\]]*[\)\]]",
        "",
        full_text,
        flags=re.IGNORECASE,
    )
    full_text = re.sub(r"[\*_#`]", "", full_text)
    full_text = re.sub(r"\s+", " ", full_text).strip()

    return full_text


def generate_youtube_metadata(topic: str, script: str) -> dict:
    """Generates high CTR title, hashtag description, and SEO search tags."""
    fallback_data = {
        "title": f"{topic} #shorts",
        "description": f"{topic}\n\n#shorts #viral #facts",
        "tags": ["shorts", "viral", "facts", "ai", "trending"],
    }
    if not GEMINI_API_KEY:
        return fallback_data

    prompt = f"""
You are an elite YouTube SEO specialist. Based on the topic and script below, generate viral YouTube Shorts metadata.

Topic: {topic}
Script:
{script[:500]}

Rules:
- The title, description, and tags MUST be written in English to match the English voiceover.
- Title must be high CTR, curiosity-inducing, under 60 characters, and end with #shorts.
- Description must be 2 punchy sentences with 4-5 relevant hashtags.
- Tags must be 5-8 hyper-relevant search tags.

Return STRICTLY a valid JSON object with the following keys and nothing else:
{{
  "title": "A short, viral, click-worthy YouTube title with #shorts under 60 characters",
  "description": "An engaging 2-sentence description with 4-5 relevant hashtags",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}
"""
    try:
        response_text = call_gemini(prompt)
        cleaned = response_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        return json.loads(cleaned)
    except Exception:
        return fallback_data
