import { HistoryEntry, SummaryVersion } from '../types';

const DB_NAME = 'TranscriptTurboHistory';
const STORE_NAME = 'history';
const DB_VERSION = 2;

/**
 * Normalizes a history entry to ensure it has the new structure
 * This is a safety check for entries that might not have been migrated yet
 */
function normalizeHistoryEntry(entry: any): HistoryEntry {
  if (!entry) {
    throw new Error('Entry is null or undefined');
  }
  
  // If entry already has summaries array, return as is
  if (entry.summaries !== undefined) {
    return entry as HistoryEntry;
  }
  
  // Migrate from old structure (summary field) to new structure (summaries array)
  const summaries: SummaryVersion[] = [];
  if (entry.summary !== null && entry.summary !== undefined) {
    summaries.push({
      summary: entry.summary,
      generatedAt: entry.processedAt || Date.now(),
      version: 1
    });
  }
  
  // Create normalized entry
  const normalized: HistoryEntry = {
    ...entry,
    summaries,
  };
  
  // Remove old summary field if it exists
  delete (normalized as any).summary;
  
  return normalized;
}

/**
 * Opens the IndexedDB database
 */
function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => {
      reject(new Error('Failed to open database'));
    };

    request.onsuccess = () => {
      resolve(request.result);
    };

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      const oldVersion = event.oldVersion;
      
      // Create object store if it doesn't exist
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const objectStore = db.createObjectStore(STORE_NAME, { keyPath: 'fileHash' });
        // Create index on processedAt for sorting
        objectStore.createIndex('processedAt', 'processedAt', { unique: false });
      } else if (oldVersion < 2) {
        // Migration from version 1 to 2: convert summary to summaries array
        const transaction = (event.target as IDBOpenDBRequest).transaction;
        if (!transaction) return;
        
        const objectStore = transaction.objectStore(STORE_NAME);
        const request = objectStore.openCursor();
        
        request.onsuccess = (event) => {
          const cursor = (event.target as IDBRequest<IDBCursorWithValue>).result;
          if (cursor) {
            const entry = cursor.value as any;
            
            // Check if entry has old 'summary' field and needs migration
            if (entry.summary !== undefined && !entry.summaries) {
              const summaries: SummaryVersion[] = [];
              
              // Convert old summary field to new summaries array
              if (entry.summary !== null) {
                summaries.push({
                  summary: entry.summary,
                  generatedAt: entry.processedAt, // Use processedAt as fallback
                  version: 1
                });
              }
              
              // Update entry with new structure
              entry.summaries = summaries;
              delete entry.summary; // Remove old field
              
              cursor.update(entry);
            }
            
            cursor.continue();
          }
        };
      }
    };
  });
}

/**
 * Saves a history entry to IndexedDB
 */
export async function saveHistoryEntry(entry: HistoryEntry): Promise<void> {
  const db = await openDatabase();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const objectStore = transaction.objectStore(STORE_NAME);
    const request = objectStore.put(entry);

    request.onsuccess = () => {
      resolve();
    };

    request.onerror = () => {
      reject(new Error('Failed to save history entry'));
    };

    transaction.oncomplete = () => {
      db.close();
    };
  });
}

/**
 * Retrieves a history entry by file hash
 */
export async function getHistoryEntry(fileHash: string): Promise<HistoryEntry | null> {
  const db = await openDatabase();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const objectStore = transaction.objectStore(STORE_NAME);
    const request = objectStore.get(fileHash);

    request.onsuccess = () => {
      const result = request.result;
      if (result) {
        try {
          resolve(normalizeHistoryEntry(result));
        } catch (e) {
          console.error('Failed to normalize history entry:', e);
          resolve(null);
        }
      } else {
        resolve(null);
      }
    };

    request.onerror = () => {
      reject(new Error('Failed to get history entry'));
    };

    transaction.oncomplete = () => {
      db.close();
    };
  });
}

