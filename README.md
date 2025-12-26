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
├── frontend/                   # Next.js web app
│   ├── app/                    # App router pages
│   ├── components/             # React components
│   └── lib/                    # Utilities
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

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key (for embeddings + LLM)
- ElevenLabs API key (optional, for TTS)

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows: venv\Scripts\activate
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

## 🔧 Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings and LLM | Yes |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for TTS | No |
| `CHROMA_PERSIST_DIR` | ChromaDB storage path | No (default: `./data/chroma`) |
| `REDIS_URL` | Redis URL for caching | No (optional) |

## 📖 API Endpoints

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

## 🧠 How RAG Works

1. **Chunking**: Transcript is split into 20-40 second semantic chunks with 5s overlap
2. **Embedding**: Each chunk is embedded using `text-embedding-3-small`
3. **Retrieval** (3 strategies):
   - **Temporal**: Chunks within ±60s of pause timestamp
   - **Foundational**: Earlier chunks that define terms used
   - **Semantic**: Similar chunks from anywhere in video
4. **Generation**: Retrieved chunks are sent to LLM with tutor prompt

## 🎤 TTS Options

| Provider | Quality | Cost | Speed |
|----------|---------|------|-------|
| ElevenLabs Turbo | High | $0.15/1K chars | Fast |
| OpenAI TTS | Good | $0.015/1K chars | Fast |
| Edge TTS | Medium | Free | Medium |

## 📊 Cost Estimates

| Operation | Estimated Cost |
|-----------|---------------|
| Ingest 1 video (10 min) | ~$0.001 |
| 1 explanation (text only) | ~$0.01 |
| 1 explanation (text + audio) | ~$0.03 |

## 🛠️ Development

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

## 📄 License

MIT
