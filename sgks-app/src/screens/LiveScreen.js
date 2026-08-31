import React, { useState, useRef, useEffect } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  SafeAreaView, ActivityIndicator, Alert, ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import { colors } from '../theme/colors';
import { startSession, stopSession, createWebSocket, uploadAudio } from '../services/api';

const CHUNK_SECONDS = 30;

const PIPELINE_STAGES = [
  { key: 'transcription', label: 'Transcribing Audio' },
  { key: 'correction', label: 'Correcting Transcript' },
  { key: 'shloka_detector', label: 'Detecting Shlokas' },
  { key: 'knowledge_structurer', label: 'Structuring Knowledge' },
  { key: 'notes_generator', label: 'Generating Notes' },
  { key: 'memory', label: 'Saving to Memory' },
];

export default function LiveScreen({ navigation }) {
  const [mode, setMode] = useState('youtube'); // 'youtube' | 'mic'
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState('idle'); // idle | processing | live | stopped | pipeline_running | done
  const [chunks, setChunks] = useState([]);
  const [recordingTime, setRecordingTime] = useState(0);
  const [completedAgents, setCompletedAgents] = useState([]);
  const [currentAgent, setCurrentAgent] = useState(null);
  const wsRef = useRef(null);
  const recordingRef = useRef(null);
  const timerRef = useRef(null);
  const chunkCountRef = useRef(0);

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (timerRef.current) clearInterval(timerRef.current);
      if (recordingRef.current) recordingRef.current.stopAndUnloadAsync().catch(() => {});
    };
  }, []);

  const openWebSocket = () => {
    wsRef.current = createWebSocket((data) => {
      if (data.type === 'chunk_complete') {
        setChunks(prev => [...prev, data]);
        setStatus('done');
        setCurrentAgent(null);
      } else if (data.type === 'agent_progress') {
        setCurrentAgent(data.label);
        setCompletedAgents(prev => {
          const idx = PIPELINE_STAGES.findIndex(s => s.key === data.agent);
          // mark all stages up to and including this one as done
          const done = PIPELINE_STAGES.slice(0, idx + 1).map(s => s.key);
          return done;
        });
      }
    }, () => {});
  };

  // ── YouTube mode ──────────────────────────────────────────
  const handleYouTubeStart = async () => {
    if (!url.trim()) { Alert.alert('Enter a YouTube URL'); return; }
    setStatus('processing');
    setChunks([]);
    try {
      await startSession(url.trim());
      setStatus('live');
      openWebSocket();
    } catch {
      Alert.alert('Could not connect to server. Make sure the backend is running.');
      setStatus('idle');
    }
  };

  const handleYouTubeStop = async () => {
    await stopSession();
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    setStatus('stopped');
  };

  // ── Mic mode ──────────────────────────────────────────────
  const startChunkRecording = async () => {
    const { recording } = await Audio.Recording.createAsync(
      Audio.RecordingOptionsPresets.HIGH_QUALITY
    );
    recordingRef.current = recording;

    setTimeout(() => stopAndUploadChunk(), CHUNK_SECONDS * 1000);
  };

  const stopAndUploadChunk = async () => {
    if (!recordingRef.current) return;
    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;
      chunkCountRef.current += 1;

      await uploadAudio(uri);

      // start next chunk if still recording
      if (status === 'live') {
        startChunkRecording();
      }
    } catch (e) {
      console.warn('Chunk upload error:', e);
    }
  };

  const handleMicStart = async () => {
    const { granted } = await Audio.requestPermissionsAsync();
    if (!granted) { Alert.alert('Microphone permission required'); return; }

    await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });

    setStatus('live');
    setChunks([]);
    setCompletedAgents([]);
    setCurrentAgent(null);
    chunkCountRef.current = 0;
    setRecordingTime(0);
    openWebSocket();

    startChunkRecording();

    timerRef.current = setInterval(() => {
      setRecordingTime(t => t + 1);
    }, 1000);
  };

  const handleMicStop = async () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (recordingRef.current) {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;
      if (uri) await uploadAudio(uri);
    }
    // Keep WebSocket open — pipeline is still running, we need progress updates
    setStatus('pipeline_running');
  };

  const handleStop = mode === 'youtube' ? handleYouTubeStop : handleMicStop;
  const handleStart = mode === 'youtube' ? handleYouTubeStart : handleMicStart;

  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  const AGENTS = ['Downloading Audio', 'Transcribing', 'Detecting Shlokas', 'Structuring Knowledge', 'Generating Notes', 'Saving to Memory'];

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <Text style={styles.lotusIcon}>❀</Text>
        <Text style={styles.title}>Live Session</Text>
        <Text style={styles.subtitle}>Process a YouTube pravachanam or record live from your microphone</Text>

        {/* Mode toggle */}
        {(status === 'idle' || status === 'stopped' || status === 'done') && (
          <View style={styles.modeToggle}>
            <TouchableOpacity
              style={[styles.modeBtn, mode === 'youtube' && styles.modeBtnActive]}
              onPress={() => setMode('youtube')}
            >
              <Ionicons name="logo-youtube" size={16} color={mode === 'youtube' ? '#FFF' : colors.gold} />
              <Text style={[styles.modeBtnText, mode === 'youtube' && styles.modeBtnTextActive]}>YouTube</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.modeBtn, mode === 'mic' && styles.modeBtnActive]}
              onPress={() => setMode('mic')}
            >
              <Ionicons name="mic" size={16} color={mode === 'mic' ? '#FFF' : colors.gold} />
              <Text style={[styles.modeBtnText, mode === 'mic' && styles.modeBtnTextActive]}>Live Mic</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* YouTube URL input */}
        {mode === 'youtube' && (status === 'idle' || status === 'stopped' || status === 'done') && (
          <TextInput
            style={styles.input}
            placeholder="https://www.youtube.com/watch?v=..."
            placeholderTextColor={colors.textMuted}
            value={url}
            onChangeText={setUrl}
            autoCapitalize="none"
            autoCorrect={false}
          />
        )}

        {/* Mic info */}
        {mode === 'mic' && (status === 'idle' || status === 'stopped' || status === 'done') && (
          <View style={styles.micInfo}>
            <Ionicons name="mic-circle-outline" size={48} color={colors.gold} />
            <Text style={styles.micInfoText}>Records in 30-second chunks and sends each one for AI processing</Text>
          </View>
        )}

        {/* Start button */}
        {(status === 'idle' || status === 'stopped' || status === 'done') && (
          <TouchableOpacity style={styles.startBtn} onPress={handleStart}>
            <Ionicons name={mode === 'mic' ? 'mic' : 'radio'} size={20} color="#FFF" />
            <Text style={styles.startText}>{mode === 'mic' ? 'Start Recording' : 'Start Processing'}</Text>
          </TouchableOpacity>
        )}

        {status === 'processing' && (
          <View style={styles.statusBox}>
            <ActivityIndicator color={colors.gold} />
            <Text style={styles.statusText}>Connecting...</Text>
          </View>
        )}

        {status === 'live' && (
          <View style={styles.liveBox}>
            <View style={styles.liveHeader}>
              <View style={styles.liveBadge}>
                <View style={styles.liveDot} />
                <Text style={styles.liveBadgeText}>{mode === 'mic' ? 'RECORDING' : 'LIVE'}</Text>
              </View>
              {mode === 'mic' ? (
                <Text style={styles.liveTitle}>{formatTime(recordingTime)} · chunk every 30s</Text>
              ) : (
                <Text style={styles.liveTitle}>Generating notes every 30 seconds</Text>
              )}
            </View>
            <View style={styles.agentList}>
              {AGENTS.map((agent, i) => (
                <View key={i} style={styles.agentRow}>
                  <Ionicons name="checkmark-circle" size={16} color={colors.gold} />
                  <Text style={styles.agentText}>{agent}</Text>
                </View>
              ))}
            </View>
            <TouchableOpacity style={styles.stopBtn} onPress={handleStop}>
              <Ionicons name="stop-circle-outline" size={20} color="#FFF" />
              <Text style={styles.stopText}>Stop Session</Text>
            </TouchableOpacity>
          </View>
        )}

        {(status === 'pipeline_running' || status === 'done') && (
          <View style={styles.pipelineBox}>
            <Text style={styles.pipelineTitle}>
              {status === 'done' ? '✓ Notes saved to library' : 'Recording stopped — processing...'}
            </Text>
            <View style={styles.stageList}>
              {PIPELINE_STAGES.map((stage) => {
                const done = completedAgents.includes(stage.key);
                const active = currentAgent === stage.label;
                return (
                  <View key={stage.key} style={styles.stageRow}>
                    {done ? (
                      <Ionicons name="checkmark-circle" size={18} color={colors.gold} />
                    ) : active ? (
                      <ActivityIndicator size="small" color={colors.gold} />
                    ) : (
                      <Ionicons name="ellipse-outline" size={18} color={colors.textMuted} />
                    )}
                    <Text style={[styles.stageText, done && styles.stageTextDone, active && styles.stageTextActive]}>
                      {stage.label}
                    </Text>
                  </View>
                );
              })}
            </View>
          </View>
        )}

        {/* Real-time chunks */}
        {chunks.length > 0 && (
          <View style={styles.chunksSection}>
            <Text style={styles.chunksTitle}>Live Notes ({chunks.length} chunk{chunks.length > 1 ? 's' : ''} processed)</Text>
            {[...chunks].reverse().map((chunk, i) => (
              <TouchableOpacity
                key={i}
                style={styles.chunkCard}
                onPress={() => navigation.navigate('SessionDetail', { session: chunk })}
              >
                <View style={styles.chunkHeader}>
                  <Text style={styles.chunkIndex}>Chunk {chunk.chunk_index + 1}</Text>
                  <Ionicons name="chevron-forward" size={14} color={colors.textMuted} />
                </View>
                {chunk.summary ? (
                  <Text style={styles.chunkSummary} numberOfLines={3}>{chunk.summary}</Text>
                ) : null}
                <View style={styles.chunkMetaRow}>
                  {chunk.shlokas?.length > 0 && (
                    <View style={styles.chunkMeta}>
                      <Ionicons name="text-outline" size={12} color={colors.gold} />
                      <Text style={styles.chunkMetaText}>{chunk.shlokas.length} shloka(s)</Text>
                    </View>
                  )}
                  {chunk.segments?.length > 0 && (
                    <View style={styles.chunkMeta}>
                      <Ionicons name="layers-outline" size={12} color={colors.gold} />
                      <Text style={styles.chunkMetaText}>{chunk.segments.length} segment(s)</Text>
                    </View>
                  )}
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  container: { paddingHorizontal: 24, alignItems: 'center', paddingTop: 60 },
  lotusIcon: { fontSize: 44, color: colors.gold, marginBottom: 12 },
  title: { fontSize: 24, fontWeight: '700', color: colors.text, marginBottom: 8 },
  subtitle: { fontSize: 14, color: colors.textMuted, textAlign: 'center', marginBottom: 28, lineHeight: 22 },
  modeToggle: {
    flexDirection: 'row',
    width: '100%',
    backgroundColor: 'rgba(196,144,15,0.1)',
    borderRadius: 100,
    padding: 4,
    marginBottom: 20,
  },
  modeBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    borderRadius: 100,
  },
  modeBtnActive: { backgroundColor: colors.gold },
  modeBtnText: { fontSize: 14, fontWeight: '600', color: colors.gold },
  modeBtnTextActive: { color: '#FFF' },
  input: {
    width: '100%',
    backgroundColor: colors.white,
    borderRadius: 14,
    paddingHorizontal: 18,
    paddingVertical: 16,
    fontSize: 14,
    color: colors.text,
    borderWidth: 1.5,
    borderColor: 'rgba(196,144,15,0.25)',
    marginBottom: 20,
  },
  micInfo: {
    width: '100%',
    alignItems: 'center',
    paddingVertical: 24,
    gap: 12,
    backgroundColor: 'rgba(196,144,15,0.07)',
    borderRadius: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(196,144,15,0.2)',
  },
  micInfoText: { fontSize: 13, color: colors.textMuted, textAlign: 'center', paddingHorizontal: 24, lineHeight: 20 },
  startBtn: {
    width: '100%',
    backgroundColor: colors.gold,
    borderRadius: 100,
    paddingVertical: 18,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 10,
  },
  startText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  statusBox: { marginTop: 24, alignItems: 'center', gap: 12 },
  statusText: { fontSize: 14, color: colors.textMuted },
  liveBox: {
    width: '100%',
    backgroundColor: colors.white,
    borderRadius: 20,
    padding: 20,
    marginTop: 20,
    borderWidth: 1,
    borderColor: 'rgba(196,144,15,0.2)',
    shadowColor: colors.gold,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 3,
  },
  liveHeader: { marginBottom: 20 },
  liveBadge: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: colors.liveBadge,
    alignSelf: 'flex-start',
    paddingHorizontal: 10, paddingVertical: 4,
    borderRadius: 100, marginBottom: 10, gap: 5,
  },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#FFF' },
  liveBadgeText: { color: '#FFF', fontSize: 11, fontWeight: '700' },
  liveTitle: { fontSize: 14, color: colors.text, fontWeight: '600' },
  agentList: { gap: 12, marginBottom: 20 },
  agentRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  agentText: { fontSize: 13, color: colors.text },
  stopBtn: {
    backgroundColor: colors.dark,
    borderRadius: 100, paddingVertical: 14,
    flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 8,
  },
  stopText: { color: '#FFF', fontSize: 15, fontWeight: '600' },
  pipelineBox: {
    marginTop: 20, backgroundColor: colors.white,
    borderRadius: 16, padding: 20, width: '100%',
    borderWidth: 1, borderColor: 'rgba(196,144,15,0.2)',
  },
  pipelineTitle: { fontSize: 14, fontWeight: '700', color: colors.text, marginBottom: 16, textAlign: 'center' },
  stageList: { gap: 12 },
  stageRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  stageText: { fontSize: 13, color: colors.textMuted },
  stageTextDone: { color: colors.text },
  stageTextActive: { color: colors.gold, fontWeight: '600' },
  chunksSection: { width: '100%', marginTop: 28 },
  chunksTitle: { fontSize: 15, fontWeight: '700', color: colors.text, marginBottom: 14 },
  chunkCard: {
    backgroundColor: colors.white, borderRadius: 16,
    padding: 16, marginBottom: 12,
    borderWidth: 1, borderColor: 'rgba(196,144,15,0.2)',
  },
  chunkHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  chunkIndex: { fontSize: 12, fontWeight: '700', color: colors.gold },
  chunkSummary: { fontSize: 13, color: colors.text, lineHeight: 20, marginBottom: 10 },
  chunkMetaRow: { flexDirection: 'row', gap: 14 },
  chunkMeta: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  chunkMetaText: { fontSize: 12, color: colors.textMuted },
});
