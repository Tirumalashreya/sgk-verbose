// Backend URL — override with EXPO_PUBLIC_API_BASE (e.g. http://localhost:8001)
export const API_BASE = process.env.EXPO_PUBLIC_API_BASE || 'http://localhost:8000';
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

export const uploadAudio = async (file) => {
  const formData = new FormData();
  formData.append('file', file, file.name || 'upload.mp3');
  const res = await fetch(`${API_BASE}/upload-audio`, { method: 'POST', body: formData });
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
