# YouTube Learning Assistant

An AI-powered YouTube tutor that provides contextual explanations when you don't understand something in a video.

## 🎯 What It Does

1. **Extracts** the complete transcript from any YouTube video
2. **Indexes** the transcript into a RAG (Retrieval-Augmented Generation) system
3. **Explains** concepts when you pause and say "I didn't understand this"
4. **Speaks** the explanation with natural TTS (optional)

## 🏗️ Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the complete system design.

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Browser Extension│────▶│  Next.js Frontend│────▶│  Python Backend  │
│ (Pause Detection)│     │  (UI + Display)  │     │  (RAG + LLM + TTS)│
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

## 📁 Project Structure

```
youtube-tutor/
├── backend/                    # Python FastAPI backend
│   ├── api/                    # REST API routes
│   │   └── routes/
│   ├── services/               # Business logic
│   │   ├── transcript/         # YouTube transcript extraction
│   │   ├── rag/                # Embedding + retrieval
│   │   ├── llm/                # LLM prompting
│   │   └── tts/                # Text-to-speech
│   ├── models/                 # Pydantic schemas
│   └── main.py                 # FastAPI entry
├── frontend/                   # Vite React web app
│   ├── src/                    # React components
│   └── public/                 # Static assets
├── extension/                  # Browser extension
│   ├── manifest.json
│   ├── content/                # YouTube page scripts
│   └── popup/                  # Extension popup UI
├── docs/                       # Documentation
│   └── ARCHITECTURE.md         # System design
└── data/                       # Local data storage
    ├── chroma/                 # Vector database
    └── audio/                  # TTS cache
```

---

## 🚀 Deployment

### Option 1: Deploy Backend to Render (Recommended - Free Tier)

1. **Push to GitHub** (if not already):
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Deploy on Render**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add Environment Variables:
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `FRONTEND_URL`: Your frontend deployment URL (after deploying frontend)
     - `LLM_PROVIDER`: `openai`
     - `TTS_PROVIDER`: `edge`

3. **Note your backend URL** (e.g., `https://ai-tutor-backend.onrender.com`)

### Option 2: Deploy Backend with Docker

```bash
cd backend
docker build -t ai-tutor-backend .
docker run -p 8000:8000 --env-file .env ai-tutor-backend
```

### Deploy Frontend to Vercel (Recommended)

1. **Deploy on Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - Add Environment Variable:
     - `VITE_API_URL`: Your backend URL (e.g., `https://ai-tutor-backend.onrender.com`)

2. **Update Backend CORS** (on Render):
   - Add `FRONTEND_URL` environment variable with your Vercel URL

### Deploy Frontend to Netlify (Alternative)

1. **Deploy on Netlify**:
   - Go to [netlify.com](https://netlify.com)
   - Connect your GitHub repository
   - **Base Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Publish Directory**: `dist`
   - Add Environment Variable:
     - `VITE_API_URL`: Your backend URL

---

## 🛠️ Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key (for embeddings + LLM)
- ElevenLabs API key (optional, for TTS)

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run development server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Extension Setup

1. Open Chrome/Edge → Extensions → Developer Mode
2. Click "Load unpacked"
3. Select the `extension/` folder

---

## 🔧 Configuration

### Backend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings and LLM | Yes |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for TTS | No |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Claude) | No |
| `FRONTEND_URL` | Production frontend URL for CORS | For Prod |
| `CHROMA_PERSIST_DIR` | ChromaDB storage path | No (default: `./data/chroma`) |
| `LLM_PROVIDER` | LLM provider: `openai` or `anthropic` | No (default: `openai`) |
| `LLM_MODEL` | LLM model name | No (default: `gpt-4o-mini`) |
| `TTS_PROVIDER` | TTS provider: `elevenlabs`, `openai`, or `edge` | No (default: `edge`) |

### Frontend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `VITE_API_URL` | Backend API URL | For Prod |

---

## 📖 API Endpoints

### GET `/api/health`
Health check endpoint.

### POST `/api/transcript/ingest`
Ingest a YouTube video transcript into the RAG system.

```json
{
  "video_id": "dQw4w9WgXcQ"
}
```

### POST `/api/explain`
Get an explanation for a specific timestamp.

```json
{
  "video_id": "dQw4w9WgXcQ",
  "timestamp": 125.5,
  "user_query": "I don't understand this",
  "include_audio": true
}
```

### POST `/api/explain/stream`
Same as above but streams the response via SSE.

---

## 🧠 How RAG Works

1. **Chunking**: Transcript is split into 20-40 second semantic chunks with 5s overlap
2. **Embedding**: Each chunk is embedded using `text-embedding-3-small`
3. **Retrieval** (3 strategies):
   - **Temporal**: Chunks within ±60s of pause timestamp
   - **Foundational**: Earlier chunks that define terms used
   - **Semantic**: Similar chunks from anywhere in video
4. **Generation**: Retrieved chunks are sent to LLM with tutor prompt

---

## 🎤 TTS Options

| Provider | Quality | Cost | Speed |
|----------|---------|------|-------|
| ElevenLabs Turbo | High | $0.15/1K chars | Fast |
| OpenAI TTS | Good | $0.015/1K chars | Fast |
| Edge TTS | Medium | Free | Medium |

---

## 📊 Cost Estimates

| Operation | Estimated Cost |
|-----------|---------------|
| Ingest 1 video (10 min) | ~$0.001 |
| 1 explanation (text only) | ~$0.01 |
| 1 explanation (text + audio) | ~$0.03 |

---

## 🛠️ Development Commands

### Run Tests
```bash
cd backend
pytest tests/
```

### Type Checking
```bash
cd backend
mypy .
```

### Lint
```bash
cd backend
ruff check .
```

### Build Frontend
```bash
cd frontend
npm run build
```

---

## 📄 License

MIT
