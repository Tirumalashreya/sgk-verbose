import Constants from 'expo-constants';
import { isWeb, storage } from './platform';

// Backend URL. EXPO_PUBLIC_API_BASE wins; on a phone, "localhost" is the phone
// itself, so default to the computer that is serving the app through Expo.
const devHost = (Constants.expoConfig?.hostUri || '').split(':')[0];
export const API_BASE = process.env.EXPO_PUBLIC_API_BASE
  || (!isWeb && devHost ? `http://${devHost}:8001` : 'http://localhost:8001');

// ── Auth ─────────────────────────────────────────────────────────────────
// Fixed username/password (APP_USERS in the backend's .env), not a signup
// flow — entered once on the Login screen, then sent as HTTP Basic Auth on
// every request after that. Stored as one "user:pass" string rather than
// two keys so there's only ever one thing to clear on logout.
const CRED_KEY = 'app_credentials';

export const getCredentials = async () => {
  const raw = await storage.get(CRED_KEY);
  if (!raw) return null;
  const i = raw.indexOf(':');
  return i === -1 ? null : { username: raw.slice(0, i), password: raw.slice(i + 1) };
};
export const saveCredentials = (username, password) => storage.set(CRED_KEY, `${username}:${password}`);
export const clearCredentials = () => storage.remove(CRED_KEY);

// A minimal, self-contained base64 encoder — not relying on btoa being
// present (older RN/Hermes builds didn't ship it; writing our own means
// this never silently breaks on some device just because a polyfill
// changed), since this only ever needs to handle plain ASCII credentials.
const _B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
function base64Encode(str) {
  let out = '';
  for (let i = 0; i < str.length; i += 3) {
    const a = str.charCodeAt(i), b = str.charCodeAt(i + 1), c = str.charCodeAt(i + 2);
    out += _B64[a >> 2] + _B64[((a & 3) << 4) | (isNaN(b) ? 0 : b >> 4)]
      + (isNaN(b) ? '=' : _B64[((b & 15) << 2) | (isNaN(c) ? 0 : c >> 6)])
      + (isNaN(c) ? '=' : _B64[c & 63]);
  }
  return out;
}

const authToken = async () => {
  const creds = await getCredentials();
  return creds ? base64Encode(`${creds.username}:${creds.password}`) : null;
};

// Set once from App.js — called whenever any request comes back 401, so the
// whole app can drop back to the Login screen in one place instead of every
// screen having to notice its own failed fetch.
let onUnauthorized = null;
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

/** Every API call goes through this instead of bare fetch() — it's the one
 * place that attaches the Basic Auth header and reacts to a 401, so no
 * individual call below has to think about auth at all. */
async function apiFetch(path, options = {}) {
  const token = await authToken();
  const headers = { ...(options.headers || {}), ...(token ? { Authorization: `Basic ${token}` } : {}) };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    await clearCredentials();
    onUnauthorized && onUnauthorized();
  }
  return res;
}

/** A plain GET /health with the given (not-yet-saved) credentials — used by
 * the Login screen to check them before storing anything. Deliberately
 * bypasses apiFetch (which reads *stored* credentials, not these). */
export const tryLogin = async (username, password) => {
  const token = base64Encode(`${username}:${password}`);
  const res = await fetch(`${API_BASE}/health`, { headers: { Authorization: `Basic ${token}` } });
  return res.ok;
};

export const startSession = async (youtubeUrl) => {
  const res = await apiFetch('/start-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ youtube_url: youtubeUrl }),
  });
  return res.json();
};

export const getSessions = async (full = false) => {
  const res = await apiFetch(`/sessions${full ? '?full=true' : ''}`);
  return res.json();
};

export const getSession = async (sessionId) => {
  const res = await apiFetch(`/sessions/${sessionId}`);
  return res.json();
};

/** liveSessionId: the id /start-live returned — stops that exact recording,
 * not just "whatever this login's most recent one was" (the same shared
 * login can be in use on two phones at once). */
export const stopSession = async (liveSessionId) => {
  const res = await apiFetch('/stop-session', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ live_session_id: liveSessionId || null }),
  });
  return res.json();
};

export const searchRag = async (query) => {
  const res = await apiFetch('/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  return res.json();
};

/** Start recording; with continueId the new minutes are added to that earlier recording. */
export const startLive = async (continueId) => {
  const res = await apiFetch('/start-live', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ continue_id: continueId || null }),
  });
  return res.json();
};

// A file reference in the shape FormData needs on this platform
async function filePart(f) {
  if (!isWeb) return { uri: f.uri, name: f.name, type: f.type || 'audio/mpeg' };
  if (f.file) return f.file;
  return (await fetch(f.uri)).blob();          // web recordings are blob: URLs
}

