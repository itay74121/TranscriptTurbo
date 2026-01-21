import { HistoryEntry } from '../types';

const DB_NAME = 'TranscriptTurboHistory';
const STORE_NAME = 'history';
const DB_VERSION = 1;

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
      
      // Create object store if it doesn't exist
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const objectStore = db.createObjectStore(STORE_NAME, { keyPath: 'fileHash' });
        // Create index on processedAt for sorting
        objectStore.createIndex('processedAt', 'processedAt', { unique: false });
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
      resolve(request.result || null);
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
        entries.push(cursor.value);
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
