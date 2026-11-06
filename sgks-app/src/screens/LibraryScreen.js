import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Dimensions, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '../theme/colors';
import VaishnavaBg from '../components/VaishnavaBg';
import LabelChip from '../components/LabelChip';
import { getSessions } from '../services/api';

const { width } = Dimensions.get('window');

const FILTERS = ['All'];

const SYMBOLS = ['🪷', 'ॐ', '☸', '❀'];

export default function LibraryScreen({ navigation }) {
  const [activeFilter, setActiveFilter] = useState('All');
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  const refreshSessions = async () => {
    setLoading(true);
    try {
      const data = await getSessions();
      setSessions((data.sessions || []).reverse());
    } catch {
      setSessions([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    refreshSessions();
    const unsubscribe = navigation.addListener('focus', refreshSessions);
    return unsubscribe;
  }, [navigation]);

  const filtered = sessions;

  return (
    <VaishnavaBg>
      <SafeAreaView style={{ flex: 1 }}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>
            <Text style={styles.lotusSmall}>❀ </Text>
            Library
          </Text>
          <TouchableOpacity style={styles.sortBtn}>
            <Ionicons name="options-outline" size={20} color={colors.gold} />
          </TouchableOpacity>
        </View>

        {/* Session count */}
        <Text style={styles.countText}>{loading ? 'Loading...' : `${filtered.length} sessions`}</Text>

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.list}>
          {loading ? (
            <ActivityIndicator color={colors.gold} style={{ marginTop: 40 }} />
          ) : filtered.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyOm}>ॐ</Text>
              <Text style={styles.emptyText}>No sessions yet.</Text>
              <Text style={styles.emptySubtext}>Start a live session to see notes here.</Text>
            </View>
          ) : (
            filtered.map((session, idx) => (
              <TouchableOpacity
                key={session.id || `session-${idx}`}
                onPress={() => navigation.navigate('SessionDetail', { session })}
              >
                <LinearGradient
                  colors={['rgba(255,255,255,0.92)', 'rgba(255,255,255,0.75)']}
                  style={styles.sessionCard}
                >
                  <View style={styles.symbolBox}>
                    <Text style={styles.symbolText}>{SYMBOLS[idx % SYMBOLS.length]}</Text>
                  </View>

                  <View style={styles.cardBody}>
                    <View style={styles.titleRow}>
                      <Text style={styles.sessionTitle} numberOfLines={1}>
                        {session.title || `Chunk ${session.chunk_index + 1}`}
                      </Text>
                    </View>

                    <Text style={styles.sessionMeta}>
                      {session.shlokas?.length || 0} shlokas · {session.segments?.length || 0} segments
                    </Text>

                    <View style={styles.bottomRow}>
                      <LabelChip label={session.segments?.[0]?.label || 'teaching'} />
                    </View>
                  </View>

                  <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
                </LinearGradient>
              </TouchableOpacity>
            ))
          )}
          <View style={{ height: 100 }} />
        </ScrollView>
      </SafeAreaView>
    </VaishnavaBg>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  headerTitle: { fontSize: 20, fontWeight: '700', color: colors.text },
  lotusSmall: { fontSize: 18, color: colors.gold },
  sortBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: 'rgba(212,160,23,0.12)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(212,160,23,0.3)',
  },
  filterRow: {
    paddingHorizontal: 20,
    paddingBottom: 14,
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 100,
    backgroundColor: 'rgba(196,144,15,0.07)',
    borderWidth: 1,
    borderColor: 'rgba(196,144,15,0.18)',
    marginRight: 8,
  },
  filterActive: {
    backgroundColor: 'rgba(212,160,23,0.2)',
    borderColor: colors.gold,
  },
  filterText: { fontSize: 13, color: colors.textMuted, fontWeight: '500' },
  filterActiveText: { color: colors.gold, fontWeight: '700' },
  countText: {
    fontSize: 12,
    color: colors.textMuted,
    paddingHorizontal: 20,
    marginBottom: 12,
  },
  emptyState: { alignItems: 'center', marginTop: 60 },
  emptyOm: { fontSize: 64, color: colors.gold, opacity: 0.4 },
  emptyText: { fontSize: 16, fontWeight: '700', color: colors.text, marginTop: 12 },
  emptySubtext: { fontSize: 13, color: colors.textMuted, marginTop: 6 },
  list: { paddingHorizontal: 20 },
  sessionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(212,160,23,0.15)',
    gap: 14,
  },
  symbolBox: {
    width: 52,
    height: 52,
    borderRadius: 12,
    backgroundColor: 'rgba(212,160,23,0.08)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(212,160,23,0.2)',
  },
  symbolText: { fontSize: 26 },
  cardBody: { flex: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4 },
  sessionTitle: { flex: 1, fontSize: 14, fontWeight: '700', color: colors.text },
  liveBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.liveBadge,
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 100,
    gap: 4,
  },
  liveDot: { width: 5, height: 5, borderRadius: 3, backgroundColor: '#FFF' },
  liveText: { color: '#FFF', fontSize: 10, fontWeight: '700' },
  sessionMeta: { fontSize: 11, color: colors.textMuted, marginBottom: 10 },
  bottomRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  progressWrap: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 6 },
  progressBar: { flex: 1, height: 3, backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 2 },
  progressFill: { height: 3, backgroundColor: colors.gold, borderRadius: 2 },
  progressPct: { fontSize: 10, color: colors.textMuted, minWidth: 28 },
});
