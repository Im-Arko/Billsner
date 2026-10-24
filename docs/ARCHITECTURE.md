# Runtime architecture

## Components

| Component | Implementation |
| --- | --- |
| Frontend | React, TypeScript, Vite, Recharts |
| API | FastAPI, SQLAlchemy async, Pydantic |
| Data | SQLite with WAL, foreign keys, and a busy timeout |
| Processing queue | Persisted pending bills, polled by the API background worker |
| Job isolation | A Python subprocess with a hard deadline and shutdown cleanup |
| OCR | Tesseract, OpenCV, native Poppler for PDFs |
| Extraction/classification | Groq Cloud HTTP API, JSON mode, validated output |
| Similarity | SQLite text index and lexical cosine similarity |
| Reports | pandas, openpyxl, ReportLab |

## Bill lifecycle

1. Authenticate the user and validate the upload.
2. Save the file and commit a bill with `pending` status.
3. The local worker reads committed pending bills in arrival order.
4. A supervised subprocess commits `processing` status and runs OCR.
5. OCR text goes to Groq Cloud; the response is validated against the extraction schema.
6. Require a valid positive total, persist an expense, and update the text index.
7. Check similar bills against existing expenses, then commit `completed`.
8. On failure, roll back partial records and store `failed` with an explanation.

The subprocess deadline covers blocking OCR, network requests, and database work.
The supervising worker terminates the child on timeout or API shutdown. Startup
requeues interrupted processing. Use one API process; this is a local application,
not a distributed queue service.

## Persistence

SQLite enables foreign keys and WAL on every connection. Database paths resolve
against the backend directory so the API and worker always open the same files.
The main database uses SQLAlchemy models in `backend/app/models/`. Search documents
are stored in a separate SQLite index behind the existing vector-store interface.
The text index downloads no model and makes no external embedding request.

The main schema includes users, bills, OCR results, expenses, vendors, categories,
audit logs, and index metadata. Bill deletion clears references from duplicate
expenses before cascading dependent rows, then removes the index entry and file.
Search results are scoped to the authenticated user.

## Groq configuration

`GROQ_API_KEY` and `GROQ_MODEL` are read only on the backend. Both extraction and
classification use `app/ai/groq_client.py`, with a fixed Groq Cloud endpoint,
explicit timeouts, JSON output mode, and no implicit retry loop. Classification
can fall back to keywords; extraction surfaces failures rather than fabricating
amounts. The default hosted model is configurable in `backend/.env`.

## Search tradeoff

Structured natural-language filters cover categories, merchants, and dates.
The lightweight text index supports similarity and duplicate checks without
local ML runtimes. It is lexical, so synonym-heavy semantic queries may return
fewer relevant results than a neural embedding model.

## Running and validation

Start the backend with `start-backend.ps1` and the frontend with
`start-frontend.ps1`. No container runtime or separate database, broker, LLM,
or worker service is required. Python dependencies are in
`backend/requirements.txt`; frontend dependencies are in `frontend/package.json`.

Backend tests use isolated SQLite databases with foreign-key enforcement and
mocked Groq responses. They cover invalid amounts, rollback, duplicate references,
queue recovery, index ownership, subprocess deadlines, and cloud errors.
