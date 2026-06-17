import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Animated, Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '../theme/colors';
import VaishnavaBg from '../components/VaishnavaBg';
import { createWebSocket, getSessions } from '../services/api';

const { width } = Dimensions.get('window');

const AI_CATEGORIES = [
  { id: 'summary', icon: 'document-text-outline', label: 'Summary', symbol: '📜' },
  { id: 'teachings', icon: 'bulb-outline', label: 'Key Teachings', symbol: '✦' },
  { id: 'slokas', icon: 'text-outline', label: 'Slokas', symbol: 'ॐ' },
  { id: 'stories', icon: 'book-outline', label: 'Stories', symbol: '🪷' },
];

const TOPICS = [
  { label: 'Bhagavad Gītā', sessions: '126' },
  { label: 'Śrīmad Bhāgavatam', sessions: '248' },
  { label: 'Rāmāyaṇa', sessions: '98' },
  { label: 'Vishnu Sahasranāma', sessions: '56' },
];

export default function HomeScreen({ navigation }) {
  const [liveData, setLiveData] = useState(null);
  const [isLive, setIsLive] = useState(false);
  const [recentSessions, setRecentSessions] = useState([]);
  const waveAnim = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    const ws = createWebSocket((data) => {
      if (data.type === 'chunk_complete') {
        setLiveData(data);
        setIsLive(true);
        setRecentSessions(prev => [data, ...prev].slice(0, 3));
      }
    }, () => {});

    getSessions().then(data => {
      const all = (data.sessions || []).reverse();
      setRecentSessions(all.slice(0, 3));
    }).catch(() => {});

    return () => ws.close();
  }, []);

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(waveAnim, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(waveAnim, { toValue: 0.3, duration: 700, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  return (
    <VaishnavaBg>
      <SafeAreaView style={{ flex: 1 }}>
        <ScrollView showsVerticalScrollIndicator={false}>

          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity>
              <Ionicons name="menu" size={24} color={colors.gold} />
            </TouchableOpacity>
            <View style={styles.headerCenter}>
              <Text style={styles.lotusSmall}>❀</Text>
              <Text style={styles.headerTitle}>Sgks Live Notes</Text>
            </View>
            <TouchableOpacity>
              <Ionicons name="notifications-outline" size={24} color={colors.gold} />
            </TouchableOpacity>
          </View>

          {/* Language toggle */}
          <View style={styles.langRow}>
            <TouchableOpacity style={[styles.langBtn, styles.langActive]}>
              <Text style={styles.langActiveText}>ENGLISH</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.langBtn}>
              <Text style={styles.langText}>తెలుగు</Text>
            </TouchableOpacity>
          </View>

          {/* Live Now Card — saffron pastel gradient */}
          <TouchableOpacity
            onPress={() => liveData && navigation.navigate('SessionDetail', { session: liveData })}
            style={styles.liveCardWrap}
          >
            <LinearGradient
              colors={['#FFE4B8', '#FFD08A', '#FFC060']}
              style={styles.liveCard}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            >
              <View style={styles.liveCardBorder} />
              <Text style={styles.liveCardOm}>ॐ</Text>

              <View style={styles.liveBadge}>
                <View style={styles.liveDot} />
                <Text style={styles.liveText}>LIVE NOW</Text>
              </View>
              <Text style={styles.liveTitle}>
                {liveData ? 'Śrīmad Bhāgavatam – Live' : 'Start a Live Session'}
              </Text>
              <Text style={styles.liveSubtitle}>
                {isLive ? '🎙 Listening & Generating Notes...' : 'Go to Live tab to begin'}
              </Text>

              <View style={styles.waveform}>
                {Array.from({ length: 24 }).map((_, i) => (
                  <Animated.View
                    key={i}
                    style={[
                      styles.waveBar,
                      { height: 4 + (i % 5) * 4, opacity: waveAnim },
                    ]}
                  />
                ))}
              </View>
            </LinearGradient>
          </TouchableOpacity>

          {/* Continue Listening */}
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Continue Listening</Text>
            <TouchableOpacity><Text style={styles.viewAll}>View all</Text></TouchableOpacity>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingLeft: 20 }}>
            {recentSessions.length === 0 ? (
              <View style={styles.noSessionsCard}>
                <Text style={styles.noSessionsText}>Start a session to see your history here</Text>
              </View>
            ) : recentSessions.map((session, i) => (
              <TouchableOpacity
                key={i}
                onPress={() => navigation.navigate('SessionDetail', { session })}
              >
                <LinearGradient
                  colors={['rgba(196,144,15,0.12)', 'rgba(196,144,15,0.04)']}
                  style={styles.sessionCard}
                >
                  <View style={styles.sessionCardImg}>
                    <Text style={styles.sessionCardSymbol}>{['🪷', 'ॐ', '☸'][i % 3]}</Text>
                  </View>
                  <View style={styles.sessionCardBody}>
                    <Text style={styles.sessionCardTitle} numberOfLines={2}>
                      {session.title || `Session ${session.chunk_index + 1}`}
                    </Text>
                    <Text style={styles.sessionCardSub}>
                      {session.shlokas?.length || 0} shlokas · {session.segments?.length || 0} segments
                    </Text>
                  </View>
                </LinearGradient>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* AI Generated For You */}
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>AI Generated For You</Text>
          </View>
          <View style={styles.grid}>
            {AI_CATEGORIES.map((cat) => (
              <TouchableOpacity key={cat.id}>
                <LinearGradient
                  colors={['rgba(212,160,23,0.15)', 'rgba(212,160,23,0.05)']}
                  style={styles.gridCard}
                >
                  <Text style={styles.gridSymbol}>{cat.symbol}</Text>
                  <Text style={styles.gridLabel}>{cat.label}</Text>
                </LinearGradient>
              </TouchableOpacity>
            ))}
          </View>

          {/* Browse Topics */}
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Browse Topics</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingLeft: 20, paddingBottom: 8 }}>
            {TOPICS.map((t, i) => (
              <TouchableOpacity key={i} style={styles.topicChip}>
                <Text style={styles.topicLabel}>{t.label}</Text>
                <Text style={styles.topicSessions}>{t.sessions} Sessions</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          <View style={{ height: 110 }} />
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
  headerCenter: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  lotusSmall: { fontSize: 18, color: colors.gold },
  headerTitle: { fontSize: 17, fontWeight: '700', color: colors.text },
  langRow: { flexDirection: 'row', gap: 10, paddingHorizontal: 20, marginBottom: 16 },
  langBtn: {
    paddingHorizontal: 18,
    paddingVertical: 8,
    borderRadius: 100,
    borderWidth: 1.5,
    borderColor: 'rgba(196,144,15,0.4)',
  },
  langActive: { backgroundColor: 'rgba(196,144,15,0.15)' },
  langActiveText: { color: colors.gold, fontWeight: '700', fontSize: 13 },
  langText: { color: colors.textMuted, fontWeight: '600', fontSize: 13 },
  liveCardWrap: { marginHorizontal: 20, marginBottom: 28, borderRadius: 20, overflow: 'hidden' },
  liveCard: { borderRadius: 20, padding: 20, minHeight: 160, overflow: 'hidden' },
  liveCardBorder: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(196,144,15,0.4)',
  },
  liveCardOm: {
    position: 'absolute',
    right: -10,
    top: -20,
    fontSize: 140,
    color: colors.goldDeep,
    opacity: 0.1,
  },
  liveBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.liveBadge,
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 100,
    marginBottom: 12,
    gap: 5,
  },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#FFF' },
  liveText: { color: '#FFF', fontSize: 11, fontWeight: '700' },
  liveTitle: { color: colors.text, fontSize: 19, fontWeight: '700', marginBottom: 6 },
  liveSubtitle: { color: colors.textMuted, fontSize: 13, marginBottom: 16 },
  waveform: { flexDirection: 'row', alignItems: 'center', gap: 3 },
  waveBar: { width: 3, backgroundColor: colors.goldDeep, borderRadius: 2 },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    marginBottom: 14,
  },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.text },
  viewAll: { fontSize: 13, color: colors.gold, fontWeight: '600' },
  noSessionsCard: {
    width: 220,
    height: 140,
    borderRadius: 16,
    marginRight: 14,
    backgroundColor: 'rgba(196,144,15,0.07)',
    borderWidth: 1,
    borderColor: 'rgba(196,144,15,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  noSessionsText: { fontSize: 13, color: colors.textMuted, textAlign: 'center', lineHeight: 20 },
  sessionCard: {
    borderRadius: 16,
    marginRight: 14,
    width: 160,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(196,144,15,0.2)',
    marginBottom: 28,
  },
  sessionCardImg: {
    height: 90,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(196,144,15,0.08)',
  },
  sessionCardSymbol: { fontSize: 40 },
  sessionCardBody: { padding: 12 },
  sessionCardTitle: { fontSize: 13, fontWeight: '700', color: colors.text, marginBottom: 3 },
  sessionCardSub: { fontSize: 11, color: colors.textMuted, marginBottom: 8 },
  progressRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  progressBar: { flex: 1, height: 3, backgroundColor: 'rgba(45,24,0,0.1)', borderRadius: 2 },
  progressFill: { height: 3, backgroundColor: colors.gold, borderRadius: 2 },
  progressPct: { fontSize: 10, color: colors.textMuted },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 20,
    gap: 14,
    marginBottom: 28,
  },
  gridCard: {
    width: (width - 54) / 2,
    borderRadius: 16,
    paddingVertical: 24,
    alignItems: 'center',
    gap: 10,
    borderWidth: 1,
    borderColor: 'rgba(196,144,15,0.2)',
  },
  gridSymbol: { fontSize: 32, color: colors.gold },
  gridLabel: { fontSize: 14, fontWeight: '600', color: colors.text },
  topicChip: {
    borderWidth: 1.5,
    borderColor: 'rgba(196,144,15,0.35)',
    borderRadius: 100,
    paddingHorizontal: 18,
    paddingVertical: 10,
    marginRight: 10,
    backgroundColor: 'rgba(196,144,15,0.08)',
  },
  topicLabel: { fontSize: 13, fontWeight: '600', color: colors.text },
  topicSessions: { fontSize: 10, color: colors.textMuted, marginTop: 2 },
});
