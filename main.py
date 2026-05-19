"""
MellowD Sync — Backend API
FastAPI + edge-tts
"""

import os, io, asyncio, uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import edge_tts

app = FastAPI(title="MellowD Sync API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

VOICES = [
    {"id": "en-US-GuyNeural",         "name": "Guy",         "gender": "Male",   "accent": "American"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher", "gender": "Male",   "accent": "American"},
    {"id": "en-US-EricNeural",        "name": "Eric",        "gender": "Male",   "accent": "American"},
    {"id": "en-US-RogerNeural",       "name": "Roger",       "gender": "Male",   "accent": "American"},
    {"id": "en-US-SteffanNeural",     "name": "Steffan",     "gender": "Male",   "accent": "American"},
    {"id": "en-US-AndrewNeural",      "name": "Andrew",      "gender": "Male",   "accent": "American"},
    {"id": "en-US-JennyNeural",       "name": "Jenny",       "gender": "Female", "accent": "American"},
    {"id": "en-US-AriaNeural",        "name": "Aria",        "gender": "Female", "accent": "American"},
    {"id": "en-US-EmmaNeural",        "name": "Emma",        "gender": "Female", "accent": "American"},
    {"id": "en-US-MichelleNeural",    "name": "Michelle",    "gender": "Female", "accent": "American"},
    {"id": "en-US-MonicaNeural",      "name": "Monica",      "gender": "Female", "accent": "American"},
    {"id": "en-US-AnaNeural",         "name": "Ana",         "gender": "Female", "accent": "American"},
    {"id": "en-US-AvaNeural",         "name": "Ava",         "gender": "Female", "accent": "American"},
    {"id": "en-US-NancyNeural",       "name": "Nancy",       "gender": "Female", "accent": "American"},
    {"id": "en-GB-RyanNeural",        "name": "Ryan",        "gender": "Male",   "accent": "British"},
    {"id": "en-GB-ThomasNeural",      "name": "Thomas",      "gender": "Male",   "accent": "British"},
    {"id": "en-GB-SoniaNeural",       "name": "Sonia",       "gender": "Female", "accent": "British"},
    {"id": "en-GB-LibbyNeural",       "name": "Libby",       "gender": "Female", "accent": "British"},
    {"id": "en-GB-MaisieNeural",      "name": "Maisie",      "gender": "Female", "accent": "British"},
    {"id": "en-AU-WilliamNeural",     "name": "William",     "gender": "Male",   "accent": "Australian"},
    {"id": "en-AU-NatashaNeural",     "name": "Natasha",     "gender": "Female", "accent": "Australian"},
    {"id": "en-CA-LiamNeural",        "name": "Liam",        "gender": "Male",   "accent": "Canadian"},
    {"id": "en-CA-ClaraNeural",       "name": "Clara",       "gender": "Female", "accent": "Canadian"},
]

VOICE_IDS = {v["id"] for v in VOICES}


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-GuyNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MellowD Sync API", "version": "1.1.0"}


@app.get("/voices")
async def get_voices():
    grouped = {}
    for v in VOICES:
        g = v["accent"] + " " + v["gender"]
        grouped.setdefault(g, []).append(v)
    return {"voices": VOICES, "grouped": grouped}


@app.post("/tts/mp3")
async def tts_mp3(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(400, "Text is empty")
    if len(req.text) > 10000:
        raise HTTPException(400, "Text too long")

    voice = req.voice if req.voice in VOICE_IDS else "en-US-GuyNeural"
    rate = req.rate if req.rate else "+0%"

    tmp_path = f"/tmp/{uuid.uuid4()}.mp3"
    try:
        communicate = edge_tts.Communicate(text=req.text, voice=voice, rate=rate)
        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline",
                "Content-Length": str(len(audio_bytes)),
                "Accept-Ranges": "bytes",
            }
        )
    except Exception as e:
        raise HTTPException(500, f"TTS error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/tts")
async def tts_stream(req: TTSRequest):
    return await tts_mp3(req)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
