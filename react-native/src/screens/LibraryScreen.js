import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, Pressable, TextInput, Modal, ActivityIndicator } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { C, F } from '../theme';
import { startSession, getSessions, startLive, uploadAudio } from '../services/api';

function Divider() {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', marginVertical: 22, paddingHorizontal: 4 }}>
      <LinearGradient colors={['rgba(216,195,147,0)', '#d8c393']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={{ flex: 1, height: 1 }} />
      <View style={{ width: 7, height: 7, backgroundColor: C.gold, marginHorizontal: 12, transform: [{ rotate: '45deg' }] }} />
      <LinearGradient colors={['#d8c393', 'rgba(216,195,147,0)']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={{ flex: 1, height: 1 }} />
    </View>
  );
}

function LangToggle({ lang, setLang }) {
  const Opt = ({ code, label }) => {
    const active = lang === code;
    return (
      <Pressable onPress={() => setLang(code)} style={{ paddingHorizontal: 11, paddingVertical: 5, borderRadius: 99, backgroundColor: active ? C.maroon : 'transparent' }}>
        <Text style={{ fontFamily: F.sansSemi, fontSize: 12, color: active ? C.cream : C.muted }}>{label}</Text>
      </Pressable>
    );
  };
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', padding: 3, borderRadius: 99, backgroundColor: C.card, borderWidth: 1, borderColor: C.line }}>
      <Opt code="en" label="EN" />
      <Opt code="te" label="తె" />
    </View>
  );
}

