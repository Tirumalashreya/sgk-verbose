import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '../theme/colors';
import VaishnavaBg from '../components/VaishnavaBg';
import { searchQuery } from '../services/api';
import LabelChip from '../components/LabelChip';

const RECENT = ['Devotion', 'Bhakti', 'Krishna', 'Surrender', 'Dharma'];
const FILTERS = ['All', 'Teaching', 'Sloka', 'Story', 'Philosophy'];

export default function SearchScreen() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState('All');

  const handleSearch = async (q) => {
    if (!q.trim()) return;
    setLoading(true);
    try {
      const res = await searchQuery(q);
      setResults(res.result ? [{ text: res.result, label: 'teaching', session: 'Search Result', time: '' }] : []);
    } catch { setResults([]); }
    setLoading(false);
  };

  return (
    <VaishnavaBg>
      <SafeAreaView style={{ flex: 1 }}>
        {/* Lang toggle */}
        <View style={styles.langRow}>
          <TouchableOpacity style={[styles.langBtn, styles.langActive]}>
            <Text style={styles.langActiveText}>ENGLISH</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.langBtn}>
            <Text style={styles.langText}>తెలుగు</Text>
          </TouchableOpacity>
        </View>

        {/* Search Bar */}
        <View style={styles.searchBar}>
          <Ionicons name="search" size={18} color={colors.gold} />
          <TextInput
            style={styles.input}
            placeholder="Ask anything about the pravachanam..."
            placeholderTextColor={colors.textMuted}
            value={query}
            onChangeText={setQuery}
            onSubmitEditing={() => handleSearch(query)}
            returnKeyType="search"
          />
          <TouchableOpacity onPress={() => handleSearch(query)}>
            <Ionicons name="mic-outline" size={18} color={colors.gold} />
          </TouchableOpacity>
        </View>

        <ScrollView showsVerticalScrollIndicator={false}>
          {results.length === 0 && !loading ? (
            <>
              <Text style={styles.sectionLabel}>Recent Searches</Text>
              <View style={styles.chipRow}>
                {RECENT.map(r => (
                  <TouchableOpacity key={r} style={styles.recentChip} onPress={() => { setQuery(r); handleSearch(r); }}>
                    <Text style={styles.recentChipText}>{r}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <View style={styles.emptyState}>
                <Text style={styles.emptyOm}>ॐ</Text>
                <Text style={styles.emptyLotus}>❀</Text>
                <Text style={styles.emptyTitle}>Ask Guru Garu anything</Text>
                <Text style={styles.emptySubtitle}>Search across all pravachanams using natural language</Text>
              </View>
            </>
          ) : (
            <>
              <View style={styles.chipRow}>
                {FILTERS.map(f => (
                  <TouchableOpacity key={f} style={[styles.filterChip, activeFilter === f && styles.filterActive]} onPress={() => setActiveFilter(f)}>
                    <Text style={[styles.filterText, activeFilter === f && styles.filterActiveText]}>{f}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              {loading
                ? <ActivityIndicator color={colors.gold} style={{ marginTop: 40 }} />
                : results.map((r, i) => (
                  <LinearGradient key={i} colors={['rgba(255,255,255,0.92)','rgba(255,255,255,0.75)']} style={styles.resultCard}>
                    <LabelChip label={r.label} />
                    <Text style={styles.resultText}>{r.text}</Text>
                    <View style={styles.resultMeta}>
                      <Text style={styles.resultSession}>{r.session}</Text>
                      {r.time ? <Text style={styles.resultTime}>{r.time}</Text> : null}
                      <TouchableOpacity style={styles.playBtn}>
                        <Ionicons name="play" size={12} color={colors.gold} />
                      </TouchableOpacity>
                    </View>
                  </LinearGradient>
                ))
              }
            </>
          )}
          <View style={{ height: 100 }} />
        </ScrollView>
      </SafeAreaView>
    </VaishnavaBg>
  );
}

const styles = StyleSheet.create({
  langRow: { flexDirection: 'row', gap: 10, paddingHorizontal: 20, paddingTop: 14, marginBottom: 14 },
  langBtn: { paddingHorizontal: 16, paddingVertical: 7, borderRadius: 100, borderWidth: 1.5, borderColor: 'rgba(212,160,23,0.35)' },
  langActive: { backgroundColor: 'rgba(212,160,23,0.15)' },
  langActiveText: { color: colors.gold, fontWeight: '700', fontSize: 12 },
  langText: { color: colors.textMuted, fontWeight: '600', fontSize: 12 },
  searchBar: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.85)', marginHorizontal: 20,
    borderRadius: 100, paddingHorizontal: 16, paddingVertical: 14,
    gap: 10, borderWidth: 1, borderColor: 'rgba(196,144,15,0.35)', marginBottom: 20,
  },
  input: { flex: 1, fontSize: 14, color: colors.text },
  sectionLabel: { fontSize: 13, fontWeight: '600', color: colors.textMuted, paddingHorizontal: 20, marginBottom: 12 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: 20, gap: 8, marginBottom: 20 },
  recentChip: { backgroundColor: 'rgba(196,144,15,0.08)', paddingHorizontal: 14, paddingVertical: 7, borderRadius: 100, borderWidth: 1, borderColor: 'rgba(196,144,15,0.18)' },
  recentChipText: { fontSize: 13, color: colors.text },
  filterChip: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 100, backgroundColor: 'rgba(196,144,15,0.07)' },
  filterActive: { backgroundColor: 'rgba(212,160,23,0.25)', borderWidth: 1, borderColor: colors.gold },
  filterText: { fontSize: 13, color: colors.textMuted },
  filterActiveText: { color: colors.gold, fontWeight: '700' },
  emptyState: { alignItems: 'center', marginTop: 50 },
  emptyOm: { fontSize: 80, color: colors.gold, opacity: 0.4 },
  emptyLotus: { fontSize: 32, color: colors.gold, opacity: 0.5, marginTop: -10 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: colors.text, marginTop: 16 },
  emptySubtitle: { fontSize: 13, color: colors.textMuted, textAlign: 'center', marginTop: 8, paddingHorizontal: 40, lineHeight: 20 },
  resultCard: { borderRadius: 14, padding: 16, marginHorizontal: 20, marginBottom: 12, borderWidth: 1, borderColor: 'rgba(196,144,15,0.2)' },
  resultText: { fontSize: 14, lineHeight: 22, color: colors.text, marginTop: 10, marginBottom: 10 },
  resultMeta: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  resultSession: { flex: 1, fontSize: 12, color: colors.textMuted },
  resultTime: { fontSize: 12, color: colors.textMuted },
  playBtn: { width: 26, height: 26, borderRadius: 13, borderWidth: 1.5, borderColor: colors.gold, justifyContent: 'center', alignItems: 'center' },
});
