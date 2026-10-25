# AI-Powered Investor Intelligence Platform

An investor research app that turns financial report PDFs into searchable, question-answerable company information. Upload a report, extract its text and financial KPIs, then ask questions grounded in the uploaded reports.

## What it does

- Upload PDF financial reports through a web dashboard or the API.
- Convert PDFs to Markdown and split the content into semantic chunks.
- Create local embeddings with `sentence-transformers/all-MiniLM-L6-v2` and store/retrieve them with FAISS.
- Ask natural-language questions about indexed reports using an Ollama-served language model.
- Extract financial metrics and store them in PostgreSQL for the dashboard.
- Filter chat retrieval by company and fiscal year when those values are available.

## Architecture

- **Web app and API:** FastAPI, Jinja2 templates, and static CSS
- **Document processing:** PyMuPDF / PyMuPDF4LLM, LangChain
- **Embeddings and retrieval:** Hugging Face sentence-transformers and FAISS
- **Language model:** Ollama (default model: `llama3.2`)
- **Metrics database:** PostgreSQL
- **Container support:** Docker and Docker Compose configuration in `k8s/`

## Requirements

- Python 3.12+
- PostgreSQL  (local or hosted)
- Ollama, if running the language model locally
- Git (to clone the repository)

The first run may download the embedding model. Ollama also needs the configured model pulled before chat requests can use it.

## Quick start (local)

### 1. Clone the repository

```bash
git clone https://github.com/intelliraff/ai-powered-investor-intelligence-platform.git
cd ai-powered-investor-intelligence-platform
```

### 2. Create and activate a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create a PostgreSQL database and set the following environment variables in a local `.env` file at the repository root:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-local-password
POSTGRES_DATABASE=investor_intelligence
POSTGRES_SSLMODE=prefer

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

The database user needs permission to create the application database and tables on first startup, or the database must already exist. Keep `.env` private; do not commit credentials.

### 5. Start Ollama and download the model

Install and start Ollama for your operating system, then run:

```bash
ollama pull llama3.2
```

If Ollama is running at a different address or you want another installed model, update `OLLAMA_HOST` and `OLLAMA_MODEL` in `.env`.

### 6. Start the application

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000) for the dashboard. The API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs), and the health endpoint is [http://localhost:8000/health](http://localhost:8000/health).

## Docker Compose

The provided Compose file starts the app and Ollama. It expects PostgreSQL to be available on the host at port `5432`; adjust its database settings in `k8s/docker-compose.yml` for your environment.

```bash
docker compose -f k8s/docker-compose.yml up --build
```

Then pull the model inside the Ollama service:

```bash
docker exec -it invintelligence-ollama ollama pull llama3.2
```

The dashboard is served at [http://localhost:8000](http://localhost:8000). For non-local or production use, replace the sample database credentials in the Compose file and configure secrets securely.

## API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Investor dashboard |
| `GET` | `/health` | Health check |
| `GET` | `/api/metrics` | Extracted financial metrics |
| `POST` | `/upload` | Upload and ingest a PDF report |
| `POST` | `/chat` | Ask a question about indexed reports |

The upload endpoint accepts a multipart form field named `file` and supports PDF files. Example:

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@./data/raw_pdfs/2024_Apple.pdf"
```

Example chat request:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What was the company's revenue?","company":"Apple","year":2024}'
```

## Data and configuration

- Uploaded PDFs are written to `data/raw_pdfs/`.
- Converted Markdown is stored under `data/markdown/`.
- The local FAISS index is stored under `data/vectorstore/`.
- PostgreSQL connection settings and Ollama configuration are read from environment variables.
- Example reports and a prebuilt local vector index are included under `data/`.

Avoid committing private reports, local credentials, or generated data that you do not intend to publish.

## Project layout

```text
.
├── main.py                 # FastAPI application entry point
├── routes/                 # Upload, chat, dashboard, and health routes
├── ingestion/              # PDF conversion and document ingestion
├── rag/                    # Retrieval-augmented KPI extraction
├── vectorstore/            # FAISS storage and retrieval
├── llm/                    # Ollama client helpers
├── database/               # PostgreSQL access and metric persistence
├── templates/              # Dashboard HTML
├── static/                 # Dashboard styles
├── data/                   # Example reports and local generated data
└── k8s/                    # Docker Compose and Kubernetes manifests
```

## Notes

- Chat responses are intended to use retrieved report content. Review financial answers against the source report before relying on them.
- Keep `.env`, database passwords, API keys, and private financial documents out of Git.
- The repository also contains deployment notes and Kubernetes manifests in `CICD_Deployment_Guide.md`, `deployment-Document.md`, and `k8s/`.
