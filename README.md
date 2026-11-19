# AI-Powered Intelligent Query Resolution System

An intelligent document-based query resolution platform built with FastAPI, React, Retrieval-Augmented Generation (RAG), and Google's Gemini API.

The system enables authenticated users to upload documents, ask natural-language questions, retrieve relevant information, and receive AI-generated responses with source citations.

## Features

- **Multi-agent architecture:** Specialized agents for query understanding, retrieval, clarification, response generation, memory, and structured data analysis.
- **Document-based RAG:** Document ingestion, text extraction, chunking, embeddings, and FAISS vector search.
- **Gemini integration:** Context-grounded answer generation using Google's Gemini API.
- **Authentication:** User registration, login, and protected API endpoints.
- **Document management:** Upload and select documents for targeted retrieval.
- **Structured data analytics:** CSV-based data analysis.
- **Conversation history:** Persistent conversation and query management.
- **Analytics and feedback:** Query analytics, user feedback, and confidence assessment.
- **WhatsApp integration:** WhatsApp Cloud API integration for document-based query workflows.
- **Frontend:** React and Vite application with chat, document upload, agent monitoring, and analytics interfaces.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React, Vite |
| LLM | Google Gemini API |
| Embeddings | Sentence Transformers |
| Vector database | FAISS |
| Database | SQLAlchemy, SQLite / configured database |
| Authentication | JWT |
| Data analysis | Pandas |
| Testing | Pytest |
| Integration | WhatsApp Cloud API |

## Project Structure

```text
ai-query-resolution-system/
├── analytics/
├── backend/
│   ├── agents/
│   ├── api/
│   ├── database/
│   ├── embeddings/
│   ├── ingestion/
│   ├── orchestration/
│   ├── retrieval/
│   ├── schemas/
│   ├── security/
│   └── main.py
├── data/
├── deploy/
├── docs/
├── frontend/
│   └── src/
├── scripts/
├── storage/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.11 or later
- Node.js 20 or later
- A Google Gemini API key

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Mukeshburdak/AI-Powered-Intelligent-Query-Resolution-System.git
cd AI-Powered-Intelligent-Query-Resolution-System
```

### 2. Configure environment variables

Create a local `.env` file using `.env.example` as a template.

Configure the required values:

```env
MAX_UPLOAD_SIZE_MB=15
CHUNK_SIZE=800
CHUNK_OVERLAP=120

JWT_SECRET_KEY=your-secure-secret

GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
LLM_PROVIDER=gemini
```

Never commit `.env` or expose API credentials.

### 3. Install backend dependencies

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Start the backend

```powershell
uvicorn backend.main:app --reload
```

Backend: `http://127.0.0.1:8000`

API documentation: `http://127.0.0.1:8000/docs`

### 5. Install and start the frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Use the local URL printed by Vite.

## Run Tests

From the project root:

```powershell
python -m pytest -q
```

## Deployment

The intended cloud deployment architecture is:

- Frontend: Vercel
- Backend: Render
- LLM: Google Gemini API
- Database and document storage: persistent production storage

Production deployment requires persistent storage for uploaded documents, FAISS indexes, and database files. Configure environment variables and webhook URLs through the hosting provider's secure settings.

## Security

- User authentication and ownership checks protect document access.
- API credentials and JWT secrets must remain outside source control.
- Uploaded documents and generated indexes are excluded from Git.
- Configure HTTPS, CORS, database backups, and persistent storage before production deployment.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).