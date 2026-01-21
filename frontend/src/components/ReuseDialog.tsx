import { HistoryEntry } from '../types';

interface ReuseDialogProps {
  isOpen: boolean;
  entry: HistoryEntry | null;
  onUseCache: () => void;
  onReprocess: () => void;
  onCancel: () => void;
}

export function ReuseDialog({ isOpen, entry, onUseCache, onReprocess, onCancel }: ReuseDialogProps) {
  if (!isOpen || !entry) return null;

  const formatDate = (timestamp: number): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    
    return `on ${date.toLocaleDateString()}`;
  };

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="reuse-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="reuse-dialog-header">
          <h2>File Already Processed</h2>
        </div>

        <div className="reuse-dialog-content">
          <p className="reuse-dialog-message">
            This file was previously processed <strong>{formatDate(entry.processedAt)}</strong>.
          </p>

          <div className="reuse-dialog-info">
            <div className="reuse-info-item">
              <span className="reuse-info-label">Filename:</span>
              <span className="reuse-info-value">{entry.fileName}</span>
            </div>
            <div className="reuse-info-item">
              <span className="reuse-info-label">Transcription Model:</span>
              <span className="reuse-info-value">{entry.metadata.transcriptionModel}</span>
            </div>
            {entry.metadata.llmModel && (
              <div className="reuse-info-item">
                <span className="reuse-info-label">Summary Model:</span>
                <span className="reuse-info-value">{entry.metadata.llmModel}</span>
              </div>
            )}
            <div className="reuse-info-item">
              <span className="reuse-info-label">Speakers:</span>
              <span className="reuse-info-value">{entry.metadata.speakerCount}</span>
            </div>
            <div className="reuse-info-item">
              <span className="reuse-info-label">Words:</span>
              <span className="reuse-info-value">{entry.metadata.wordCount.toLocaleString()}</span>
            </div>
          </div>

          <p className="reuse-dialog-question">
            Would you like to use the cached results or reprocess the file?
          </p>
        </div>

        <div className="reuse-dialog-actions">
          <button className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button className="btn btn-reprocess" onClick={onReprocess}>
            Reprocess File
          </button>
          <button className="btn btn-primary" onClick={onUseCache}>
            Use Cached Results
          </button>
        </div>
      </div>
    </div>
  );
}
