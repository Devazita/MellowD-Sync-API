# MellowD Sync — Backend API

FastAPI backend for MellowD Sync app.
Provides real Neural TTS voices via edge-tts (Microsoft Neural voices).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Status check |
| GET | /voices | List of Neural voices |
| POST | /tts | Stream MP3 audio (for playback) |
| POST | /tts/mp3 | Download MP3 file |
| POST | /video | Generate MP4 video with highlight |

## Deploy on Render.com (Free)

1. Upload this folder to a GitHub repo
2. Go to render.com → New → Web Service
3. Connect your GitHub repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Click Deploy

Your API URL will be: `https://mellowd-sync-api.onrender.com`

## Local development

```bash
pip install -r requirements.txt
python main.py
# → http://localhost:8000
```

## Test

```bash
curl http://localhost:8000/health
curl http://localhost:8000/voices
curl -X POST http://localhost:8000/tts/mp3 \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world","voice":"en-US-GuyNeural"}' \
  --output test.mp3
```