export default function LibraryScreen({ go, t, lang, setLang }) {
  const [showPaste, setShowPaste] = useState(false);
  const [url, setUrl]             = useState('');
  const [loading, setLoading]     = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sessions, setSessions]   = useState([]);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const data = await getSessions();
      setSessions(data.sessions || []);
    } catch {}
  };

  const handleUploadAudio = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'audio/*,video/webm';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      setUploading(true);
      try {
        await startLive();
        await uploadAudio(file);
        go('live');
      } catch (err) {
        console.error('Upload failed:', err);
      } finally {
        setUploading(false);
      }
    };
    input.click();
  };

  const handleStartSession = async () => {
    if (!url.trim()) return;
    setLoading(true);
    try {
      const pastedUrl = url.trim();
      await startSession(pastedUrl);
      setShowPaste(false);
      setUrl('');
      go('live', { url: pastedUrl });
    } catch (e) {
      console.error('Failed to start session:', e);
      setProcessing(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: C.paper }}
      contentContainerStyle={{ paddingTop: 20, paddingHorizontal: 22, paddingBottom: 60 }}
      showsVerticalScrollIndicator={false}
    >
      {/* Lang toggle */}
      <View style={{ flexDirection: 'row', justifyContent: 'flex-end', marginBottom: 20 }}>
        <LangToggle lang={lang} setLang={setLang} />
      </View>

      {/* URL paste modal */}
      <Modal visible={showPaste} transparent animationType="fade">
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 24 }}>
          <View style={{ backgroundColor: C.paper, borderRadius: 20, padding: 24 }}>
            <Text style={{ fontFamily: F.serif, fontSize: 18, color: C.ink, marginBottom: 6 }}>{t('pasteTitle')}</Text>
            <Text style={{ fontSize: 13, color: C.muted, marginBottom: 16 }}>{t('pasteSub')}</Text>
            <TextInput
              value={url}
              onChangeText={setUrl}
              placeholder="https://youtube.com/..."
              placeholderTextColor={C.muted}
              autoFocus
              style={{ borderWidth: 1, borderColor: C.line, borderRadius: 12, padding: 12, fontSize: 14, color: C.ink, backgroundColor: C.card }}
            />
            <View style={{ flexDirection: 'row', gap: 10, marginTop: 16 }}>
              <Pressable onPress={() => { setShowPaste(false); setUrl(''); }} style={{ flex: 1, padding: 14, borderRadius: 12, borderWidth: 1, borderColor: C.line, alignItems: 'center' }}>
                <Text style={{ fontSize: 14, color: C.muted }}>Cancel</Text>
              </Pressable>
              <Pressable onPress={handleStartSession} style={{ flex: 1, padding: 14, borderRadius: 12, backgroundColor: C.maroon, alignItems: 'center' }}>
                {loading
                  ? <ActivityIndicator color="#fff" />
                  : <Text style={{ fontSize: 14, color: '#fff', fontFamily: F.sansSemi }}>Start</Text>}
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>

      {/* Actions */}
      <Text style={{ fontFamily: F.serif, fontSize: 15, color: C.maroon, marginBottom: 12, marginLeft: 2 }}>{t('transcribeTitle')}</Text>
      <View style={{ flexDirection: 'row' }}>
        <Pressable onPress={() => setShowPaste(true)} style={{ flex: 1, borderWidth: 1, borderColor: C.line, borderRadius: 18, padding: 16, backgroundColor: C.card, marginRight: 12 }}>
          <View style={{ width: 38, height: 38, borderRadius: 12, backgroundColor: '#f1e6cf', alignItems: 'center', justifyContent: 'center' }}>
            <Text style={{ fontSize: 18 }}>🔗</Text>
          </View>
          <Text style={{ fontFamily: F.sansSemi, fontSize: 14, color: C.ink, marginTop: 10 }}>{t('pasteTitle')}</Text>
          <Text style={{ fontSize: 11.5, color: C.muted, marginTop: 3, lineHeight: 16 }}>{t('pasteSub')}</Text>
        </Pressable>
        <Pressable onPress={() => go('live')} style={{ flex: 1, borderRadius: 18, overflow: 'hidden' }}>
          <LinearGradient colors={['#e0843b', '#c25a26']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={{ flex: 1, padding: 16 }}>
            <View style={{ width: 38, height: 38, borderRadius: 12, backgroundColor: 'rgba(255,244,226,0.25)', alignItems: 'center', justifyContent: 'center' }}>
              <View style={{ width: 14, height: 14, borderRadius: 7, backgroundColor: '#fff4e2' }} />
            </View>
            <Text style={{ fontFamily: F.sansSemi, fontSize: 14, color: '#fff7ec', marginTop: 10 }}>{t('recordTitle')}</Text>
            <Text style={{ fontSize: 11.5, color: '#ffe6cc', marginTop: 3, lineHeight: 16 }}>{t('recordSub')}</Text>
          </LinearGradient>
        </Pressable>
      </View>

      {/* Upload audio button */}
      <Pressable onPress={handleUploadAudio} style={{ marginTop: 12, borderWidth: 1, borderColor: C.line, borderRadius: 18, padding: 16, backgroundColor: C.card, flexDirection: 'row', alignItems: 'center' }}>
        <View style={{ width: 38, height: 38, borderRadius: 12, backgroundColor: '#f1e6cf', alignItems: 'center', justifyContent: 'center', marginRight: 14 }}>
          <Text style={{ fontSize: 18 }}>🎵</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={{ fontFamily: F.sansSemi, fontSize: 14, color: C.ink }}>Upload audio file</Text>
          <Text style={{ fontSize: 11.5, color: C.muted, marginTop: 3 }}>MP3, WAV, M4A, WebM → Telugu notes</Text>
        </View>
        {uploading
          ? <ActivityIndicator color={C.maroon} size="small" />
          : <Text style={{ fontSize: 18, color: C.gold }}>›</Text>}
      </Pressable>

      {/* Recent sessions */}
      {sessions.length > 0 && (
        <>
          <Divider />
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <Text style={{ fontFamily: F.serif, fontSize: 15, color: C.maroon }}>{t('recent')}</Text>
            <Pressable onPress={() => go('history')}>
              <Text style={{ fontSize: 12, color: C.gold, fontFamily: F.sansSemi }}>View all ›</Text>
            </Pressable>
          </View>
          {sessions.filter(s => s.notes || s.transcript).slice().reverse().slice(0, 3).map((session, i) => (
            <Pressable
              key={i}
              onPress={() => go('discourse', { session })}
              style={{ flexDirection: 'row', alignItems: 'center', padding: 13, borderRadius: 16, backgroundColor: C.card, borderWidth: 1, borderColor: C.lineSoft, marginBottom: 10 }}
            >
              <LinearGradient colors={['#efe0c0', '#e4cf9f']} style={{ width: 50, height: 50, borderRadius: 13, alignItems: 'center', justifyContent: 'center' }}>
                <Text style={{ fontSize: 22 }}>🪷</Text>
              </LinearGradient>
              <View style={{ flex: 1, marginLeft: 14 }}>
                <Text style={{ fontFamily: F.serif, fontSize: 16, color: C.ink }} numberOfLines={1}>
                  {session.title || `Pravachanam ${i + 1}`}
                </Text>
                <Text style={{ fontSize: 12, color: C.muted, marginTop: 3 }} numberOfLines={1}>
                  {session.summary?.slice(0, 60) || 'Processing...'}
                </Text>
                {session.created_at && (
                  <Text style={{ fontSize: 11, color: C.gold, marginTop: 2 }}>
                    {new Date(session.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </Text>
                )}
              </View>
              <Text style={{ fontSize: 18, color: C.gold }}>›</Text>
            </Pressable>
          ))}
        </>
      )}

      {sessions.length === 0 && (
        <View style={{ alignItems: 'center', marginTop: 48 }}>
          <Text style={{ fontSize: 32, marginBottom: 12 }}>🪷</Text>
          <Text style={{ fontFamily: F.serif, fontSize: 16, color: C.muted, textAlign: 'center' }}>
            No pravachanams yet.{'\n'}Paste a link or record live to begin.
          </Text>
        </View>
      )}
    </ScrollView>
  );
}
