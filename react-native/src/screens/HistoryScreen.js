import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, Pressable, ActivityIndicator, Alert } from 'react-native';
import { C, F } from '../theme';
import { getSessions, deleteSession } from '../services/api';

export default function HistoryScreen({ go, lang }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadSessions = () => {
    getSessions()
      .then(data => setSessions(
        (data.sessions || [])
          .filter(s => s.notes || s.transcript)
          .slice().reverse()
      ))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadSessions(); }, []);

  const handleDelete = (session, e) => {
    e.stopPropagation();
    const id = session.id;
    if (!id) return;
    if (typeof window !== 'undefined') {
      if (!window.confirm('Delete this recording?')) return;
      deleteSession(id).then(loadSessions).catch(() => {});
    } else {
      Alert.alert('Delete', 'Delete this recording?', [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Delete', style: 'destructive', onPress: () => deleteSession(id).then(loadSessions).catch(() => {}) },
      ]);
    }
  };

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: C.paper, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color={C.maroon} />
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: C.paper }}
      contentContainerStyle={{ padding: 22, paddingBottom: 100 }}
      showsVerticalScrollIndicator={false}
    >
      <Text style={{ fontFamily: F.serif, fontSize: 26, color: C.ink, marginBottom: 4 }}>History</Text>
      <Text style={{ fontSize: 13, color: C.muted, marginBottom: 24 }}>
        {sessions.length} pravachanam{sessions.length !== 1 ? 's' : ''} recorded
      </Text>

      {sessions.length === 0 && (
        <View style={{ alignItems: 'center', marginTop: 60 }}>
          <Text style={{ fontSize: 36, marginBottom: 14 }}>🪷</Text>
          <Text style={{ fontFamily: F.serif, fontSize: 16, color: C.muted, textAlign: 'center' }}>
            No recordings yet.{'\n'}Paste a link or record live to begin.
          </Text>
          <Pressable
            onPress={() => go('library')}
            style={{ marginTop: 24, paddingHorizontal: 24, paddingVertical: 12, borderRadius: 99, backgroundColor: C.maroon }}
          >
            <Text style={{ color: '#fff', fontFamily: F.sansSemi, fontSize: 14 }}>Go to Home</Text>
          </Pressable>
        </View>
      )}

      {sessions.map((session, i) => (
        <Pressable
          key={i}
          onPress={() => go('discourse', { session })}
          style={{
            borderRadius: 18, backgroundColor: C.card,
            borderWidth: 1, borderColor: C.lineSoft,
            padding: 18, marginBottom: 14,
          }}
        >
          {/* Title row */}
          <View style={{ flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' }}>
            <View style={{ flex: 1, marginRight: 10 }}>
              <Text style={{ fontFamily: F.serif, fontSize: 17, color: C.ink }} numberOfLines={2}>
                {session.title || `Pravachanam ${sessions.length - i}`}
              </Text>
              {session.created_at && (
                <Text style={{ fontSize: 11, color: C.gold, marginTop: 3 }}>
                  {new Date(session.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                </Text>
              )}
            </View>
            <View style={{ alignItems: 'flex-end', gap: 6 }}>
              <Text style={{ fontSize: 11, color: C.gold, fontFamily: F.sansSemi }}>
                {(session.shlokas || []).length} shlokas
              </Text>
              <Text style={{ fontSize: 10, color: C.faint }}>
                {(session.segments || []).length} segments
              </Text>
              <Pressable
                onPress={(e) => handleDelete(session, e)}
                style={{ marginTop: 2, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8, backgroundColor: 'rgba(180,30,30,0.08)', borderWidth: 1, borderColor: 'rgba(180,30,30,0.18)' }}
              >
                <Text style={{ fontSize: 11, color: '#b01e1e', fontFamily: F.sansSemi }}>Delete</Text>
              </Pressable>
            </View>
          </View>

          {/* Summary */}
          {session.summary ? (
            <Text style={{ fontSize: 13, color: C.inkSoft, lineHeight: 20, marginTop: 10 }} numberOfLines={2}>
              {session.summary}
            </Text>
          ) : null}

          {/* Tags */}
          <View style={{ flexDirection: 'row', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
            {(session.segments || [])
              .map(s => s.label)
              .filter((v, idx, a) => a.indexOf(v) === idx)
              .map((label, j) => (
                <View key={j} style={{ paddingHorizontal: 10, paddingVertical: 3, borderRadius: 99, backgroundColor: 'rgba(122,46,37,0.08)', borderWidth: 1, borderColor: 'rgba(122,46,37,0.15)' }}>
                  <Text style={{ fontSize: 11, color: C.maroon, fontFamily: F.sansSemi }}>{label}</Text>
                </View>
              ))}
          </View>

          {/* Open arrow */}
          <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 14, gap: 6 }}>
            <Text style={{ fontSize: 12, color: C.saffron, fontFamily: F.sansSemi }}>View Transcript & Notes</Text>
            <Text style={{ color: C.saffron, fontSize: 14 }}>›</Text>
          </View>
        </Pressable>
      ))}
    </ScrollView>
  );
}
