/**
 * Computes SHA-256 hash of a file's content
 * @param file - The file to hash
 * @returns Promise resolving to hex-encoded hash string
 */
export async function computeFileHash(file: File): Promise<string> {
  // Read file as ArrayBuffer
  const arrayBuffer = await file.arrayBuffer();
  
  // Compute SHA-256 hash using Web Crypto API
  const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
  
  // Convert ArrayBuffer to hex string
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  
  return hashHex;
}
