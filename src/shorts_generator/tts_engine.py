"""Edge-TTS voiceover synthesis and synchronized subtitle generator."""

import os
import edge_tts

from .config import DEFAULT_VOICE
from .utils import srt_to_vtt


async def text_to_speech(
    text: str,
    output_audio: str = "output.mp3",
    output_subtitle: str = "output.srt",
    voice: str = DEFAULT_VOICE,
) -> tuple[str, str]:
    """Synthesizes text into high quality MP3 voiceover and synchronized SRT/VTT subtitles.

    Args:
        text: Voiceover narrative text to speak.
        output_audio: Destination path for generated MP3 audio file.
        output_subtitle: Destination path for generated SRT subtitle file.
        voice: Edge-TTS neural voice model name.

    Returns:
        tuple[str, str]: Paths to generated audio and subtitle files.
    """
    if not text.strip():
        raise ValueError("Seslendirilecek metin bulunamadı!")

    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()

    with open(output_audio, "wb") as f_audio:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f_audio.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)

    srt_content = submaker.get_srt()
    with open(output_subtitle, "w", encoding="utf-8") as f_sub:
        f_sub.write(srt_content)

    vtt_path = os.path.splitext(output_subtitle)[0] + ".vtt"
    with open(vtt_path, "w", encoding="utf-8") as f_vtt:
        f_vtt.write(srt_to_vtt(srt_content))

    return output_audio, output_subtitle
