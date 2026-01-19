# TranscriptTurbo Frontend

Modern React frontend for AI-powered meeting transcription and summarization with automatic silence trimming.

## Features

- Upload audio files (MP3/WAV)
- **Automatic silence removal** using FFmpeg.wasm
  - Removes silence from beginning and end of audio
  - Shows before/after comparison
  - Displays size and time reduction
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

## Silence Trimming

The frontend automatically trims silent parts from uploaded audio files using FFmpeg.wasm:

1. **Client-side processing**: All trimming happens in the browser
2. **Visual feedback**: Shows real-time progress during trimming
3. **Comparison display**: Side-by-side view of original vs trimmed stats
4. **Efficiency metrics**: Shows percentage reduction in file size and duration
5. **Smart insights**: Tells you what percentage of the audio is meaningful content

This reduces upload time and processing costs while maintaining audio quality.

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
- FFmpeg.wasm (for client-side audio processing)
- Modern CSS with custom properties

## API Integration

The frontend connects to these backend endpoints:
- `POST /api/meetings/process` - Upload and process audio file
  - Sends `frontend_trimmed` flag to indicate if silence was already removed
- `POST /api/meetings/docx` - Generate Word document from results

## FFmpeg.wasm

The app uses FFmpeg.wasm to process audio entirely in the browser. The silence removal algorithm:
- Detects silence at the beginning and end of the audio
- Uses a threshold of -50dB for silence detection
- Removes silence periods longer than 0.5 seconds
- Re-encodes audio as MP3 with high quality settings

The trimmed audio is then sent to the backend for transcription.
