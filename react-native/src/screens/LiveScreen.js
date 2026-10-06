import React, { useEffect, useRef, useState } from 'react';
import { View, Text, Image, ScrollView, Pressable, Animated } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { C, F, ACHARYA, acharyaPhoto } from '../theme';
import Waveform from '../components/Waveform';
import { API_BASE, createWebSocket, stopSession } from '../services/api';


// Pipeline stages in the order they run on the backend
const STAGES = [
  { key: 'listener',             label: 'Preparing'    },
  { key: 'transcription',        label: 'Transcribing' },
  { key: 'correction',           label: 'Correcting'   },
  { key: 'shloka_detector',      label: 'Shlokas'      },
  { key: 'knowledge_structurer', label: 'Structuring'  },
  { key: 'summary',              label: 'Summary'      },
  { key: 'formatting',           label: 'Notes'        },
  { key: 'validation',           label: 'Verifying'    },
  { key: 'memory',               label: 'Saving'       },
];
const STAGE_IDX = Object.fromEntries(STAGES.map((s, i) => [s.key, i]));

// Status messages shown in content area while each stage is active
const STAGE_MESSAGES = {
  listener:             'Preparing audio...',
  transcription:        'Transcribing audio into Telugu text...',
  correction:           'Fixing known term misspellings...',
  shloka_detector:      'Detecting Sanskrit shlokas & Tamil pasurams...',
  knowledge_structurer: 'Structuring knowledge from the pravachanam...',
  summary:              'Writing a short summary...',
  formatting:           'Arranging the transcript into paragraphs...',
  validation:           'Checking notes match the transcript word-for-word...',
  memory:               'Saving to library...',
};

function fmt(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m + ':' + String(s).padStart(2, '0');
}

function Pulse() {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const a = Animated.loop(Animated.timing(v, { toValue: 1, duration: 2400, useNativeDriver: true }));
    a.start();
    return () => a.stop();
  }, []);
  return (
    <Animated.View style={{
      position: 'absolute', width: 74, height: 74, borderRadius: 37,
      backgroundColor: 'rgba(224,132,59,0.4)',
      opacity: v.interpolate({ inputRange: [0, 0.7, 1], outputRange: [0.55, 0, 0] }),
      transform: [{ scale: v.interpolate({ inputRange: [0, 1], outputRange: [1, 1.9] }) }],
    }} />
  );
}

// Small pulsing dot for the active stage pill
function ActiveDot() {
  const v = useRef(new Animated.Value(0.4)).current;
  useEffect(() => {
    const a = Animated.loop(Animated.sequence([
      Animated.timing(v, { toValue: 1,   duration: 700, useNativeDriver: true }),
      Animated.timing(v, { toValue: 0.4, duration: 700, useNativeDriver: true }),
    ]));
    a.start();
    return () => a.stop();
  }, []);
  return <Animated.View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: C.saffron, opacity: v, marginRight: 5 }} />;
}

// Horizontal pipeline stepper
function PipelineStepper({ doneSet, activeKey }) {
  const scrollRef = useRef(null);
  const activeIdx = STAGE_IDX[activeKey] ?? -1;

  useEffect(() => {
    if (activeIdx > 2 && scrollRef.current) {
      scrollRef.current.scrollTo({ x: (activeIdx - 2) * 88, animated: true });
    }
  }, [activeIdx]);

  return (
    <ScrollView
      ref={scrollRef}
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ paddingHorizontal: 18, paddingVertical: 10, alignItems: 'center' }}
    >
      {STAGES.map((s, i) => {
        const done   = doneSet.has(s.key);
        const active = s.key === activeKey;

        return (
          <React.Fragment key={s.key}>
            {/* Stage pill */}
            <View style={{
              flexDirection: 'row', alignItems: 'center',
              paddingHorizontal: 10, paddingVertical: 5,
              borderRadius: 99,
              backgroundColor: done   ? 'rgba(80,160,80,0.15)'
                             : active ? 'rgba(224,132,59,0.15)'
                             : 'rgba(255,255,255,0.04)',
              borderWidth: 1,
              borderColor:  done   ? 'rgba(100,200,100,0.35)'
                          : active ? 'rgba(224,132,59,0.45)'
                          : 'rgba(255,255,255,0.08)',
            }}>
              {active && <ActiveDot />}
              {done && (
                <Text style={{ fontSize: 9, color: '#7fdd7f', marginRight: 4 }}>✓</Text>
              )}
              <Text style={{
                fontSize: 10.5,
                fontFamily: F.sansSemi,
                letterSpacing: 0.5,
                color: done   ? '#7fdd7f'
                     : active ? C.saffron
                     : 'rgba(255,255,255,0.25)',
              }}>{s.label}</Text>
            </View>

            {/* Arrow between stages */}
            {i < STAGES.length - 1 && (
              <Text style={{ color: 'rgba(255,255,255,0.12)', marginHorizontal: 4, fontSize: 11 }}>›</Text>
            )}
          </React.Fragment>
        );
      })}
    </ScrollView>
  );
}

