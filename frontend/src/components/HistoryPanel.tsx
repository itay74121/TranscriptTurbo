import { useState, useEffect } from 'react';
import { HistoryEntry } from '../types';
import { getAllHistory, deleteHistoryEntry, clearAllHistory } from '../utils/historyStorage';

interface HistoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadEntry: (entry: HistoryEntry) => void;
}

export function HistoryPanel({ isOpen, onClose, onLoadEntry }: HistoryPanelProps) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadHistory();
    }
  }, [isOpen]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const entries = await getAllHistory();
      setHistory(entries);
    } catch (error) {
      console.error('Failed to load history:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (fileHash: string, event: React.MouseEvent) => {
    event.stopPropagation();
    try {
      await deleteHistoryEntry(fileHash);
      setHistory(history.filter(entry => entry.fileHash !== fileHash));
    } catch (error) {
      console.error('Failed to delete entry:', error);
    }
  };

  const handleClearAll = async () => {
    try {
      await clearAllHistory();
      setHistory([]);
      setShowClearConfirm(false);
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  };

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

  const formatDate = (timestamp: number): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="history-panel" onClick={(e) => e.stopPropagation()}>
        <div className="history-header">
          <h2>Processing History</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>

        {loading ? (
          <div className="history-loading">
            <div className="spinner"></div>
            <p>Loading history...</p>
          </div>
        ) : history.length === 0 ? (
          <div className="history-empty">
            <p>No processing history yet</p>
            <p className="history-empty-subtitle">Process your first audio file to see it here</p>
          </div>
        ) : (
          <>
            <div className="history-actions">
              <span className="history-count">{history.length} file{history.length !== 1 ? 's' : ''}</span>
              {!showClearConfirm ? (
                <button 
                  className="btn-clear-history" 
                  onClick={() => setShowClearConfirm(true)}
                >
                  Clear All
                </button>
              ) : (
                <div className="clear-confirm">
                  <span>Are you sure?</span>
                  <button className="btn-confirm-yes" onClick={handleClearAll}>Yes</button>
                  <button className="btn-confirm-no" onClick={() => setShowClearConfirm(false)}>No</button>
                </div>
              )}
            </div>

            <div className="history-list">
              {history.map((entry) => (
                <div 
                  key={entry.fileHash} 
                  className="history-item"
                  onClick={() => {
                    onLoadEntry(entry);
                    onClose();
                  }}
                >
                  <div className="history-item-header">
                    <h3 className="history-item-filename">{entry.fileName}</h3>
                    <button 
                      className="btn-delete-entry"
                      onClick={(e) => handleDelete(entry.fileHash, e)}
                      title="Delete this entry"
                    >
                      🗑️
                    </button>
                  </div>
                  
                  <div className="history-item-meta">
                    <span className="history-meta-item">
                      <strong>Processed:</strong> {formatDate(entry.processedAt)}
                    </span>
                    <span className="history-meta-item">
                      <strong>Duration:</strong> {formatDuration(entry.duration)}
                    </span>
                    <span className="history-meta-item">
                      <strong>Size:</strong> {formatFileSize(entry.fileSize)}
                    </span>
                  </div>

                  <div className="history-item-stats">
                    <span className="history-stat-item">
                      {entry.metadata.speakerCount} speaker{entry.metadata.speakerCount !== 1 ? 's' : ''}
                    </span>
                    <span className="history-stat-item">
                      {entry.metadata.wordCount.toLocaleString()} words
                    </span>
                  </div>

                  <div className="history-item-models">
                    <small>
                      {entry.metadata.transcriptionModel}
                      {entry.metadata.llmModel && ` • ${entry.metadata.llmModel}`}
                    </small>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
