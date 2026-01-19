from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="TranscriptTurbo API", version="0.1.0")


# For local dev with Vite (http://localhost:5173). You can adjust as needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


class TranscribeRequest(BaseModel):
    text: str


@app.post("/api/transcribe")
def transcribe(req: TranscribeRequest):
    # Placeholder "transcription" so you have a working API surface to iterate on.
    return {"transcript": req.text}

