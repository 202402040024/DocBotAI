# DocBot AI — Multi-Document AI Chatbot

A production-ready full-stack AI chatbot with Hybrid RAG, MongoDB Atlas, FAISS vector search, conversational memory, and streaming responses.

🔗 **Live Demo:** [https://doc-bot-ai-mcp3.vercel.app](https://doc-bot-ai-mcp3.vercel.app)  
📡 **API Docs:** [https://docbotai-idyn.onrender.com/docs](https://docbotai-idyn.onrender.com/docs)

---

## Features

| Feature | Description |
|---------|-------------|
| 📄 Document Upload | PDF, DOCX, CSV, XML support |
| 🧠 Hybrid RAG | Auto-switches between document search and general AI |
| 💬 Streaming Chat | Real-time SSE streaming responses |
| 🔍 Semantic Search | FAISS vector similarity search |
| 🗣️ Voice I/O | Speech-to-text and text-to-speech |
| 📊 Dashboard | Analytics with charts and stats |
| 🌙 Dark/Light Mode | Theme toggle with persistence |
| 🔐 JWT Auth | Secure authentication with refresh tokens |
| 📱 Mobile Responsive | Works on all screen sizes |

---

## Tech Stack

**Frontend:** Next.js 16, TypeScript, Tailwind CSS, Zustand, Framer Motion, React Markdown  
**Backend:** FastAPI, Python 3.11, Async Architecture  
**Database:** MongoDB Atlas  
**Vector Store:** FAISS (per-user index)  
**Embeddings:** sentence-transformers/all-MiniLM-L6-v2  
**LLM:** Gemini 2.5 Flash (with Ollama fallback)  
**Deployment:** Vercel (frontend) + Render (backend)

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB Atlas account
- Gemini API key

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
cp .env.example .env           # Fill in your values
uvicorn app.main:app --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # Set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Deployment

### Backend → Render
1. Connect GitHub repo to Render
2. Set **Root Directory** → `backend`
3. Set **Runtime** → Python 3
4. **Build:** `pip install -r requirements.txt`
5. **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add all environment variables from `.env.example`

### Frontend → Vercel
1. Connect GitHub repo to Vercel
2. Set **Root Directory** → `frontend`
3. Add env var: `NEXT_PUBLIC_API_URL` = your Render URL
4. Deploy

---

## Environment Variables

### Backend (`.env`)
| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `JWT_SECRET_KEY` | Secret key for JWT signing |
| `GEMINI_API_KEY` | Google Gemini API key |
| `EMBEDDING_MODEL_NAME` | HuggingFace model name |
| `SIMILARITY_THRESHOLD` | RAG match threshold (0.0–1.0) |
| `FRONTEND_URL` | Your Vercel URL (for CORS) |

### Frontend (`.env.local`)
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Your Render backend URL |

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

---

## Project Structure

```
chatbot/
├── backend/
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Config & security
│   │   ├── database/     # MongoDB client
│   │   ├── repositories/ # Data access layer
│   │   ├── schemas/      # Pydantic models
│   │   └── services/     # Business logic
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    └── src/
        ├── app/           # Next.js pages
        ├── components/    # React components
        ├── services/      # API clients
        ├── store/         # Zustand state
        └── types/         # TypeScript types
```
