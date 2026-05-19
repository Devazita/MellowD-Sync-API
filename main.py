"""
MellowD Sync — Backend API
FastAPI + edge-tts
Endpoints:
  GET  /voices          → list of available Neural voices
  POST /tts             → text → MP3 audio (streaming)
  POST /tts/mp3         → text → MP3 file download
  POST /video           → text + frames → WebM video
  GET  /health          → status check
"""

import os, io, asyncio, tempfile, uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel
import edge_tts

app = FastAPI(title="MellowD Sync API", version="1.0.0")

# CORS — allow devazita.com and localhost for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://devazita.com",
        "https://www.devazita.com",
        "http://localhost",
        "http://127.0.0.1",
        "*",  # remove in production if you want strict origin
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Voice list (Neural voices only, English) ──────────────────────────────
VOICES = [
    # American Male
    {"id": "en-US-GuyNeural",         "name": "Guy",         "gender": "Male",   "accent": "American"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher", "gender": "Male",   "accent": "American"},
    {"id": "en-US-EricNeural",        "name": "Eric",        "gender": "Male",   "accent": "American"},
    {"id": "en-US-RogerNeural",       "name": "Roger",       "gender": "Male",   "accent": "American"},
    {"id": "en-US-SteffanNeural",     "name": "Steffan",     "gender": "Male",   "accent": "American"},
    {"id": "en-US-AndrewNeural",      "name": "Andrew",      "gender": "Male",   "accent": "American"},
    # American Female
    {"id": "en-US-JennyNeural",       "name": "Jenny",       "gender": "Female", "accent": "American"},
    {"id": "en-US-AriaNeural",        "name": "Aria",        "gender": "Female", "accent": "American"},
    {"id": "en-US-EmmaNeural",        "name": "Emma",        "gender": "Female", "accent": "American"},
    {"id": "en-US-MichelleNeural",    "name": "Michelle",    "gender": "Female", "accent": "American"},
    {"id": "en-US-MonicaNeural",      "name": "Monica",      "gender": "Female", "accent": "American"},
    {"id": "en-US-AnaNeural",         "name": "Ana",         "gender": "Female", "accent": "American"},
    {"id": "en-US-AvaNeural",         "name": "Ava",         "gender": "Female", "accent": "American"},
    {"id": "en-US-NancyNeural",       "name": "Nancy",       "gender": "Female", "accent": "American"},
    # British
    {"id": "en-GB-RyanNeural",        "name": "Ryan",        "gender": "Male",   "accent": "British"},
    {"id": "en-GB-ThomasNeural",      "name": "Thomas",      "gender": "Male",   "accent": "British"},
    {"id": "en-GB-SoniaNeural",       "name": "Sonia",       "gender": "Female", "accent": "British"},
    {"id": "en-GB-LibbyNeural",       "name": "Libby",       "gender": "Female", "accent": "British"},
    {"id": "en-GB-MaisieNeural",      "name": "Maisie",      "gender": "Female", "accent": "British"},
    # Australian
    {"id": "en-AU-WilliamNeural",     "name": "William",     "gender": "Male",   "accent": "Australian"},
    {"id": "en-AU-NatashaNeural",     "name": "Natasha",     "gender": "Female", "accent": "Australian"},
    # Canadian
    {"id": "en-CA-LiamNeural",        "name": "Liam",        "gender": "Male",   "accent": "Canadian"},
    {"id": "en-CA-ClaraNeural",       "name": "Clara",       "gender": "Female", "accent": "Canadian"},
]


# ── Request models ────────────────────────────────────────────────────────
class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-GuyNeural"
    rate: str = "+0%"    # e.g. "+20%" or "-10%"
    pitch: str = "+0Hz"  # e.g. "+5Hz"


class VideoRequest(BaseModel):
    text: str
    voice: str = "en-US-GuyNeural"
    rate: str = "+0%"
    highlight_color: str = "#7F77DD"
    bg_color: str = "#ffffff"
    text_color: str = "#1a1a2e"
    font_size: int = 32
    width: int = 1280
    height: int = 720


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "MellowD Sync API"}


@app.get("/voices")
async def get_voices():
    """Return grouped list of Neural voices."""
    grouped = {}
    for v in VOICES:
        g = v["accent"] + " " + v["gender"]
        grouped.setdefault(g, []).append(v)
    return {"voices": VOICES, "grouped": grouped}


@app.post("/tts")
async def tts_stream(req: TTSRequest):
    """
    Stream MP3 audio for the given text.
    Frontend uses this for real-time playback via Audio element.
    """
    if not req.text.strip():
        raise HTTPException(400, "Text is empty")
    if len(req.text) > 10000:
        raise HTTPException(400, "Text too long (max 10000 chars)")

    voice_ids = [v["id"] for v in VOICES]
    if req.voice not in voice_ids:
        req.voice = "en-US-GuyNeural"

    async def generate():
        communicate = edge_tts.Communicate(
            text=req.text,
            voice=req.voice,
            rate=req.rate,
            pitch=req.pitch,
        )
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    return StreamingResponse(
        generate(),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
        }
    )


