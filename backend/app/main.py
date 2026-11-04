from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from starlette.concurrency import run_in_threadpool

from .rag import VideoNotIndexedError, index_video, answer_question


app = FastAPI(title="YouTube RAG Agent", version="0.1.0")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to the deployed frontend origin in production.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VideoRequest(BaseModel):
    url: HttpUrl


class ChatRequest(BaseModel):
    video_id: str
    question: str


def is_youtube_url(url: HttpUrl) -> bool:
    host = (urlparse(str(url)).hostname or "").lower()
    return host == "youtu.be" or host.endswith("youtube.com")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "phase": "complete"}


@app.post("/api/video")
async def add_video(request: VideoRequest) -> dict[str, object]:
    if not is_youtube_url(request.url):
        raise HTTPException(status_code=400, detail="أدخل رابط YouTube صحيحًا.")

    try:
        return await run_in_threadpool(index_video, str(request.url))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, object]:
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="اكتب سؤالًا أولًا.")

    try:
        return await run_in_threadpool(answer_question, request.video_id, request.question)
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
