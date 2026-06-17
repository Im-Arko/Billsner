# Billsner: AI-Based Expense Bill Analyzer

Production-oriented full-stack platform that uploads bills/invoices, runs OCR + LLM extraction, classifies expenses, detects semantic duplicates, and supports natural-language search with dashboards and exports.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TypeScript, Recharts, react-dropzone |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2 async |
| Database | MariaDB |
| Migrations | Alembic |
| AI | LangChain, Ollama, Tesseract OCR, ChromaDB, sentence-transformers |
| Jobs | Celery + Redis |
| Deploy | Docker Compose |

## Quick start

```bash
# Copy environment
cp backend/.env.example backend/.env

docker compose up --build
```

To start only the database service:

```bash
docker compose up -d mariadb
```

To start the database and Redis without the full stack:

```bash
docker compose up -d mariadb redis
```

- Frontend: http://localhost:3000  
- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

### Local development (without Docker)

**Backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
# Start MariaDB + Redis locally, update .env
uvicorn app.main:app --reload
celery -A app.tasks.celery_app:celery_app worker --loglevel=info --pool=solo --concurrency=1
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

**Backend tests**

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Project structure

```
billanalyser/
├── backend/app/
│   ├── api/v1/          # REST routers
│   ├── ai/              # OCR, LLM, vectors
│   ├── models/          # SQLAlchemy ORM
│   ├── schemas/         # Pydantic DTOs
│   ├── services/        # Business logic
│   ├── tasks/           # Celery
│   └── utils/           # Auth, file validation
├── frontend/src/
│   ├── api/             # Axios client
│   ├── components/      # Upload, UI
│   └── pages/           # Dashboard, expenses, auth
├── docs/ARCHITECTURE.md # Full system design
└── docker-compose.yml
```

## API overview

| Group | Endpoints |
|-------|-----------|
| Auth | `POST /api/v1/auth/register`, `/login`, `/refresh`, `GET /me` |
| Bills | `POST /upload`, `GET /{id}`, `DELETE /{id}` |
| Expenses | `GET /`, `POST /search`, `GET /summary`, `PATCH /{id}` |
| AI | `POST /ocr/{bill_id}`, `/classify`, `GET /duplicates/{bill_id}` |
| Reports | `GET /export?format=csv\|xlsx\|pdf&category={category}&vendor={vendor}&date_from={YYYY-MM-DD}&date_to={YYYY-MM-DD}` |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for ER diagram, pipelines, and deployment guidance.
