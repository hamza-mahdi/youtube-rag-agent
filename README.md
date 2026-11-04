# YouTube RAG Agent

An Arabic-friendly starter project for chatting with a YouTube video.

## Features

- Fetches public Arabic or English YouTube captions
- Splits and indexes the transcript in a persistent local ChromaDB database
- Retrieves relevant transcript passages for every question
- Answers in Arabic through the Groq model configured in `.env`
- Provides a plain HTML/CSS/JavaScript chat interface

## تشغيل بواجهة رسومية — الموصى به

انقر مرتين على `تشغيل_التطبيق.pyw` في مجلد المشروع. سيظهر مشغّل صغير؛ اختر **تشغيل وفتح التطبيق**. لا تحتاج إلى الطرفية.

## تشغيل يدوي (اختياري)

```powershell
cd E:\youtube-rag-agent\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000`. Keep the `.env` file in the project root; it must define `GROQ_API_KEY` and `GROQ_MODEL`.

## API

- `GET /api/health` confirms the service is running.
- `POST /api/video` accepts `{ "url": "https://www.youtube.com/watch?v=..." }`, fetches captions, and indexes them.
- `POST /api/chat` accepts `{ "video_id": "...", "question": "..." }` and returns an Arabic answer with retrieved excerpts.

## Limitations

The video must be public and have Arabic or English captions available. ChromaDB stores the local index in `chroma_data/`, which can be deleted to clear all indexed videos.
