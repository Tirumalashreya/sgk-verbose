const BASE_URL = 'http://localhost:8000';

export const startSession = async (youtubeUrl) => {
  const res = await fetch(`${BASE_URL}/start-session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ youtube_url: youtubeUrl }),
  });
  return res.json();
};

export const stopSession = async () => {
  const res = await fetch(`${BASE_URL}/stop-session`, { method: 'POST' });
  return res.json();
};

export const searchQuery = async (query) => {
  const res = await fetch(`${BASE_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  return res.json();
};

export const uploadAudio = async (uri) => {
  const formData = new FormData();
  formData.append('file', {
    uri,
    type: 'audio/m4a',
    name: 'chunk.m4a',
  });
  const res = await fetch(`${BASE_URL}/upload-audio`, {
    method: 'POST',
    body: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.json();
};

export const getSessions = async () => {
  const res = await fetch(`${BASE_URL}/sessions`);
  return res.json();
};

export const createWebSocket = (onMessage, onError) => {
  const ws = new WebSocket(`ws://localhost:8000/ws`);
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onMessage(data);
    } catch {}
  };
  ws.onerror = onError;
  return ws;
};
