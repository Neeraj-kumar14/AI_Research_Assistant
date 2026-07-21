---
title: AI Research Assistant
emoji: 📚
colorFrom: green
colorTo: yellow
sdk: streamlit
sdk_version: "1.58.0"
app_file: app.py
pinned: false
---

# AI Research Assistant

Chat with your PDF/DOCX documents — ask questions grounded in the source
pages, generate study notes, flashcards, and quizzes, with automatic web
fallback and OCR for scanned pages.

## Setting up secrets (required before first run)

This app needs API keys. **Never commit them to the repo** — on HF Spaces,
set them under **Settings → Variables and secrets → New secret** instead:

| Secret name        | Required | Notes                                  |
|---------------------|----------|-----------------------------------------|
| `GROQ_API_KEY`       | Yes      | Primary Groq key                       |
| `GROQ_API_KEY_2`     | No       | Extra fallback key (separate quota)    |
| `GROQ_API_KEY_3`     | No       | Extra fallback key                     |
| `GROQ_API_KEY_4`     | No       | Extra fallback key                     |
| `TAVILY_API_KEY`     | Yes      | Web search fallback                    |

Secrets set this way are exposed to the running app as normal environment
variables — `os.getenv(...)` picks them up automatically, no `.env` file
needed in production. `.env` (or `_env`) is only for local development and
must stay out of the repo (see `.gitignore` below).

## Tuning for available resources (optional)

These all have working defaults; only set them if you need to raise or
lower limits for your hosting tier:

| Variable                      | Default   | Purpose                                  |
|--------------------------------|-----------|-------------------------------------------|
| `MAX_PDF_PAGES`                 | 300       | Cap on pages processed per PDF upload      |
| `MAX_OCR_PAGES`                 | 30        | Cap on scanned pages OCR'd per PDF upload  |
| `MAX_DOCX_CHARS`                | 600000    | Cap on characters processed per DOCX       |
| `SESSION_IDLE_TIMEOUT_SECONDS`  | 1800      | Idle time before a session's loaded doc is evicted from memory |
| `CACHE_TTL_SECONDS`             | 604800    | Max age of a cached processed document (7 days) |
| `MAX_CACHE_BYTES`               | 524288000 | Max total size of the on-disk document cache (500MB) |
| `CPU_JOB_SLOTS`                 | 2         | Max concurrent embedding/OCR jobs across all users |
| `EMBEDDING_MODEL`               | paraphrase-multilingual-MiniLM-L12-v2 | Sentence-transformers model |
| `GROQ_MODEL_FALLBACKS`          | see `utils/llm.py` | Comma-separated Groq model fallback chain |

## Local development

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your real keys, keep this file untracked
streamlit run app.py
```

## Notes on this deployment

- Runs CPU-only (no GPU) — torch is installed from the CPU wheel index in
  `requirements.txt`.
- `.study_cache/` on most free hosts sits on ephemeral storage and is wiped
  on restarts/redeploys — it speeds up re-uploads of the same file within a
  running instance, but isn't a permanent store.
- Free CPU tiers have limited cores; heavy concurrent usage (many users
  uploading large/scanned documents at once) will queue rather than fail,
  via `CPU_JOB_SLOTS` — expect things to slow down under real load rather
  than error out.
