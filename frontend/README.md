# TranscriptTurbo Frontend

Modern React frontend for AI-powered meeting transcription and summarization.

## Features

- Upload audio files (MP3/WAV)
- Real-time processing with loading states
- Beautiful display of:
  - Meeting summary
  - Participants list
  - Decisions made
  - Action items with owners and due dates
  - Full transcript
- Download results as Word document
- Responsive design
- Modern dark theme UI

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` and will proxy API requests to the backend at `http://localhost:8000`.

## Tech Stack

- React 18
- TypeScript
- Vite
- Modern CSS with custom properties

## API Integration

The frontend connects to these backend endpoints:
- `POST /api/meetings/process` - Upload and process audio file
- `POST /api/meetings/docx` - Generate Word document from results
