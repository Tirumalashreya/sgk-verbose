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
import { createWebSocket, startLive, stopSession, uploadAudio, startSession, getSessions } from '../services/api';
import { useMinuteRecorder } from '../services/useMinuteRecorder';
import { notify, choose, isWeb } from '../services/platform';

const c = palettes.manuscript;
const STAGES = ['transcription', 'correction', 'shloka_detector', 'knowledge_structurer', 'formatting', 'validation', 'memory'];
const isTe = (s) => /[ఀ-౿]/.test(s || '');
const CONTINUE_WINDOW_MS = 15 * 60 * 1000;   // pressing Record soon after Stop offers to continue
const utc = (iso) => Date.parse(/Z|[+-]\d\d:\d\d$/.test(iso || '') ? iso : `${iso}Z`);
const fmt = (ms) => { const s = Math.floor(ms / 1000); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
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
  const pieces = useRef(0);
  const startedAt = useRef(0);
  const modeRef = useRef(mode);
  modeRef.current = mode;

  const recorder = useMinuteRecorder(async (uri) => {
    const n = pieces.current++;
    const ext = (uri.match(/\.(\w+)(\?|$)/) || [])[1] || (isWeb ? 'webm' : 'm4a');
    try { await uploadAudio({ uri, name: `minute-${n + 1}.${ext}`, type: audioType(uri) }, { live: true }); }
    catch (e) { console.warn('[live] minute upload failed', e); }
  });

  useEffect(() => {
    if (mode !== 'recording') return undefined;
    const id = setInterval(() => setElapsed(Date.now() - startedAt.current), 1000);
    return () => clearInterval(id);
  }, [mode]);

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
      openSession(data.session_id);
    } else if (data.type === 'pipeline_error' && (m === 'processing' || m === 'saving')) {
      setError(data.message || ''); setMode('error');
      setUpload?.((u) => (u ? { ...u, status: 'error', message: data.message } : u));
    }
  };
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  useEffect(() => {
    const ws = createWebSocket((d) => onMessageRef.current(d));
    return () => ws.close();
  }, []);

  const finish = (session) => {
    setDone(new Set(STAGES)); setActive(null);
    setUpload?.(null);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    setTimeout(() => go('reading', { session }), 700);
  };

  const openSession = async (id) => {
    try {
      const list = (await getSessions()).sessions || [];
      const s = list.find((x) => x.id === id);
      if (s) return finish(s);
    } catch {}
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
      setUpload?.({ name: f.name, status: 'processing', startedAt: at, duplicate: res.status === 'duplicate' });
    } catch (e) {
      const msg = String(e.message || e);
      setUpload?.({ name: f.name, status: 'error', startedAt: at, message: msg });
      setError(msg); setMode('error');
    }
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
      await startLive(continueId);
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
    await stopSession();               // the server then rebuilds the notes once, over everything
  };

  const recording = mode === 'recording';
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
        {recording && <Chip c={c} tone="live">{`${t('recording')} · ${fmt(elapsed)}`}</Chip>}
        {busy && <Chip c={c} tone="live">{mode === 'saving' ? t('stopSaving') : t('processing')}</Chip>}
        <View style={{ width: 44 }} />
      </View>

      <View style={st.center}>
        <Portrait c={c} size={120} />
        <View style={{ marginTop: S.x3 }}>
          <Waveform color={c.brassBright} accent={c.kumkum} bars={32} height={72} level={level} />
        </View>
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

      {recording && preview.length > 0 && (
        <ScrollView style={st.preview} contentContainerStyle={{ padding: S.l, gap: S.s }}>
          <Overline c={c}>{t('listening')}</Overline>
          {preview.map((p, i) => (
            <Text key={i} numberOfLines={4} style={[T.read, { color: i === preview.length - 1 ? c.ink : c.muted, fontSize: 15.5, lineHeight: 28 }]}>{p}</Text>
          ))}
        </ScrollView>
      )}

      <View style={[st.controls, { paddingBottom: insets.bottom + S.xl }]}>
        {(mode === 'idle' || mode === 'error') && <Button c={c} icon="mic" label={t('record')} onPress={startRecording} style={{ minWidth: 240 }} />}
        {recording && <Button c={c} icon="stop" label={t('stop')} onPress={stopRecording} style={{ minWidth: 240 }} />}
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: S.s },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  stages: { width: '100%', maxWidth: 560, alignSelf: 'center', paddingHorizontal: S.l, paddingBottom: S.xl },
  preview: { maxHeight: 190, marginHorizontal: S.l, borderRadius: R.panel, backgroundColor: 'rgba(252,248,240,0.92)', borderWidth: 1, borderColor: palettes.manuscript.line },
  controls: { alignItems: 'center', paddingTop: S.l },
  error: { marginTop: S.l, borderWidth: 1, borderRadius: R.control, padding: S.m, maxWidth: 420 },
});