const makeBanner = (step, icon, label, sub, color) => ({
  kind: 'stage_banner', step, icon, label, sub, color,
});

const SHLOKA_LINE = /^\*\*"(.+?)"\*\*(?:\s*\(([^)]*)\))?$/;

function chunkToLines(data) {
  const raw = data.notes || data.transcript || '';
  const shlokas = data.shlokas || [];
  const result = [];
  let paraLines = [];

  const flushPara = () => {
    if (paraLines.length > 0) {
      result.push({ kind: 'para', te: paraLines.join(' ') });
      paraLines = [];
    }
  };

  for (const line of raw.split('\n')) {
    const t = line.trim();
    if (!t) { flushPara(); continue; }
    // **"verse"** (devanagari) — shloka line from the backend formatter
    const sm = t.match(SHLOKA_LINE);
    if (sm) {
      flushPara();
      const meta = shlokas.find(s => s.text?.trim() === sm[1].trim());
      result.push({ kind: 'shloka', ref: meta?.type || 'Shloka', dev: sm[1], original: sm[2] || '' });
      continue;
    }
    const hm = t.match(/^\*{1,2}(.+?)\*{1,2}$/);
    if (hm) { flushPara(); result.push({ kind: 'heading', te: hm[1].trim() }); continue; }
    const hit = shlokas.find(s => t.includes(s.text?.trim()?.slice(0, 20)));
    if (hit) {
      flushPara();
      result.push({ kind: 'shloka', ref: hit.type || 'Shloka', dev: t, original: hit.original || '' });
    } else {
      paraLines.push(t);
    }
  }
  flushPara();
  return result;
}