@app.post("/tts/mp3")
async def tts_download(req: TTSRequest):
    """
    Return a downloadable MP3 file.
    Used by Save as MP3 button.
    """
    if not req.text.strip():
        raise HTTPException(400, "Text is empty")
    if len(req.text) > 10000:
        raise HTTPException(400, "Text too long (max 10000 chars)")

    voice_ids = [v["id"] for v in VOICES]
    if req.voice not in voice_ids:
        req.voice = "en-US-GuyNeural"

    tmp_path = f"/tmp/{uuid.uuid4()}.mp3"
    try:
        communicate = edge_tts.Communicate(
            text=req.text,
            voice=req.voice,
            rate=req.rate,
            pitch=req.pitch,
        )
        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": 'attachment; filename="mellowd_sync.mp3"',
                "Content-Length": str(len(audio_bytes)),
            }
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/video")
async def generate_video(req: VideoRequest):
    """
    Generate a video of the text being read with word-by-word highlight.
    Returns a WebM/MP4 file.
    """
    if not req.text.strip():
        raise HTTPException(400, "Text is empty")
    if len(req.text) > 5000:
        raise HTTPException(400, "Text too long for video (max 5000 chars)")

    tmp_audio = f"/tmp/{uuid.uuid4()}.mp3"
    tmp_video = f"/tmp/{uuid.uuid4()}.mp4"

    try:
        from PIL import Image, ImageDraw, ImageFont
        from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeAudioClip
        import numpy as np

        # 1. Generate audio and word timings
        communicate = edge_tts.Communicate(
            text=req.text,
            voice=req.voice,
            rate=req.rate,
        )

        word_timings = []  # [(word, start_ms, end_ms)]
        audio_chunks = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timings.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 10000,   # 100ns → ms
                    "duration": chunk["duration"] / 10000,
                })

        # Save audio
        with open(tmp_audio, "wb") as f:
            for c in audio_chunks:
                f.write(c)

        if not word_timings:
            raise HTTPException(500, "No word timings received from TTS")

        # 2. Build video frames
        W, H = req.width, req.height
        FPS = 24
        words = req.text.split()
        total_duration_ms = word_timings[-1]["start"] + word_timings[-1]["duration"] + 500
        total_frames = int((total_duration_ms / 1000) * FPS) + FPS

        # Try to load a font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", req.font_size)
            font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", req.font_size)
        except:
            font = ImageFont.load_default()
            font_bold = font

        bg = tuple(int(req.bg_color.lstrip("#")[i:i+2], 16) for i in (0,2,4))
        tc = tuple(int(req.text_color.lstrip("#")[i:i+2], 16) for i in (0,2,4))
        hc = tuple(int(req.highlight_color.lstrip("#")[i:i+2], 16) for i in (0,2,4))

        # Wrap words into lines
        padding = 60
        max_w = W - padding * 2
        lines = []
        current_line = []
        current_width = 0

        dummy_img = Image.new("RGB", (W, H))
        dummy_draw = ImageDraw.Draw(dummy_img)

        for word in words:
            bbox = dummy_draw.textbbox((0,0), word + " ", font=font)
            ww = bbox[2] - bbox[0]
            if current_width + ww > max_w and current_line:
                lines.append(current_line)
                current_line = [word]
                current_width = ww
            else:
                current_line.append(word)
                current_width += ww
        if current_line:
            lines.append(current_line)

        # word → (line_idx, word_idx_in_line)
        word_positions = []
        for li, line in enumerate(lines):
            for wi, w in enumerate(line):
                word_positions.append((li, wi))

        line_height = req.font_size + 16
        total_text_h = len(lines) * line_height
        text_start_y = (H - total_text_h) // 2

        frames = []
        for frame_idx in range(total_frames):
            current_ms = (frame_idx / FPS) * 1000

            # Find active word
            active_word_idx = -1
            for i, wt in enumerate(word_timings):
                if wt["start"] <= current_ms < wt["start"] + wt["duration"]:
                    active_word_idx = i
                    break
                elif current_ms < wt["start"] and active_word_idx == -1:
                    break

            img = Image.new("RGB", (W, H), bg)
            draw = ImageDraw.Draw(img)

            global_word_idx = 0
            for li, line_words in enumerate(lines):
                # calculate line x start (centered)
                line_text = " ".join(line_words)
                bbox = draw.textbbox((0,0), line_text, font=font)
                line_w = bbox[2] - bbox[0]
                x = (W - line_w) // 2
                y = text_start_y + li * line_height

                for wi, word in enumerate(line_words):
                    bbox_w = draw.textbbox((0,0), word, font=font)
                    ww = bbox_w[2] - bbox_w[0]

                    if global_word_idx == active_word_idx:
                        # Highlight background
                        draw.rectangle([x-4, y-2, x+ww+4, y+req.font_size+4], fill=hc)
                        draw.text((x, y), word, font=font_bold, fill=(255,255,255))
                    elif global_word_idx < active_word_idx:
                        draw.text((x, y), word, font=font, fill=tuple(int(c*0.5) for c in tc))
                    else:
                        draw.text((x, y), word, font=font, fill=tc)

                    # space
                    bbox_sp = draw.textbbox((0,0), word + " ", font=font)
                    x += bbox_sp[2] - bbox_sp[0]
                    global_word_idx += 1

            frames.append(np.array(img))

        # 3. Combine video + audio
        clip = ImageSequenceClip(frames, fps=FPS)
        audio = AudioFileClip(tmp_audio)
        final = clip.set_audio(audio)
        final.write_videofile(tmp_video, fps=FPS, codec="libx264", audio_codec="aac", logger=None)

        with open(tmp_video, "rb") as f:
            video_bytes = f.read()

        return StreamingResponse(
            io.BytesIO(video_bytes),
            media_type="video/mp4",
            headers={
                "Content-Disposition": 'attachment; filename="mellowd_sync.mp4"',
                "Content-Length": str(len(video_bytes)),
            }
        )

    except Exception as e:
        raise HTTPException(500, f"Video generation failed: {str(e)}")
    finally:
        for p in [tmp_audio, tmp_video]:
            if os.path.exists(p):
                os.remove(p)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
