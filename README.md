# DocBot AI — Multi-Document AI Chatbot

Production-ready full-stack AI chatbot with Hybrid RAG, MongoDB Atlas, FAISS, conversational memory, and Gemini streaming.

## Single-Deployment Architecture

The entire app (Next.js frontend + FastAPI backend) deploys as **one project** — no CORS, no cross-origin issues, one domain.

| Option | Platform | When to use |
|--------|----------|-------------|
| **A** | **Vercel (recommended)** | Free tier, easiest setup, auto-scaling |
| **B** | **Docker (Railway / Fly.io / VPS)** | Need persistent FAISS, longer timeouts, no cold starts |

---

## Project Structure

```
chatbot/
├── api/
│   ├── index.py            # Vercel serverless entry (Mangum + FastAPI)
│   └── requirements.txt    # Python deps for Vercel
├── app/                    # FastAPI backend package
│   ├── main.py
│   ├── api/                # Route handlers (auth, chat, documents, rag, voice)
│   ├── core/               # Config & security
│   ├── database/           # MongoDB client
│   ├── repositories/       # Data access layer
│   ├── schemas/            # Pydantic models
│   └── services/           # Business logic (embeddings, vector store, LLM, RAG, memory)
├── src/                    # Next.js frontend (App Router)
│   ├── app/
│   ├── components/
│   ├── services/           # API client services
│   ├── store/              # Zustand state
│   └── types/
├── public/
├── Dockerfile              # Single-container deploy (alternative to Vercel)
├── docker-compose.yml      # Local Docker development
├── start.sh                # Multi-process startup for Docker
├── vercel.json             # Vercel configuration
├── next.config.ts
├── package.json
└── .env.example            # All required env vars
```

---

## Option A: Deploy on Vercel

### Prerequisites

- MongoDB Atlas cluster
- Google Gemini API key (free: https://aistudio.google.com/app/apikey)

### Steps

1. **Push this repo to GitHub**

2. **Import into Vercel**
   - New Project → Import Git Repo
   - Vercel auto-detects Next.js + Python
   - Root directory: `./` (default)

3. **Set environment variables** in Vercel Dashboard → Settings → Environment Variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `MONGODB_DB_NAME` | Database name | `chatbot_rag` |
| `JWT_SECRET_KEY` | Random 64-char hex | `python -c "import secrets; print(secrets.token_hex(64))"` |
| `GEMINI_API_KEY` | Google Gemini API key | From Google AI Studio |
| `SIMILARITY_THRESHOLD` | RAG match threshold | `0.5` |
| `TOP_K` | Number of chunks to retrieve | `4` |

4. **Deploy** → Vercel builds Next.js and Python function together.

> ⚠️ **Vercel Free Tier limits:** 10s timeout, 100s max duration. Upgrade to **Pro ($20/mo)** for 60s timeout + 900s max execution.
>
> ⚠️ **Cold starts:** FAISS indexes are rebuilt from MongoDB chunks when the serverless instance recycles (typically after 5-15 min idle). RAG queries fall back to general AI during rebuild.

---

## Option B: Deploy via Docker (Railway / Fly.io / VPS)

For production with persistent FAISS, no cold starts, and longer timeouts:

### Docker (single container)

```bash
# 1. Build the Docker image
docker build -t docbot .

# 2. Run with environment variables
docker run -p 8000:8000 \
  -e MONGODB_URI="your_mongodb_uri" \
  -e GEMINI_API_KEY="your_gemini_key" \
  -e JWT_SECRET_KEY="your_jwt_secret" \
  docbot
```

### Docker Compose (local dev)

```bash
# Set env vars in .env file, then:
docker compose up --build
```

### Deploy on Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

Set the same env vars in Railway Dashboard.

### Deploy on Fly.io

```bash
# Install flyctl
fly launch --no-deploy
fly secrets set MONGODB_URI=... GEMINI_API_KEY=... JWT_SECRET_KEY=...
fly deploy
```

---

## Local Development

### Terminal 1 — FastAPI backend

```bash
pip install -r api/requirements.txt
uvicorn app.main:app --port 8000 --reload
```

### Terminal 2 — Next.js frontend

```bash
npm install
npm run dev   # proxies /api/* → localhost:8000 automatically
```

Open http://localhost:3000

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register |
| POST | `/api/auth/login` | Login |
| POST | `/api/documents/upload` | Upload document |
| GET | `/api/documents` | List documents |
| POST | `/api/chat?stream=true` | Stream chat |
| POST | `/api/rag/query` | RAG query |
| POST | `/api/rag/search` | Semantic search |
| POST | `/api/rag/summarize` | Summarize document |
| POST | `/api/rag/quiz` | Generate quiz |
| GET | `/api/dashboard/stats` | Analytics |