export default function LiveScreen({ go, t, sessionUrl, pendingUpload, clearPendingUpload, upload, setUpload }) {
  const insets = useSafeAreaInsets();

  // session state
  const [clock, setClock]       = useState(0);
  const [active, setActive]     = useState(false);
  const [recording, setRecording] = useState(false);
  const [isFileUpload, setIsFileUpload] = useState(false);
  const [title, setTitle]       = useState('');
  const [connected, setConnected] = useState(false);
  const [saving, setSaving]     = useState(false);
  const [done, setDone]         = useState(false);

  // pipeline progress
  const [doneStages, setDoneStages]   = useState(new Set());
  const [activeStage, setActiveStage] = useState(null);

  // progressive content
  const [transcript, setTranscript] = useState('');
  const [shlokas, setShlokas]       = useState([]);
  const [notes, setNotes]           = useState('');
  const [lines, setLines]           = useState([]);

  const scRef        = useRef(null);
  const wsRef        = useRef(null);
  const timerRef     = useRef(null);
  const fileUploadRef = useRef(false); // read by the WebSocket handler, which holds a stale closure
  const mediaRef     = useRef(null);
  const pollRef      = useRef(null);
  const sessionCount = useRef(0);

  // ── WebSocket handler ─────────────────────────────────────────────────────
  const handleWsMessage = (data) => {
    // Pipeline stage just completed → update stepper
    if (data.type === 'agent_progress') {
      const idx = STAGE_IDX[data.agent] ?? -1;
      setDoneStages(prev => {
        const next = new Set(prev);
        STAGES.forEach((s, i) => { if (i <= idx) next.add(s.key); });
        return next;
      });
      // Next stage in list is now active
      const nextStage = STAGES[idx + 1];
      setActiveStage(nextStage ? nextStage.key : null);
    }

    // Step 1 — transcript ready
    if (data.type === 'stage_result' && data.stage === 'transcription') {
      setTranscript(data.transcript || '');
      setLines([
        makeBanner('Step 1', '📝', 'Transcript Ready', 'Audio converted to text', '#6b9fff'),
        ...chunkToLines({ transcript: data.transcript, shlokas: [] }),
      ]);
    }

    // Step 2 — shlokas detected (append banner, re-render transcript with highlights)
    if (data.type === 'stage_result' && data.stage === 'shlokas') {
      const detected = data.shlokas || [];
      setShlokas(detected);
      setLines(prev => {
        const withoutContent = prev.filter(l => l.kind === 'stage_banner');
        return [
          ...withoutContent,
          ...chunkToLines({ transcript, shlokas: detected }),
          makeBanner('Step 2', 'ॐ', `${detected.length} Shlokas Detected`, 'Sanskrit & Tamil verses identified', C.saffron),
        ];
      });
    }

    // Step 3 — notes ready (replace content)
    if (data.type === 'stage_result' && data.stage === 'notes') {
      setNotes(data.notes || '');
      setLines([
        makeBanner('Step 3', '✦', 'Notes Ready', 'Structured notes generated', '#7fdd7f'),
        ...chunkToLines({ notes: data.notes, shlokas }),
      ]);
    }

    // Full result — used for YouTube / mic chunks (no intermediate stage_result events)
    if (data.type === 'chunk_complete') {
      if (data.title) setTitle(data.title);
      if (data.shlokas?.length) setShlokas(data.shlokas);
      if (data.notes)      setNotes(data.notes);
      if (data.transcript) setTranscript(data.transcript);

      // Only inject banner + content if notes/transcript weren't already shown via stage_result
      const contentLines = chunkToLines(data);
      setLines(prev => {
        const alreadyHasContent = prev.some(l => l.kind !== 'stage_banner');
        if (alreadyHasContent) return prev; // stage_result already populated content
        const banner = data.notes
          ? makeBanner('Complete', '✦', 'Notes Ready', 'Structured notes generated', '#7fdd7f')
          : makeBanner('Complete', '📝', 'Transcript Ready', 'Audio converted to text', '#6b9fff');
        return isFileUpload ? [banner, ...contentLines] : [...prev, banner, ...contentLines];
      });

      // File uploads: auto-complete (no manual Stop needed)
      if (fileUploadRef.current) finishUpload();
    }

    if (data.type === 'session_complete') {
      setDone(true);
      setConnected(false);
      clearInterval(timerRef.current);
      // Auto-stop and save for mic recording when session fully completes
      if (recording) {
        stopRecording();
      }
    }
  };

  const startTimer = (startedAt = Date.now()) => {
    clearInterval(timerRef.current);
    const tick = () => setClock(Math.floor((Date.now() - startedAt) / 1000));
    tick();
    timerRef.current = setInterval(tick, 1000);
  };

  // File upload finished (WebSocket result or the app-level session poll)
  const finishUpload = () => {
    if (!fileUploadRef.current) return;
    fileUploadRef.current = false;
    stopPolling();
    setDoneStages(new Set(STAGES.map(s => s.key)));
    setActiveStage(null);
    setDone(true);
    clearInterval(timerRef.current);
    setUpload?.(null);
    setTimeout(() => {
      setActive(false);
      setIsFileUpload(false);
      go('history');
    }, 2000);
  };

  const startWebSocket = () => {
    wsRef.current = createWebSocket(
      handleWsMessage,
      () => setConnected(true),
      () => setConnected(false),
    );
  };

  const startPolling = (knownCount) => {
    sessionCount.current = knownCount;
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/sessions`);
        const data = await res.json();
        const sessions = data.sessions || [];
        if (sessions.length > sessionCount.current) {
          const newest = sessions[sessions.length - 1];
          if (newest.notes) {
            clearInterval(pollRef.current);
            clearInterval(timerRef.current);
            setDoneStages(new Set(STAGES.map(s => s.key)));
            setActiveStage(null);
            setDone(true);
            setTimeout(() => {
              setActive(false);
              setIsFileUpload(false);
              go('history');
            }, 2000);
          }
        }
      } catch (_) {}
    }, 8000);
  };

  const stopPolling = () => clearInterval(pollRef.current);

  const sendAudioChunk = async (blob, filename = 'chunk.webm') => {
    const form = new FormData();
    form.append('file', blob, filename);
    try {
      await fetch(`${API_BASE}/upload-audio`, { method: 'POST', body: form });
    } catch (e) {
      console.warn('[live] upload failed', e);
    }
  };

  // ── Upload file ────────────────────────────────────────────────────────────
  const pickAndUploadFile = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'audio/*,.ogg,.m4a,.mp3,.wav,.webm';
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (file) uploadFile(file);
    };
    input.click();
  };

  const showUploadView = (name, startedAt) => {
    fileUploadRef.current = true;
    setIsFileUpload(true);
    setActive(true);
    setDone(false);
    setTitle(name.replace(/\.[^.]+$/, ''));
    startTimer(startedAt);
    startWebSocket();
  };

  const uploadFile = async (file) => {
    // One upload at a time — a second one would queue the whole pipeline again
    if (upload && (upload.status === 'uploading' || upload.status === 'processing')) return;
    try { await stopSession(); } catch (_) {}
    setIsFileUpload(true);
    setActive(true);
    setLines([]);
    setTranscript('');
    setShlokas([]);
    setNotes('');
    setDoneStages(new Set());
    setActiveStage('listener');
    setDone(false);
    const startedAt = Date.now();
    showUploadView(file.name, startedAt);
    let knownCount = 0;
    try {
      const countData = await (await fetch(`${API_BASE}/sessions`)).json();
      knownCount = (countData.sessions || []).length;
    } catch (_) {}
    setUpload?.({ name: file.name, status: 'uploading', startedAt, knownCount });
    try {
      const form = new FormData();
      form.append('file', file, file.name);
      const res = await fetch(`${API_BASE}/upload-audio`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setUpload?.({ name: file.name, status: 'processing', startedAt, knownCount,
                    duplicate: data.status === 'duplicate' });
    } catch (e) {
      console.warn('[live] upload failed', e);
      setUpload?.({ name: file.name, status: 'error', startedAt, knownCount });
    }
  };

  // Coming back to this screen while an upload is still running → show its progress
  useEffect(() => {
    if (upload && (upload.status === 'uploading' || upload.status === 'processing') && !active) {
      showUploadView(upload.name, upload.startedAt);
    }
    return () => {
      clearInterval(timerRef.current);
      clearInterval(pollRef.current);
      wsRef.current?.close();
    };
  }, []);

  // App-level poll noticed the finished session
  useEffect(() => {
    if (upload?.status === 'done') finishUpload();
  }, [upload?.status]);

  // File picked on the Library screen — run it through the same tracked flow
  useEffect(() => {
    if (!pendingUpload) return;
    const file = pendingUpload;
    clearPendingUpload?.();
    uploadFile(file);
  }, [pendingUpload]);

  // ── Start mic recording ────────────────────────────────────────────────────
  const startRecording = async () => {
    try { await stopSession(); } catch (_) {}
    try { await fetch(`${API_BASE}/start-live`, { method: 'POST' }); } catch (_) {}
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRef.current = { stream };
      setRecording(true);
      setIsFileUpload(false);
      setActive(true);
      setLines([]);
      setTranscript('');
      setShlokas([]);
      setNotes('');
      setDoneStages(new Set());
      setActiveStage('listener');
      setDone(false);
      startTimer();
      startWebSocket();
      const recordChunk = () => {
        const rec = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        const parts = [];
        rec.ondataavailable = (e) => { if (e.data.size > 0) parts.push(e.data); };
        rec.onstop = () => {
          const blob = new Blob(parts, { type: 'audio/webm' });
          if (blob.size > 5000) sendAudioChunk(blob, 'chunk.webm');
          if (mediaRef.current?.stream) recordChunk();
        };
        rec.start();
        setTimeout(() => { try { rec.stop(); } catch (_) {} }, 60000);
        mediaRef.current.recorder = rec;
      };
      recordChunk();
    } catch (e) {
      console.error('[live] mic access denied', e);
      alert('Microphone access denied. Please allow mic access in your browser.');
    }
  };

  // ── Stop mic recording ─────────────────────────────────────────────────────
  const stopRecording = async () => {
    setSaving(true);
    const { recorder, stream } = mediaRef.current || {};
    try { recorder?.stop(); } catch (_) {}
    stream?.getTracks().forEach(t => t.stop());
    mediaRef.current = null;
    setRecording(false);
    clearInterval(timerRef.current);
    wsRef.current?.close();
    await stopSession();
    setTimeout(() => {
      setSaving(false);
      setActive(false);
      go('history');
    }, 1200);
  };

  // ── YouTube session ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!sessionUrl) return;
    setActive(true);
    setLines([]);
    setDoneStages(new Set());
    setActiveStage('listener');
    startTimer();
    startWebSocket();
    return () => {
      clearInterval(timerRef.current);
      wsRef.current?.close();
    };
  }, [sessionUrl]);

  // ── IDLE ───────────────────────────────────────────────────────────────────
  if (!active && !sessionUrl) {
    return (
      <LinearGradient colors={['#2a1a12', '#17120d', '#0f0b08']} style={{ flex: 1 }}>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 }}>
          <Image source={acharyaPhoto} style={{ width: 80, height: 80, borderRadius: 40, borderWidth: 2, borderColor: 'rgba(232,185,107,0.55)', marginBottom: 24 }} />
          <Text style={{ fontFamily: F.serif, fontSize: 24, color: '#f6ecd6', marginBottom: 8 }}>Live Pravachanam</Text>
          <Text style={{ fontSize: 13, color: '#9b875f', textAlign: 'center', lineHeight: 22, marginBottom: 40 }}>
            Record live audio and get real-time Telugu notes with shloka detection.
          </Text>

          <Pressable onPress={startRecording} style={{ alignItems: 'center' }}>
            <View style={{ width: 90, height: 90, borderRadius: 45, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: 'rgba(224,132,59,0.5)', marginBottom: 12 }}>
              <LinearGradient colors={['#e0843b', '#c25a26']} style={{ width: 74, height: 74, borderRadius: 37, alignItems: 'center', justifyContent: 'center' }}>
                <View style={{ width: 24, height: 24, borderRadius: 12, backgroundColor: '#fff4e2' }} />
              </LinearGradient>
            </View>
            <Text style={{ fontSize: 14, color: '#e8b96b', fontFamily: F.sansSemi, letterSpacing: 1 }}>TAP TO RECORD</Text>
          </Pressable>

          <Pressable onPress={pickAndUploadFile} style={{ marginTop: 32, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 22, paddingVertical: 12, borderRadius: 99, borderWidth: 1, borderColor: 'rgba(201,167,75,0.35)' }}>
            <Text style={{ fontSize: 16, color: '#9b875f', marginRight: 8 }}>↑</Text>
            <Text style={{ fontSize: 13, color: '#9b875f', fontFamily: F.sansSemi, letterSpacing: 0.5 }}>Upload Audio File</Text>
          </Pressable>
        </View>
      </LinearGradient>
    );
  }

  // ── ACTIVE SESSION ─────────────────────────────────────────────────────────
  const statusColor = done ? '#7fdd7f' : C.saffron;
  const statusLabel = done
    ? (isFileUpload ? 'DONE · Saving to library...' : `COMPLETE · ${fmt(clock)}`)
    : saving ? 'SAVING...'
    : recording ? `RECORDING · ${fmt(clock)}`
    : isFileUpload ? `PROCESSING · ${fmt(clock)}`
    : connected ? `${t('transcribing')} · ${fmt(clock)}`
    : `CONNECTING · ${fmt(clock)}`;

  const statusDotColor = done ? '#7fdd7f' : recording ? '#e05050' : connected ? C.saffron : '#888';

  return (
    <LinearGradient colors={['#2a1a12', '#17120d', '#0f0b08']} style={{ flex: 1 }}>
      <View style={{ flex: 1 }}>

        {/* Status bar */}
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 22, paddingTop: 10, paddingBottom: 4 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 6, borderRadius: 99, backgroundColor: done ? 'rgba(60,140,60,0.18)' : 'rgba(224,132,59,0.14)', borderWidth: 1, borderColor: done ? 'rgba(100,200,100,0.4)' : 'rgba(224,132,59,0.3)' }}>
            {done
              ? <Text style={{ fontSize: 12, color: '#7fdd7f', marginRight: 6 }}>✓</Text>
              : <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: statusDotColor, marginRight: 8 }} />
            }
            <Text style={{ fontSize: 11, letterSpacing: 1.5, color: statusColor, fontFamily: F.sansSemi }}>{statusLabel}</Text>
          </View>
          {!isFileUpload && !done && (
            <Text style={{ fontSize: 18, color: '#c9b78f' }}>⋯</Text>
          )}
        </View>

        {/* Pipeline stepper */}
        <PipelineStepper doneSet={doneStages} activeKey={activeStage} />

        {/* Active stage message */}
        {activeStage && !done && (
          <View style={{ paddingHorizontal: 22, marginBottom: 6 }}>
            <Text style={{ fontSize: 12, color: '#b09a73', fontStyle: 'italic' }}>
              {STAGE_MESSAGES[activeStage] || ''}
            </Text>
          </View>
        )}

        {/* Acharya header */}
        <View style={{ alignItems: 'center', paddingTop: 2, paddingBottom: 6 }}>
          <View style={{ width: 52, height: 52, marginBottom: 7 }}>
            <View style={{ position: 'absolute', top: -4, left: -4, right: -4, bottom: -4, borderRadius: 30, borderWidth: 1, borderColor: 'rgba(224,132,59,0.4)' }} />
            <Image source={acharyaPhoto} style={{ width: 52, height: 52, borderRadius: 26, borderWidth: 2, borderColor: 'rgba(232,185,107,0.55)' }} />
          </View>
          <Text style={{ fontFamily: F.serif, fontSize: 18, color: '#f6ecd6' }}>{title || 'Live Pravachanam'}</Text>
          <Text style={{ fontSize: 11, color: '#b09a73', marginTop: 2 }}>{ACHARYA} · {t('liveTag')}</Text>
        </View>

        {/* Upload status — makes it obvious the file is already in, so it isn't uploaded twice */}
        {isFileUpload && upload && (
          <View style={{ alignSelf: 'center', marginTop: 4, marginBottom: 6, paddingHorizontal: 14, paddingVertical: 7, borderRadius: 99,
                         backgroundColor: upload.status === 'error' ? 'rgba(224,80,80,0.15)' : 'rgba(127,221,127,0.10)',
                         borderWidth: 1, borderColor: upload.status === 'error' ? 'rgba(224,80,80,0.45)' : 'rgba(127,221,127,0.35)' }}>
            <Text style={{ fontSize: 12, fontFamily: F.sansSemi, color: upload.status === 'error' ? '#f0a0a0' : '#a8e6a8' }}>
              {upload.status === 'uploading' ? `⇪ Uploading ${upload.name}…`
                : upload.status === 'error' ? `⚠ Upload of ${upload.name} failed — try again`
                : upload.duplicate ? `✓ ${upload.name} is already being processed — no need to upload again`
                : `✓ Uploaded ${upload.name} — processing, no need to upload again`}
            </Text>
          </View>
        )}

        {/* Content area */}
        <ScrollView
          ref={scRef}
          onContentSizeChange={() => scRef.current?.scrollToEnd({ animated: true })}
          style={{ flex: 1 }}
          contentContainerStyle={{ paddingHorizontal: 22, paddingBottom: 12 }}
          showsVerticalScrollIndicator={false}
        >
          {lines.length === 0 && (
            <View style={{ marginTop: 30, alignItems: 'center' }}>
              <Text style={{ fontSize: 13, color: '#7d6c4c', textAlign: 'center', lineHeight: 22 }}>
                {activeStage
                  ? STAGE_MESSAGES[activeStage]
                  : '▍ Listening... content will appear as each stage completes'}
              </Text>
            </View>
          )}

          {lines.map((line, i) => (
            <View key={i} style={{ marginBottom: line.kind === 'heading' ? 6 : line.kind === 'stage_banner' ? 0 : 16 }}>
              {line.kind === 'stage_banner' ? (
                <View style={{ flexDirection: 'row', alignItems: 'center', marginVertical: 18 }}>
                  <View style={{ flex: 1, height: 1, backgroundColor: 'rgba(255,255,255,0.07)' }} />
                  <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 5, marginHorizontal: 10, borderRadius: 99, borderWidth: 1, borderColor: (line.color || C.saffron) + '55', backgroundColor: (line.color || C.saffron) + '12' }}>
                    <Text style={{ fontSize: 12, marginRight: 5 }}>{line.icon}</Text>
                    <View>
                      <Text style={{ fontSize: 9, color: line.color || C.saffron, fontFamily: F.sansSemi, letterSpacing: 1 }}>{line.step?.toUpperCase()}</Text>
                      <Text style={{ fontSize: 11, color: '#f1e6cf', fontFamily: F.sansSemi }}>{line.label}</Text>
                    </View>
                  </View>
                  <View style={{ flex: 1, height: 1, backgroundColor: 'rgba(255,255,255,0.07)' }} />
                </View>
              ) : line.kind === 'heading' ? (
                <Text style={{ fontFamily: F.serif, fontSize: 16, color: C.saffron, marginTop: i === 0 ? 0 : 10 }}>{line.te}</Text>
              ) : line.kind === 'para' ? (
                <Text style={{ fontFamily: F.telugu, fontSize: 16.5, lineHeight: 30, color: '#f1e6cf' }}>{line.te}</Text>
              ) : (
                <View style={{ marginBottom: 4, paddingLeft: 12, borderLeftWidth: 2, borderLeftColor: 'rgba(224,132,59,0.4)' }}>
                  <Text style={{ fontSize: 9, color: C.saffron, fontFamily: F.sansSemi, letterSpacing: 1, marginBottom: 3 }}>{line.ref?.toUpperCase()}</Text>
                  <Text style={{ fontFamily: F.telugu, fontSize: 15.5, lineHeight: 28, color: '#d4b483' }}>"{line.dev}"</Text>
                  {line.original ? (
                    <Text style={{ fontFamily: F.dev, fontSize: 14, lineHeight: 26, color: '#e8c97a', marginTop: 4 }}>{line.original}</Text>
                  ) : null}
                </View>
              )}
            </View>
          ))}

          {active && !done && <Text style={{ fontSize: 12, color: '#7d6c4c' }}>▍</Text>}
        </ScrollView>

        {/* Controls — hide Stop for file uploads, show it only for mic recording */}
        {!isFileUpload && (
          <View style={{ paddingHorizontal: 22, paddingBottom: insets.bottom + 18 }}>
            <View style={{ marginBottom: 18 }}><Waveform /></View>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center' }}>
              <View style={{ alignItems: 'center', marginRight: 26 }}>
                <View style={{ width: 54, height: 54, borderRadius: 27, borderWidth: 1, borderColor: 'rgba(201,167,75,0.4)', alignItems: 'center', justifyContent: 'center' }}>
                  <Text style={{ color: '#c9b78f', fontSize: 18 }}>✎</Text>
                </View>
                <Text style={{ fontSize: 10.5, color: '#9b875f', marginTop: 6 }}>{t('note')}</Text>
              </View>

              <Pressable onPress={stopRecording} disabled={saving} style={{ width: 74, height: 74, alignItems: 'center', justifyContent: 'center' }}>
                {!saving && <Pulse />}
                <LinearGradient colors={saving ? ['#4a4a4a', '#333'] : ['#e0843b', '#c25a26']} style={{ width: 74, height: 74, borderRadius: 37, alignItems: 'center', justifyContent: 'center' }}>
                  {saving
                    ? <Text style={{ fontSize: 10, color: '#fff', letterSpacing: 0.5 }}>SAVING</Text>
                    : <View style={{ width: 22, height: 22, borderRadius: 4, backgroundColor: '#fff4e2' }} />}
                </LinearGradient>
              </Pressable>

              <Pressable onPress={() => go('ask')} style={{ alignItems: 'center', marginLeft: 26 }}>
                <View style={{ width: 54, height: 54, borderRadius: 27, borderWidth: 1, borderColor: 'rgba(201,167,75,0.4)', alignItems: 'center', justifyContent: 'center' }}>
                  <Text style={{ color: '#c9b78f', fontSize: 18 }}>✦</Text>
                </View>
                <Text style={{ fontSize: 10.5, color: '#9b875f', marginTop: 6 }}>{t('ask')}</Text>
              </Pressable>
            </View>
          </View>
        )}

        {/* File upload footer — just info, no Stop button */}
        {isFileUpload && !done && (
          <View style={{ paddingHorizontal: 22, paddingBottom: insets.bottom + 18, alignItems: 'center' }}>
            <Text style={{ fontSize: 11, color: '#7d6c4c', textAlign: 'center', lineHeight: 18 }}>
              Processing automatically — no action needed.{'\n'}Results will appear as each stage completes.
            </Text>
          </View>
        )}

      </View>
    </LinearGradient>
  );
}
