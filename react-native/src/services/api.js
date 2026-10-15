import Constants from 'expo-constants';
import { isWeb } from './platform';

// Backend URL. EXPO_PUBLIC_API_BASE wins; on a phone, "localhost" is the phone
// itself, so default to the computer that is serving the app through Expo.
const devHost = (Constants.expoConfig?.hostUri || '').split(':')[0];
export const API_BASE = process.env.EXPO_PUBLIC_API_BASE
  || (!isWeb && devHost ? `http://${devHost}:8001` : 'http://localhost:8001');
const WS_URL = API_BASE.replace(/^http/, 'ws') + '/ws';

export const startSession = async (youtubeUrl) => {
  const res = await fetch(`${API_BASE}/start-session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ youtube_url: youtubeUrl }),
  });
  return res.json();
};

export const getSessions = async () => {
  const res = await fetch(`${API_BASE}/sessions`);
  return res.json();
};

export const stopSession = async () => {
  const res = await fetch(`${API_BASE}/stop-session`, { method: 'POST' });
  return res.json();
};

export const searchRag = async (query) => {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  return res.json();
};

export const startLive = async () => {
  const res = await fetch(`${API_BASE}/start-live`, { method: 'POST' });
  return res.json();
};

// A file reference in the shape FormData needs on this platform
async function filePart(f) {
  if (!isWeb) return { uri: f.uri, name: f.name, type: f.type || 'audio/mpeg' };
  if (f.file) return f.file;
  return (await fetch(f.uri)).blob();          // web recordings are blob: URLs
}

/** Upload a whole audio file ({ name, uri, type, file? }). With live, it is the
 *  next minute of the mic recording in progress. */
export const uploadAudio = async (f, { live = false } = {}) => {
  const formData = new FormData();
  const part = await filePart(f);
  if (isWeb) formData.append('file', part, f.name || 'upload.mp3');
  else formData.append('file', part);
  if (live) formData.append('live', '1');
  const res = await fetch(`${API_BASE}/upload-audio`, { method: 'POST', body: formData });
  if (!res.ok) throw new Error(`upload failed (${res.status})`);
  return res.json();
};

export const deleteSession = async (sessionId) => {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
  return res.json();
};

export const createWebSocket = (onMessage, onOpen, onClose) => {
  const ws = new WebSocket(WS_URL);
  ws.onopen = () => onOpen && onOpen();
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onMessage(data);
    } catch {}
  };
  ws.onclose = () => onClose && onClose();
  return ws;
};
