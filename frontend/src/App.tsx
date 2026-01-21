import { useState, FormEvent } from 'react';
import { TranscribeResponse, SummarizeResponse } from './types';
import './style.css';

const API_BASE = '/api';

interface FileStats {
  size: number;
  duration: number;
}

interface ProcessingState {
  transcribing: boolean;
  summarizing: boolean;
}

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [originalStats, setOriginalStats] = useState<FileStats | null>(null);
  const [processing, setProcessing] = useState<ProcessingState>({ transcribing: false, summarizing: false });
  const [transcriptData, setTranscriptData] = useState<TranscribeResponse | null>(null);
  const [summaryData, setSummaryData] = useState<SummarizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
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
    setSummaryError(null);
    setTranscriptData(null);
    setSummaryData(null);

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

    setProcessing({ transcribing: true, summarizing: false });
    setError(null);
    setSummaryError(null);
    setTranscriptData(null);
    setSummaryData(null);

    try {
      // Step 1: Transcribe the audio
      const formData = new FormData();
      formData.append('file', file);

      const transcribeResponse = await fetch(`${API_BASE}/meetings/transcribe`, {
        method: 'POST',
        body: formData,
      });

      if (!transcribeResponse.ok) {
        const errorData = await transcribeResponse.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || `Transcription failed: ${transcribeResponse.status}`);
      }

      const transcript: TranscribeResponse = await transcribeResponse.json();
      setTranscriptData(transcript);
      
      // Step 2: Summarize the transcript
      setProcessing({ transcribing: false, summarizing: true });
      
      try {
        const summarizeResponse = await fetch(`${API_BASE}/meetings/summarize`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            transcript: transcript.transcript_text,
          }),
        });

        if (!summarizeResponse.ok) {
          const errorData = await summarizeResponse.json().catch(() => ({ error: 'Unknown error' }));
          throw new Error(errorData.error || `Summarization failed: ${summarizeResponse.status}`);
        }

        const summary: SummarizeResponse = await summarizeResponse.json();
        setSummaryData(summary);
      } catch (summaryErr) {
        // Summarization failed, but we keep the transcript
        setSummaryError(summaryErr instanceof Error ? summaryErr.message : 'Failed to generate summary');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to transcribe meeting');
    } finally {
      setProcessing({ transcribing: false, summarizing: false });
    }
  };

  const handleDownloadDocx = async () => {
    if (!transcriptData || !summaryData) return;

    setDownloadingDocx(true);
    try {
      const response = await fetch(`${API_BASE}/meetings/docx`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          meeting_title: file?.name.replace(/\.[^/.]+$/, '') || 'Meeting',
          transcript: transcriptData.transcript_text,
          notes: summaryData.notes,
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

  const getSpeakerColor = (speaker: string): string => {
    const colors = [
      '#3b82f6', // blue
      '#10b981', // green
      '#f59e0b', // amber
      '#ef4444', // red
      '#8b5cf6', // purple
      '#ec4899', // pink
      '#14b8a6', // teal
      '#f97316', // orange
    ];
    const index = speaker.charCodeAt(speaker.length - 1) % colors.length;
    return colors[index];
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
                disabled={processing.transcribing || processing.summarizing}
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
              disabled={!file || processing.transcribing || processing.summarizing}
              className="btn btn-primary"
            >
              {processing.transcribing 
                ? 'Transcribing...' 
                : processing.summarizing 
                ? 'Summarizing...' 
                : 'Process Meeting'}
            </button>
          </form>

          {processing.transcribing && (
            <div className="loading">
              <div className="spinner"></div>
              <p>Transcribing your meeting audio...</p>
              <p className="loading-subtext">This may take a minute</p>
            </div>
          )}

          {processing.summarizing && (
            <div className="loading">
              <div className="spinner"></div>
              <p>Generating meeting summary...</p>
              <p className="loading-subtext">Almost done!</p>
            </div>
          )}

          {error && (
            <div className="error">
              <strong>Error:</strong> {error}
            </div>
          )}

          {summaryError && transcriptData && (
            <div className="error" style={{ backgroundColor: '#fef3c7', color: '#92400e', border: '1px solid #fbbf24' }}>
              <strong>Note:</strong> Summary generation failed ({summaryError}), but transcript is available below.
            </div>
          )}
        </div>

        {transcriptData && (
          <div className="results">
            <div className="results-header">
              <h2>Meeting Analysis</h2>
              {summaryData && (
                <button 
                  onClick={handleDownloadDocx}
                  disabled={downloadingDocx}
                  className="btn btn-secondary"
                >
                  {downloadingDocx ? 'Generating...' : 'Download as Word'}
                </button>
              )}
            </div>

            {summaryData && (
              <>
                <section className="result-section">
                  <h3>Summary</h3>
                  <div className="card">
                    <p className="summary-text">{summaryData.notes.summary}</p>
                  </div>
                </section>

                {summaryData.notes.participants.length > 0 && (
                  <section className="result-section">
                    <h3>Participants</h3>
                    <div className="card">
                      <ul className="participants-list">
                        {summaryData.notes.participants.map((participant, idx) => (
                          <li key={idx}>{participant}</li>
                        ))}
                      </ul>
                    </div>
                  </section>
                )}

                {summaryData.notes.decisions.length > 0 && (
                  <section className="result-section">
                    <h3>Decisions Made</h3>
                    <div className="card">
                      <ul className="decisions-list">
                        {summaryData.notes.decisions.map((decision, idx) => (
                          <li key={idx}>{decision}</li>
                        ))}
                      </ul>
                    </div>
                  </section>
                )}

                {summaryData.notes.action_items.length > 0 && (
                  <section className="result-section">
                    <h3>Action Items</h3>
                    <div className="card">
                      <ul className="action-items-list">
                        {summaryData.notes.action_items.map((item, idx) => (
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
              </>
            )}

            <section className="result-section">
              <h3>Transcript with Speakers</h3>
              <div className="card transcript">
                {transcriptData.segments.length > 0 ? (
                  <div className="transcript-segments">
                    {transcriptData.segments.map((segment, idx) => (
                      <div key={idx} className="transcript-segment" style={{ marginBottom: '12px' }}>
                        <span 
                          className="speaker-label" 
                          style={{ 
                            color: getSpeakerColor(segment.speaker),
                            fontWeight: 'bold',
                            marginRight: '8px'
                          }}
                        >
                          [{segment.speaker}]
                        </span>
                        <span className="segment-text">{segment.text}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <pre className="transcript-text">{transcriptData.transcript_text}</pre>
                )}
              </div>
            </section>

            <div className="model-info">
              <small>
                Transcription: {transcriptData.transcription_model}
                {summaryData && ` | Summary: ${summaryData.llm_model}`}
              </small>
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        <p>Powered by AI - Speechmatics Transcription & LLM Summarization</p>
      </footer>
    </div>
  );
}

export default App;
