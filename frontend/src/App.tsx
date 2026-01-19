import { useState, FormEvent } from 'react';
import { MeetingProcessResponse } from './types';
import './style.css';

const API_BASE = '/api';

interface FileStats {
  size: number;
  duration: number;
}

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [originalStats, setOriginalStats] = useState<FileStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MeetingProcessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloadingDocx, setDownloadingDocx] = useState(false);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getAudioDuration = (file: File): Promise<number> => {
    return new Promise((resolve, reject) => {
      const audio = new Audio();
      const objectUrl = URL.createObjectURL(file);
      
      audio.addEventListener('loadedmetadata', () => {
        resolve(audio.duration);
        URL.revokeObjectURL(objectUrl);
      });

      audio.addEventListener('error', () => {
        reject(new Error('Failed to load audio'));
        URL.revokeObjectURL(objectUrl);
      });

      audio.src = objectUrl;
    });
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setError(null);
    setResult(null);

    try {
      const duration = await getAudioDuration(selectedFile);
      setOriginalStats({
        size: selectedFile.size,
        duration: duration
      });
    } catch (err) {
      console.error('File processing error:', err);
      setError('Failed to process audio file');
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select an audio file');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/meetings/process`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }

      const data: MeetingProcessResponse = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process meeting');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadDocx = async () => {
    if (!result) return;

    setDownloadingDocx(true);
    try {
      const response = await fetch(`${API_BASE}/meetings/docx`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          meeting_title: file?.name.replace(/\.[^/.]+$/, '') || 'Meeting',
          transcript: result.transcript,
          notes: result.notes,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate document');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'meeting-notes.docx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download document');
    } finally {
      setDownloadingDocx(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>TranscriptTurbo</h1>
        <p className="subtitle">AI-Powered Meeting Transcription & Summarization</p>
      </header>

      <main className="main">
        <div className="upload-section">
          <form onSubmit={handleSubmit} className="upload-form">
            <div className="file-input-wrapper">
              <input
                type="file"
                id="audio-file"
                accept=".mp3,.wav"
                onChange={handleFileChange}
                disabled={loading}
                className="file-input"
              />
              <label htmlFor="audio-file" className="file-label">
                {file ? file.name : 'Choose audio file (MP3 or WAV)'}
              </label>
            </div>

            {originalStats && (
              <div className="file-stats-container">
                <div className="file-stats-comparison">
                  <div className="stats-column">
                    <h4 className="stats-title">File Info</h4>
                    <div className="stats-grid">
                      <div className="stat-item">
                        <span className="stat-label">Size:</span>
                        <span className="stat-value">{formatFileSize(originalStats.size)}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Duration:</span>
                        <span className="stat-value">{formatDuration(originalStats.duration)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <button 
              type="submit" 
              disabled={!file || loading}
              className="btn btn-primary"
            >
              {loading ? 'Processing...' : 'Process Meeting'}
            </button>
          </form>

          {loading && (
            <div className="loading">
              <div className="spinner"></div>
              <p>Transcribing and analyzing your meeting...</p>
              <p className="loading-subtext">This may take a minute</p>
            </div>
          )}

          {error && (
            <div className="error">
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {result && (
          <div className="results">
            <div className="results-header">
              <h2>Meeting Analysis</h2>
              <button 
                onClick={handleDownloadDocx}
                disabled={downloadingDocx}
                className="btn btn-secondary"
              >
                {downloadingDocx ? 'Generating...' : 'Download as Word'}
              </button>
            </div>

            <section className="result-section">
              <h3>Summary</h3>
              <div className="card">
                <p className="summary-text">{result.notes.summary}</p>
              </div>
            </section>

            {result.notes.participants.length > 0 && (
              <section className="result-section">
                <h3>Participants</h3>
                <div className="card">
                  <ul className="participants-list">
                    {result.notes.participants.map((participant, idx) => (
                      <li key={idx}>{participant}</li>
                    ))}
                  </ul>
                </div>
              </section>
            )}

            {result.notes.decisions.length > 0 && (
              <section className="result-section">
                <h3>Decisions Made</h3>
                <div className="card">
                  <ul className="decisions-list">
                    {result.notes.decisions.map((decision, idx) => (
                      <li key={idx}>{decision}</li>
                    ))}
                  </ul>
                </div>
              </section>
            )}

            {result.notes.action_items.length > 0 && (
              <section className="result-section">
                <h3>Action Items</h3>
                <div className="card">
                  <ul className="action-items-list">
                    {result.notes.action_items.map((item, idx) => (
                      <li key={idx}>
                        <div className="action-item">
                          <span className="action-item-text">{item.item}</span>
                          {item.owner && (
                            <span className="action-item-owner">👤 {item.owner}</span>
                          )}
                          {item.due_date && (
                            <span className="action-item-date">📅 {item.due_date}</span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
            )}

            <section className="result-section">
              <h3>Full Transcript</h3>
              <div className="card transcript">
                <pre className="transcript-text">{result.transcript}</pre>
              </div>
            </section>

            <div className="model-info">
              <small>
                Transcription: {result.model_info.transcription_model} | 
                Summary: {result.model_info.llm_model}
              </small>
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        <p>Powered by AI - Whisper Transcription & LLM Summarization</p>
      </footer>
    </div>
  );
}

export default App;
