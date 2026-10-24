# Billsner — native Windows + Groq Cloud

Upload receipt images or PDFs, extract expense data through Groq Cloud, review
expenses, detect similar bills, search, and export CSV/XLSX/PDF reports.

The app runs directly on Windows with Python and Node.js. SQLite stores accounts,
expenses, and the processing queue. The API starts its own background worker.
There is no Docker, database server, Redis, Celery service, or local LLM to start.

## Start the app

From this project folder, run this in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1
```

On the first run it creates the Python environment and installs dependencies if
needed. If `backend/.env` does not exist, it creates one with a generated secret.
Add your Groq API key to `GROQ_API_KEY` in that file, then restart the backend.
Existing local settings and API keys are preserved by the start script.

In a second PowerShell window:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-frontend.ps1
```

- App: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Keep both windows open. Stop each with Ctrl+C. To reinstall backend dependencies
when updating this checkout, add `-InstallDependencies` to the backend script.

## Requirements

- Python 3.12 or 3.13 and Node.js/npm.
- Internet access and a Groq Cloud API key: https://console.groq.com/keys
- Tesseract OCR installed on Windows for images.
- Poppler installed on Windows for image-based PDFs.

`TESSERACT_CMD` and `POPPLER_PATH` in `backend/.env` point to your native OCR
installations. These tools perform OCR; all language-model work runs on Groq.
No model weights are downloaded by the application.

The default model is `openai/gpt-oss-20b`, hosted by Groq. Override `GROQ_MODEL`
with another model available to your account. Model availability changes; consult
https://console.groq.com/docs/models and https://console.groq.com/docs/deprecations.

## Configuration

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./data/billanalyser.db
LLM_PROVIDER=groq
GROQ_API_KEY=your-key-here
GROQ_MODEL=openai/gpt-oss-20b
SEARCH_INDEX_PATH=./data/search.db
UPLOAD_DIR=./uploads
```

Relative paths resolve against `backend/`, including in processing subprocesses.
The API key stays in the backend; it is never sent to the frontend.
Missing/invalid keys, rate limits, and connectivity failures are reported on the
failed upload instead of silently saving empty expenses.

## Storage and processing

- `backend/data/billanalyser.db`: accounts, bills, OCR results, expenses, and queue.
- `backend/data/search.db`: rebuildable text similarity index.
- `backend/uploads/`: uploaded bill files.

This version uses a new SQLite database. Existing MariaDB data and old Chroma
files are not automatically imported or overwritten. Register a new account if
you have not used the SQLite version before. Keep database files and uploads when
moving or backing up the app; stop the backend before copying them.

Run **one API process** (`--workers 1`); it supervises one processing job at a time.
Pending bills persist across restarts. Interrupted processing is requeued at
startup. Each job has an enforceable process timeout controlled by
`BILL_PROCESSING_TIMEOUT_SECONDS`. No separate worker command is needed.

Groq receives the extracted receipt text for structured extraction and
classification. OCR runs locally. Similarity search uses a lightweight lexical
cosine index, so identical/near-identical receipt text matches well; it does not
provide the synonym understanding of neural semantic embeddings. Natural-language
category, vendor, and date filters still run against the expense database.

Bills with missing, zero, or negative totals fail without creating expenses.
The dashboard polls queued/processing bills and displays failure reasons.
Deleting a bill clears duplicate references, OCR, expenses, index entries, and the
uploaded file. Bills currently processing cannot be deleted.

## Manual startup

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Tests isolate storage and mock Groq requests; they do not require an API key or
send real receipt data to a provider.

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the runtime design.