/**
 * Retrieves all history entries sorted by processedAt (newest first)
 */
export async function getAllHistory(): Promise<HistoryEntry[]> {
  const db = await openDatabase();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const objectStore = transaction.objectStore(STORE_NAME);
    const index = objectStore.index('processedAt');
    const request = index.openCursor(null, 'prev'); // 'prev' for descending order
    
    const entries: HistoryEntry[] = [];

    request.onsuccess = (event) => {
      const cursor = (event.target as IDBRequest<IDBCursorWithValue>).result;
      if (cursor) {
        try {
          entries.push(normalizeHistoryEntry(cursor.value));
        } catch (e) {
          console.error('Failed to normalize history entry:', e);
        }
        cursor.continue();
      } else {
        resolve(entries);
      }
    };

    request.onerror = () => {
      reject(new Error('Failed to get all history'));
    };

    transaction.oncomplete = () => {
      db.close();
    };
  });
}

/**
 * Deletes a history entry by file hash
 */
export async function deleteHistoryEntry(fileHash: string): Promise<void> {
  const db = await openDatabase();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const objectStore = transaction.objectStore(STORE_NAME);
    const request = objectStore.delete(fileHash);

    request.onsuccess = () => {
      resolve();
    };

    request.onerror = () => {
      reject(new Error('Failed to delete history entry'));
    };

    transaction.oncomplete = () => {
      db.close();
    };
  });
}

/**
 * Clears all history entries
 */
export async function clearAllHistory(): Promise<void> {
  const db = await openDatabase();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const objectStore = transaction.objectStore(STORE_NAME);
    const request = objectStore.clear();

    request.onsuccess = () => {
      resolve();
    };

    request.onerror = () => {
      reject(new Error('Failed to clear history'));
    };

    transaction.oncomplete = () => {
      db.close();
    };
  });
}

/**
 * Enforces storage limit by keeping only the newest entries
 * @param maxItems - Maximum number of entries to keep
 */
export async function enforceStorageLimit(maxItems: number): Promise<void> {
  const allEntries = await getAllHistory();
  
  // If we're within the limit, no action needed
  if (allEntries.length <= maxItems) {
    return;
  }

  // Delete entries beyond the limit (oldest ones)
  const entriesToDelete = allEntries.slice(maxItems);
  
  for (const entry of entriesToDelete) {
    await deleteHistoryEntry(entry.fileHash);
  }
}

/**
 * Gets the count of history entries
 */
export async function getHistoryCount(): Promise<number> {
  const db = await openDatabase();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const objectStore = transaction.objectStore(STORE_NAME);
    const request = objectStore.count();

    request.onsuccess = () => {
      resolve(request.result);
    };

    request.onerror = () => {
      reject(new Error('Failed to get history count'));
    };

    transaction.oncomplete = () => {
      db.close();
    };
  });
}

/**
 * Adds a new summary version to an existing history entry
 */
export async function addSummaryVersion(fileHash: string, summaryVersion: SummaryVersion): Promise<void> {
  const db = await openDatabase();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const objectStore = transaction.objectStore(STORE_NAME);
    const request = objectStore.get(fileHash);

    request.onsuccess = () => {
      const entry = request.result as HistoryEntry | undefined;
      if (!entry) {
        reject(new Error('History entry not found'));
        return;
      }

      // Add new version to summaries array
      entry.summaries = entry.summaries || [];
      entry.summaries.push(summaryVersion);
      
      // Update metadata with latest LLM model
      if (entry.metadata) {
        entry.metadata.llmModel = summaryVersion.summary.llm_model;
      }

      // Save updated entry
      const updateRequest = objectStore.put(entry);
      updateRequest.onsuccess = () => {
        resolve();
      };
      updateRequest.onerror = () => {
        reject(new Error('Failed to update history entry'));
      };
    };

    request.onerror = () => {
      reject(new Error('Failed to get history entry'));
    };

    transaction.oncomplete = () => {
      db.close();
    };
  });
}