/** Upload a whole audio file ({ name, uri, type, file? }). With live, it is the
 *  next minute of the mic recording in progress — liveSessionId (from
 *  startLive's response) says exactly which one, so two phones sharing one
 *  login never land pieces in the same document. */
export const uploadAudio = async (f, { live = false, liveSessionId } = {}) => {
  const formData = new FormData();
  const part = await filePart(f);
  if (isWeb) formData.append('file', part, f.name || 'upload.mp3');
  else formData.append('file', part);
  if (live) formData.append('live', '1');
  if (live && liveSessionId) formData.append('live_session_id', liveSessionId);
  const res = await apiFetch('/upload-audio', { method: 'POST', body: formData });
  if (!res.ok) throw new Error(`upload failed (${res.status})`);
  return res.json();
};

/** Discard an upload still processing. Already-in-flight API calls finish on
 * the backend (can't be force-killed mid-request), but nothing new starts
 * and the result is never saved as a session. */
export const cancelUpload = async (digest) => {
  const res = await apiFetch(`/upload-audio/${digest}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`cancel failed (${res.status})`);
  return res.json();
};

/** A manual correction from the Reading screen's edit mode — replaces the
 * notes text and/or title outright (a human override, never re-validated). */
export const updateNotes = async (sessionId, notes, title) => {
  const payload = {};
  if (notes !== undefined) payload.notes = notes;
  if (title !== undefined) payload.title = title;
  const res = await apiFetch(`/sessions/${sessionId}/notes`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`save failed (${res.status})`);
  return res.json();
};

export const updateSessionTitle = async (sessionId, title) => {
  const res = await apiFetch(`/sessions/${sessionId}/title`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`rename failed (${res.status})`);
  return res.json();
};

export const deleteSession = async (sessionId) => {
  const res = await apiFetch(`/sessions/${sessionId}`, { method: 'DELETE' });
  return res.json();
};

/** Notes with [MM:SS] markers, anchored to the real audio. Cached server-side
 * after the first build — expect the first call for a recording to take a
 * while (it re-transcribes the audio to recover timing), later ones to be
 * instant. Throws 'unavailable' when the original audio is no longer on
 * disk, so the caller can show that distinctly from a real error. */
export const getTimestampedNotes = async (sessionId) => {
  const res = await apiFetch(`/sessions/${sessionId}/timestamps`);
  if (res.status === 404) throw new Error('unavailable');
  if (!res.ok) throw new Error(`timestamps failed (${res.status})`);
  return (await res.json()).notes_timestamped;
};

export const downloadSessionAudio = async (sessionId, customTitle) => {
  const token = await authToken();
  const url = `${API_BASE}/sessions/${sessionId}/audio`;
  const cleanTitle = (customTitle || 'pravachanam').replace(/[^a-z0-9\u0C00-\u0C7F ]/gi, '_').trim() || 'recording';

  if (isWeb) {
    const res = await fetch(url, {
      headers: token ? { Authorization: `Basic ${token}` } : {},
    });
    if (!res.ok) throw new Error('Audio not available');

    let ext = '.m4a';
    const cd = res.headers.get('content-disposition') || '';
    const match = cd.match(/filename=["']?([^"';]+)["']?/i);
    if (match && match[1]) {
      const dotIdx = match[1].lastIndexOf('.');
      if (dotIdx !== -1) ext = match[1].slice(dotIdx);
    } else {
      const ct = res.headers.get('content-type') || '';
      if (ct.includes('audio/webm')) ext = '.webm';
      else if (ct.includes('audio/mpeg')) ext = '.mp3';
      else if (ct.includes('audio/wav')) ext = '.wav';
      else if (ct.includes('audio/mp4') || ct.includes('audio/aac')) ext = '.m4a';
    }
    const fileName = `${cleanTitle}${ext}`;

    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(blobUrl), 2000);
    return;
  }

  const FileSystemLegacy = await import('expo-file-system/legacy');
  const Sharing = await import('expo-sharing');
  const fileName = `${cleanTitle}.m4a`;
  const destUri = `${FileSystemLegacy.cacheDirectory}${fileName}`;
  await FileSystemLegacy.downloadAsync(url, destUri, {
    headers: token ? { Authorization: `Basic ${token}` } : {},
  });
  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(destUri);
  }
};

export const mergeSessions = async (ids) => {
  const res = await apiFetch('/merge-sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Merge failed');
  }
  return res.json();
};

export const createWebSocket = async (onMessage, onOpen, onClose) => {
  const token = await authToken();
  const wsUrl = API_BASE.replace(/^http/, 'ws') + '/ws' + (token ? `?token=${token}` : '');
  const ws = new WebSocket(wsUrl);
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
