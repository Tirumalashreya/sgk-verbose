// Live — record in the hall (the waves follow the voice), or follow an upload /
// YouTube link through the pipeline.
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import * as Haptics from 'expo-haptics';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { palettes, F, T, S, R } from '../theme';
import { Button, IconButton, Chip, StagePath, Overline, Enter, Portrait } from '../ui/kit';
import Waveform from '../ui/Waveform';
import Kolam from '../ui/Kolam';
import Icon from '../ui/Icon';
import { createWebSocket, startLive, stopSession, uploadAudio, cancelUpload, startSession, getSessions } from '../services/api';
import { useMinuteRecorder } from '../services/useMinuteRecorder';
import { notify, choose, confirm, isWeb } from '../services/platform';

const c = palettes.manuscript;
const STAGES = ['transcription', 'correction', 'shloka_detector', 'knowledge_structurer', 'formatting', 'validation', 'memory'];
const isTe = (s) => /[ఀ-౿]/.test(s || '');
const CONTINUE_WINDOW_MS = 15 * 60 * 1000;   // pressing Record soon after Stop offers to continue
const utc = (iso) => Date.parse(/Z|[+-]\d\d:\d\d$/.test(iso || '') ? iso : `${iso}Z`);
const fmt = (ms) => { const s = Math.floor(ms / 1000); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
const fmtHMS = (ms) => {
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
};
const audioType = (uri) => (isWeb || /\.webm/i.test(uri) ? 'audio/webm' : /\.(m4a|mp4|aac)/i.test(uri) ? 'audio/mp4' : /\.wav/i.test(uri) ? 'audio/wav' : 'audio/mpeg');

export default function LiveScreen({ go, back, t, upload, setUpload, pendingUpload, clearPendingUpload, pendingLink, clearPendingLink }) {
  const insets = useSafeAreaInsets();
  // mode: idle | recording | saving | processing | error
  const [mode, setMode] = useState(upload && ['uploading', 'processing'].includes(upload.status) ? 'processing' : 'idle');
  const [title, setTitle] = useState(upload?.name?.replace(/\.[^.]+$/, '') || '');
  const [done, setDone] = useState(new Set());
  const [active, setActive] = useState('transcription');
  const [preview, setPreview] = useState([]);
  const [error, setError] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const [silentWarning, setSilentWarning] = useState(false);
  const silenceTimer = useRef(null);
  const pieces = useRef(0);
  const startedAt = useRef(0);
  const pausedAt = useRef(0);
  const modeRef = useRef(mode);
  modeRef.current = mode;
  const liveSessionId = useRef(null);   // identifies *this* recording on the server, not just this login —
                                        // the same shared username can be recording on another phone at once

  const recorder = useMinuteRecorder(async (uri) => {
    const n = pieces.current++;
    const ext = (uri.match(/\.(\w+)(\?|$)/) || [])[1] || (isWeb ? 'webm' : 'm4a');
    try { await uploadAudio({ uri, name: `minute-${n + 1}.${ext}`, type: audioType(uri) }, { live: true, liveSessionId: liveSessionId.current }); }
    catch (e) { console.warn('[live] minute upload failed', e); }
  });

  useEffect(() => {
    if (mode !== 'recording') return undefined;
    const id = setInterval(() => setElapsed(Date.now() - startedAt.current), 1000);
    return () => clearInterval(id);
  }, [mode]);

  useEffect(() => {
    if (mode !== 'recording') {
      if (silenceTimer.current) {
        clearTimeout(silenceTimer.current);
        silenceTimer.current = null;
      }
      setSilentWarning(false);
      return;
    }

    if (recorder.level >= 0.02) {
      if (silenceTimer.current) {
        clearTimeout(silenceTimer.current);
        silenceTimer.current = null;
      }
      setSilentWarning(false);
    } else if (!silenceTimer.current && !silentWarning) {
      silenceTimer.current = setTimeout(() => {
        setSilentWarning(true);
        silenceTimer.current = null;
      }, 4000);
    }
  }, [mode, recorder.level, silentWarning]);

  useEffect(() => {
    return () => {
      if (silenceTimer.current) clearTimeout(silenceTimer.current);
    };
  }, []);

  // ── pipeline events ─────────────────────────────────────────────────────
  const onMessage = (data) => {
    const m = modeRef.current;
    if (data.type === 'agent_progress' && m === 'processing') {
      const i = STAGES.indexOf(data.agent);
      if (i >= 0) {
        setDone((prev) => new Set([...prev, ...STAGES.slice(0, i + 1)]));
        setActive(STAGES[i + 1] || null);
      }
    } else if (data.type === 'chunk_complete') {
      if (m === 'recording' && data.transcript) setPreview((p) => [...p, data.transcript].slice(-6));
      else if (m === 'processing' && data.id) finish(data);          // finished upload / YouTube session
    } else if (data.type === 'session_complete' && m === 'saving') {
      if (data.session) finish(data.session);
      else openSession(data.session_id);
    } else if (data.type === 'pipeline_error' && (m === 'processing' || m === 'saving')) {
      setError(data.message || ''); setMode('error');
      setUpload?.((u) => (u ? { ...u, status: 'error', message: data.message } : u));
    }
  };
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  useEffect(() => {
    let ws, cancelled = false;
    createWebSocket((d) => onMessageRef.current(d)).then((socket) => {
      if (cancelled) { socket.close(); return; }   // unmounted before the auth token lookup finished
      ws = socket;
    });
    return () => { cancelled = true; ws?.close(); };
  }, []);

  const finish = (session) => {
    setDone(new Set(STAGES)); setActive(null);
    setUpload?.(null);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    setTimeout(() => go('reading', { session }), 700);
  };

  const openSession = async (id, retries = 3) => {
    try {
      const list = (await getSessions()).sessions || [];
      const s = list.find((x) => x.id === id);
      if (s) return finish(s);
    } catch {}
    if (retries > 0) {
      setTimeout(() => openSession(id, retries - 1), 1000);
      return;
    }
    go('history');
  };

  // ── a file or YouTube link handed over from Home ────────────────────────
  useEffect(() => {
    if (pendingUpload) { const f = pendingUpload; clearPendingUpload?.(); runUpload(f); }
    else if (pendingLink) { const url = pendingLink; clearPendingLink?.(); runLink(url); }
  }, [pendingUpload, pendingLink]);

  const runUpload = async (f) => {
    if (upload && ['uploading', 'processing'].includes(upload.status)) return;   // one at a time
    setTitle(f.name.replace(/\.[^.]+$/, '')); setDone(new Set()); setActive('transcription'); setError('');
    setMode('processing');
    const at = Date.now();
    setUpload?.({ name: f.name, status: 'uploading', startedAt: at });
    try {
      const res = await uploadAudio(f);
      setUpload?.({ name: f.name, status: 'processing', startedAt: at, duplicate: res.status === 'duplicate', digest: res.digest });
    } catch (e) {
      const msg = String(e.message || e);
      setUpload?.({ name: f.name, status: 'error', startedAt: at, message: msg });
      setError(msg); setMode('error');
    }
  };

  const discardUpload = async () => {
    if (!upload?.digest) return;
    const ok = await confirm(t('discardUpload'), t('discardUploadHint'), t('discard'));
    if (!ok) return;
    try { await cancelUpload(upload.digest); } catch (e) { console.warn('[live] cancel failed', e); }
    setUpload?.(null);
    setMode('idle');
    setDone(new Set()); setActive('transcription'); setError('');
  };

  const runLink = async (url) => {
    setTitle('YouTube'); setDone(new Set()); setActive('transcription'); setError('');
    setMode('processing');
    try { await startSession(url); } catch (e) { setError(String(e.message || e)); setMode('error'); }
  };

  // ── mic recording ───────────────────────────────────────────────────────
  const startRecording = async () => {
    try {
      pieces.current = 0; setPreview([]); setError('');
      // A recording stopped a few minutes ago is probably the same pravachanam
      let continueId = null;
      const last = ((await getSessions().catch(() => ({}))).sessions || [])
        .filter((s) => (s.live || s.pieces_recorded) && Date.now() - utc(s.stopped_at || s.created_at) < CONTINUE_WINDOW_MS)
        .pop();
      if (last && await choose(t('continueTitle'), t('continueHint')(last.title), t('continueYes'), t('continueNo'))) continueId = last.id;
      const started = await startLive(continueId);
      liveSessionId.current = started?.id || null;
      await recorder.start();
      startedAt.current = Date.now(); setElapsed(0);
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
      setTitle(t('liveIdleTitle'));
      setMode('recording');
    } catch (e) {
      if (String(e.message) === 'mic-denied') notify(t('liveIdleTitle'), t('micDenied'));
      else { setError(String(e.message || e)); setMode('error'); }
    }
  };

  const stopRecording = async () => {
    setMode('saving');
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    await recorder.stop();             // resolves after the last minute is uploaded
    await stopSession(liveSessionId.current);   // the server then rebuilds the notes once, over everything
    liveSessionId.current = null;
  };

  const pauseRecording = () => {
    recorder.pause();
    pausedAt.current = Date.now();
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    setMode('paused');
  };

  const resumeRecording = () => {
    startedAt.current += Date.now() - pausedAt.current;   // keep elapsed frozen across the pause
    recorder.resume();
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    setMode('recording');
  };

  const recording = mode === 'recording';
  const paused = mode === 'paused';
  const busy = mode === 'processing' || mode === 'saving';
  const level = recording ? recorder.level : busy ? 0.5 : 0.08;
  const banner = upload && mode === 'processing'
    ? (upload.status === 'uploading' ? `${upload.name}…` : `${t('uploaded')} · ${t('noNeedAgain')}`)
    : null;
  const heading = mode === 'idle' ? t('liveIdleTitle') : title;

  return (
    <View style={{ flex: 1, backgroundColor: c.bg }}>
      <Kolam color={c.kolam} />
      <View style={[st.top, { paddingTop: insets.top + S.s }]}>
        <IconButton c={c} icon="back" label={t('back')} onPress={() => back() || go('home')} />
        <View style={{ flex: 1, alignItems: 'center' }}>
          {recording && <Chip c={c} tone="live" big>{`${t('recording')} · ${fmt(elapsed)}`}</Chip>}
          {paused && <Chip c={c} tone="review" big>{`${t('paused')} · ${fmt(elapsed)}`}</Chip>}
          {busy && <Chip c={c} tone="live" big>{mode === 'saving' ? t('stopSaving') : t('processing')}</Chip>}
        </View>
        <View style={{ width: 44 }} />
      </View>

      <View style={st.center}>
        <Portrait c={c} size={120} />
        {(recording || paused) && (
          <Text style={[st.bigTimer, { color: paused ? c.review : c.ink }]}>{fmtHMS(elapsed)}</Text>
        )}
        <View style={{ marginTop: S.x3 }}>
          <Waveform color={c.brassBright} accent={c.kumkum} bars={32} height={72} level={level} />
        </View>
        {silentWarning && recording && (
          <View style={{ marginTop: S.m, flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: 'rgba(168, 50, 47, 0.08)', borderWidth: 1, borderColor: c.kumkumText, borderRadius: R.control, paddingVertical: 6, paddingHorizontal: S.m }}>
            <Icon name="alert" size={16} color={c.kumkumText} strokeWidth={2} />
            <Text style={[T.label, { color: c.kumkumText, fontSize: 13 }, isTe(t('micSilenceWarning')) && { fontFamily: F.readMed }]}>
              {t('micSilenceWarning')}
            </Text>
          </View>
        )}
        <Enter delay={60} style={{ alignItems: 'center', marginTop: S.l, paddingHorizontal: S.xl }}>
          <Text style={[isTe(heading) ? T.displayTe : T.display, { color: c.ink, textAlign: 'center' }]} numberOfLines={2}>{heading}</Text>
          {mode === 'idle' && (
            <Text style={[isTe(t('liveIdleHint')) ? { fontFamily: F.read, fontSize: 14.5, lineHeight: 25 } : T.body, { color: c.inkSoft, textAlign: 'center', marginTop: S.s, maxWidth: 360 }]}>
              {t('liveIdleHint')}
            </Text>
          )}
          {!!banner && <View style={{ marginTop: S.m }}><Chip c={c} tone="ok" icon="check">{banner}</Chip></View>}
          {mode === 'error' && (
            <View style={[st.error, { borderColor: c.kumkumText }]}>
              <Text style={[T.label, { color: c.kumkumText }]}>{t('uploadFailed')}</Text>
              {!!error && <Text style={[T.body, { color: c.inkSoft, marginTop: 4 }]}>{error}</Text>}
            </View>
          )}
        </Enter>
      </View>

      {busy && <View style={st.stages}><StagePath c={c} stages={STAGES} labels={t('stages')} done={done} active={active} /></View>}
      {mode === 'processing' && !!upload?.digest && (
        <View style={{ alignItems: 'center', marginTop: S.l }}>
          <Button c={c} label={t('discardUpload')} variant="quiet" onPress={discardUpload} />
        </View>
      )}

      {(recording || paused) && preview.length > 0 && (
        <ScrollView style={st.preview} contentContainerStyle={{ padding: S.l, gap: S.s }}>
          <Overline c={c}>{t('listening')}</Overline>
          {preview.map((p, i) => (
            <Text key={i} numberOfLines={4} style={[T.read, { color: i === preview.length - 1 ? c.ink : c.muted, fontSize: 15.5, lineHeight: 28 }]}>{p}</Text>
          ))}
        </ScrollView>
      )}

      <View style={[st.controls, { paddingBottom: insets.bottom + S.xl }]}>
        {(mode === 'idle' || mode === 'error') && <Button c={c} icon="mic" label={t('record')} onPress={startRecording} style={{ minWidth: 240 }} />}
        {(recording || paused) && (
          <View style={{ flexDirection: 'row', gap: S.m }}>
            {recording
              ? <Button c={c} variant="quiet" icon="pause" label={t('pause')} onPress={pauseRecording} style={{ minWidth: 150 }} />
              : <Button c={c} variant="quiet" icon="play" label={t('resume')} onPress={resumeRecording} style={{ minWidth: 150 }} />}
            <Button c={c} icon="stop" label={t('stop')} onPress={stopRecording} style={{ minWidth: 150 }} />
          </View>
        )}
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.s },
  bigTimer: { fontFamily: F.uiBold, fontSize: 48, letterSpacing: 2, marginTop: S.m, fontVariant: ['tabular-nums'] },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  stages: { width: '100%', maxWidth: 560, alignSelf: 'center', paddingHorizontal: S.l, paddingBottom: S.xl },
  preview: { maxHeight: 190, marginHorizontal: S.l, borderRadius: R.panel, backgroundColor: 'rgba(252,248,240,0.92)', borderWidth: 1, borderColor: palettes.manuscript.line },
  controls: { alignItems: 'center', paddingTop: S.l },
  error: { marginTop: S.l, borderWidth: 1, borderRadius: R.control, padding: S.m, maxWidth: 420 },
});
