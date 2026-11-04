"""Transcript ingestion, local Chroma retrieval, and Groq answers."""

import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import chromadb
from dotenv import load_dotenv
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

CHROMA_PATH = PROJECT_ROOT / "chroma_data"
COLLECTION_NAME = "youtube_transcripts"


class VideoNotIndexedError(RuntimeError):
    """Raised when chat is requested for a video that has not been indexed."""


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host.endswith("youtube.com"):
        candidate = parse_qs(parsed.query).get("v", [""])[0]
        if not candidate and parsed.path.startswith("/shorts/"):
            candidate = parsed.path.split("/")[2]
    else:
        candidate = ""

    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        raise ValueError("تعذر استخراج معرّف الفيديو من الرابط.")
    return candidate


def _collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _fetch_transcript(video_id: str) -> list[dict[str, object]]:
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=["ar", "en"])
        return [
            {"text": snippet.text, "start": float(snippet.start)}
            for snippet in transcript
            if snippet.text.strip()
        ]
    except Exception as error:  # The library exposes several provider-specific errors.
        raise RuntimeError(
            "تعذر جلب النص من YouTube. تأكد أن للفيديو ترجمة متاحة وأنه عام."
        ) from error


def _chunk_transcript(items: list[dict[str, object]], limit: int = 1000) -> list[dict[str, object]]:
    chunks: list[dict[str, object]] = []
    words: list[str] = []
    start = 0.0
    size = 0

    for item in items:
        text = str(item["text"]).strip()
        if not words:
            start = float(item["start"])
        if words and size + len(text) > limit:
            chunks.append({"text": " ".join(words), "start": start})
            words, size, start = [], 0, float(item["start"])
        words.append(text)
        size += len(text) + 1

    if words:
        chunks.append({"text": " ".join(words), "start": start})
    return chunks


def index_video(url: str) -> dict[str, object]:
    video_id = extract_video_id(url)
    items = _fetch_transcript(video_id)
    chunks = _chunk_transcript(items)
    if not chunks:
        raise RuntimeError("نص الفيديو فارغ ولا يمكن فهرسته.")

    collection = _collection()
    collection.delete(where={"video_id": video_id})
    collection.upsert(
        ids=[f"{video_id}-{index}" for index in range(len(chunks))],
        documents=[str(chunk["text"]) for chunk in chunks],
        metadatas=[
            {"video_id": video_id, "start": float(chunk["start"]), "source_url": url}
            for chunk in chunks
        ],
    )
    return {
        "message": "تمت فهرسة نص الفيديو بنجاح. يمكنك الآن طرح الأسئلة.",
        "video_id": video_id,
        "chunks": len(chunks),
    }


def _timestamp(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def answer_question(video_id: str, question: str) -> dict[str, object]:
    collection = _collection()
    result = collection.query(
        query_texts=[question],
        n_results=4,
        where={"video_id": video_id},
        include=["documents", "metadatas", "distances"],
    )
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    if not documents:
        raise VideoNotIndexedError("هذا الفيديو غير مفهرس بعد. أضف رابطه أولًا.")

    key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")
    if not key or not model:
        raise RuntimeError("ملف .env يحتاج GROQ_API_KEY وGROQ_MODEL.")

    context = "\n\n".join(
        f"[المقطع {index + 1} — { _timestamp(float(metadata['start'])) }]\n{document}"
        for index, (document, metadata) in enumerate(zip(documents, metadatas))
    )
    prompt = (
        "أجب بالعربية اعتمادًا على مقاطع نص الفيديو فقط. "
        "إن لم تجد الإجابة في المقاطع فقل ذلك بوضوح. "
        "اذكر وقتًا أو أكثر بصيغة [د:ث] عند الاستشهاد بالمقطع.\n\n"
        f"المقاطع:\n{context}\n\nالسؤال: {question}"
    )
    try:
        response = Groq(api_key=key).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "أنت مساعد دقيق لفهم فيديوهات YouTube."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
    except Exception as error:
        raise RuntimeError("تعذر الحصول على إجابة من Groq. تحقق من المفتاح واسم النموذج.") from error

    return {
        "answer": response.choices[0].message.content or "لم يتم إنشاء إجابة.",
        "sources": [
            {"timestamp": _timestamp(float(metadata["start"])), "text": document[:220]}
            for document, metadata in zip(documents, metadatas)
        ],
    }
