# TranscriptTurbo

AI-powered meeting transcription and summarization system built with React and Python FastAPI.

## Features

- Audio transcription using Speechmatics API
- AI-powered summarization using OpenAI/Claude
- Extracts participants, decisions, and action items
- Download results as Word document
- Modern, responsive UI

## Project Structure

```
TranscriptTurbo/
├── backend/          # Python FastAPI backend
│   ├── app/
│   │   ├── api/      # API routes
│   │   ├── core/     # Configuration
│   │   ├── models.py # Data models
│   │   ├── prompts/  # LLM system prompts
│   │   ├── services/ # External API clients
│   │   └── utils/    # Helper utilities
│   └── tests/        # Backend tests
└── frontend/         # React TypeScript frontend
    └── src/
```

## Quick Start

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
uv sync
```

3. Create `.env` file with your API keys:
```env
SPEECHMATICS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

4. Run the server:
```bash
uv run uvicorn app.main:app --reload
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Usage

1. Open `http://localhost:5173` in your browser
2. Upload an audio file (MP3 or WAV)
3. Click "Process Meeting"
4. View the results:
   - Meeting summary
   - Participants list
   - Decisions made
   - Action items
   - Full transcript
5. Download as Word document if needed

## Tech Stack

### Backend
- Python 3.11+
- FastAPI
- OpenAI API
- Speechmatics API
- python-docx

### Frontend
- React 18
- TypeScript
- Vite
- Modern CSS

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/meetings/process` - Upload and process audio file
- `POST /api/meetings/docx` - Generate Word document

## Testing

Run backend tests:
```bash
cd backend
uv run pytest
```

## License

MIT
