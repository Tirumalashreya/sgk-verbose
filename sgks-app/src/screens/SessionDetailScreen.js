import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Dimensions, TextInput, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '../theme/colors';
import VaishnavaBg from '../components/VaishnavaBg';
import ShlokaBox from '../components/ShlokaBox';
import LabelChip from '../components/LabelChip';
import FloatingPlayer from '../components/FloatingPlayer';

const TABS = ['Summary', 'Notes', 'Slokas', 'Stories'];

const SAMPLE_STORIES = [
  { title: 'The Devotion of Ambarīṣa', day: 'Day 7', duration: '18:26', symbol: '🪷' },
  { title: "Prahlāda's Unwavering Faith", day: 'Day 7', duration: '22:14', symbol: 'ॐ' },
  { title: "Dhruva's Determination", day: 'Day 7', duration: '22:15', symbol: '☸' },
];

export default function SessionDetailScreen({ route, navigation }) {
  const { session } = route.params || {};
  const [activeTab, setActiveTab] = useState('Summary');
  const [isPlaying, setIsPlaying] = useState(true);

  // Editable notes state
  const [localNotes, setLocalNotes] = useState(session?.notes || '');
  const [localEnhanced, setLocalEnhanced] = useState(session?.enhanced_notes || '');
  const [editingNotes, setEditingNotes] = useState(false);
  const [editingEnhanced, setEditingEnhanced] = useState(false);
  const [draftNotes, setDraftNotes] = useState('');
  const [draftEnhanced, setDraftEnhanced] = useState('');

  const segments = session?.segments || [];
  const shlokas = session?.shlokas || [];
  const stories = segments.filter(s => s.label === 'story');
  const teachings = segments.filter(s => s.label === 'teaching' || s.label === 'philosophy');

  const startEditNotes = () => { setDraftNotes(localNotes); setEditingNotes(true); };
  const saveNotes = () => { setLocalNotes(draftNotes); setEditingNotes(false); };
  const cancelNotes = () => setEditingNotes(false);

  const startEditEnhanced = () => { setDraftEnhanced(localEnhanced); setEditingEnhanced(true); };
  const saveEnhanced = () => { setLocalEnhanced(draftEnhanced); setEditingEnhanced(false); };
  const cancelEnhanced = () => setEditingEnhanced(false);

  return (
    <VaishnavaBg>
      <SafeAreaView style={{ flex: 1 }}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <Ionicons name="arrow-back" size={22} color={colors.gold} />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.headerTitle} numberOfLines={1}>
              {session?.title || 'Śrīmad Bhāgavatam – Day 13'}
            </Text>
            <Text style={styles.headerSub}>
              Today · 9:00 AM · <Text style={styles.liveRed}>● Live</Text>
            </Text>
          </View>
          <TouchableOpacity>
            <Ionicons name="bookmark-outline" size={22} color={colors.gold} />
          </TouchableOpacity>
        </View>

        {/* Lang toggle */}
        <View style={styles.langRow}>
          <TouchableOpacity style={[styles.langBtn, styles.langActive]}>
            <Text style={styles.langActiveText}>ENGLISH</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.langBtn}>
            <Text style={styles.langText}>తెలుగు</Text>
          </TouchableOpacity>
        </View>

        {/* Tabs */}
        <View style={styles.tabBar}>
          {TABS.map(tab => (
            <TouchableOpacity key={tab} style={styles.tab} onPress={() => setActiveTab(tab)}>
              <Text style={[styles.tabText, activeTab === tab && styles.tabActive]}>{tab}</Text>
              {activeTab === tab && <View style={styles.tabIndicator} />}
            </TouchableOpacity>
          ))}
        </View>

        <KeyboardAvoidingView
          style={{ flex: 1 }}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <ScrollView style={{ flex: 1 }} showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 40 }}>

            {/* SUMMARY */}
            {activeTab === 'Summary' && (
              <View>
                <LinearGradient
                  colors={['rgba(212,160,23,0.1)', 'rgba(212,160,23,0.03)']}
                  style={styles.card}
                >
                  <View style={styles.cardHeader}>
                    <View style={styles.cardTitleRow}>
                      <Text style={styles.spark}>✦</Text>
                      <Text style={styles.cardTitle}>AI Summary</Text>
                    </View>
                    <View style={styles.autoBadge}>
                      <Text style={styles.autoBadgeText}>Auto-generated</Text>
                    </View>
                  </View>
                  <Text style={styles.bodyText}>
                    {session?.summary || 'Processing... Notes will appear as the session continues.'}
                  </Text>
                </LinearGradient>

                {teachings.length > 0 && (
                  <View style={styles.section}>
                    <View style={styles.sectionRow}>
                      <Text style={styles.spark}>✦</Text>
                      <Text style={styles.sectionHeading}>Key Highlights</Text>
                    </View>
                    {teachings.slice(0, 5).map((t, i) => (
                      <View key={i} style={styles.highlightRow}>
                        <Ionicons name="checkmark-circle" size={18} color={colors.gold} />
                        <Text style={styles.highlightText}>{t.summary || t.text}</Text>
                      </View>
                    ))}
                  </View>
                )}

                <View style={styles.actions}>
                  {[['heart-outline','248'], ['bookmark-outline','Bookmark'], ['share-outline','Share']].map(([icon, label], i) => (
                    <TouchableOpacity key={i} style={styles.actionBtn}>
                      <Ionicons name={icon} size={20} color={colors.textMuted} />
                      <Text style={styles.actionText}>{label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>

                <View style={styles.section}>
                  <Text style={styles.sectionHeading}>Key Moments</Text>
                  {segments.slice(0, 4).map((seg, i) => (
                    <View key={i} style={styles.momentRow}>
                      <TouchableOpacity style={styles.playCircle}>
                        <Ionicons name="play" size={12} color={colors.gold} />
                      </TouchableOpacity>
                      <Text style={styles.timestamp}>00:{String(i * 5 + 5).padStart(2,'0')}:12</Text>
                      <Text style={styles.momentText}>{seg.summary || seg.text?.slice(0, 50)}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}

            {/* NOTES — Exact + AI Enhanced, both editable */}
            {activeTab === 'Notes' && (
              <View style={styles.section}>

                {/* ── Exact Notes ── */}
                <View style={styles.notesCard}>
                  <View style={styles.notesCardHeader}>
                    <View style={styles.cardTitleRow}>
                      <Text style={styles.spark}>✦</Text>
                      <Text style={styles.cardTitle}>Exact Notes</Text>
                    </View>
                    {editingNotes ? (
                      <View style={styles.editBtnRow}>
                        <TouchableOpacity style={styles.cancelBtn} onPress={cancelNotes}>
                          <Ionicons name="close" size={16} color={colors.textMuted} />
                          <Text style={styles.cancelBtnText}>Cancel</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={styles.saveBtn} onPress={saveNotes}>
                          <Ionicons name="checkmark" size={16} color="#FFF" />
                          <Text style={styles.saveBtnText}>Save</Text>
                        </TouchableOpacity>
                      </View>
                    ) : (
                      <TouchableOpacity style={styles.editIconBtn} onPress={startEditNotes}>
                        <Ionicons name="pencil-outline" size={16} color={colors.gold} />
                        <Text style={styles.editIconText}>Edit</Text>
                      </TouchableOpacity>
                    )}
                  </View>

                  <View style={styles.notesBadgeRow}>
                    <View style={styles.notesBadge}>
                      <Text style={styles.notesBadgeText}>Word-for-word</Text>
                    </View>
                  </View>

                  {editingNotes ? (
                    <TextInput
                      multiline
                      autoFocus
                      value={draftNotes}
                      onChangeText={setDraftNotes}
                      style={styles.notesInput}
                      placeholder="Edit exact notes here..."
                      placeholderTextColor={colors.textMuted}
                    />
                  ) : (
                    <Text style={styles.notesText}>
                      {localNotes || 'Exact notes will appear after the session is processed.'}
                    </Text>
                  )}
                </View>

                {/* ── AI Enhanced Notes ── */}
                <View style={[styles.notesCard, { marginTop: 16 }]}>
                  <View style={styles.notesCardHeader}>
                    <View style={styles.cardTitleRow}>
                      <Text style={styles.spark}>✦</Text>
                      <Text style={styles.cardTitle}>AI Enhanced Notes</Text>
                    </View>
                    {editingEnhanced ? (
                      <View style={styles.editBtnRow}>
                        <TouchableOpacity style={styles.cancelBtn} onPress={cancelEnhanced}>
                          <Ionicons name="close" size={16} color={colors.textMuted} />
                          <Text style={styles.cancelBtnText}>Cancel</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={styles.saveBtn} onPress={saveEnhanced}>
                          <Ionicons name="checkmark" size={16} color="#FFF" />
                          <Text style={styles.saveBtnText}>Save</Text>
                        </TouchableOpacity>
                      </View>
                    ) : (
                      <TouchableOpacity style={styles.editIconBtn} onPress={startEditEnhanced}>
                        <Ionicons name="pencil-outline" size={16} color={colors.gold} />
                        <Text style={styles.editIconText}>Edit</Text>
                      </TouchableOpacity>
                    )}
                  </View>

                  <View style={styles.notesBadgeRow}>
                    <View style={[styles.notesBadge, styles.enhancedBadge]}>
                      <Text style={[styles.notesBadgeText, styles.enhancedBadgeText]}>AI enriched with context & meanings</Text>
                    </View>
                  </View>

                  {editingEnhanced ? (
                    <TextInput
                      multiline
                      autoFocus
                      value={draftEnhanced}
                      onChangeText={setDraftEnhanced}
                      style={styles.notesInput}
                      placeholder="Edit AI enhanced notes here..."
                      placeholderTextColor={colors.textMuted}
                    />
                  ) : (
                    <Text style={styles.notesText}>
                      {localEnhanced || 'AI enhanced notes will appear after the session is processed.'}
                    </Text>
                  )}
                </View>

              </View>
            )}

            {/* SLOKAS */}
            {activeTab === 'Slokas' && (
              <View style={{ paddingTop: 16 }}>
                {shlokas.length === 0
                  ? <Text style={[styles.emptyText, { margin: 20 }]}>ॐ Shlokas will appear as they are detected...</Text>
                  : shlokas.map((s, i) => (
                    <ShlokaBox
                      key={i}
                      shloka={typeof s === 'string' ? s : s.text}
                      meaning={s.meaning}
                      source={s.source}
                    />
                  ))}

                <View style={styles.storiesSectionHeader}>
                  <Text style={styles.sectionHeading}>Stories from Today</Text>
                  <TouchableOpacity><Text style={styles.viewAll}>View all</Text></TouchableOpacity>
                </View>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingLeft: 20 }}>
                  {(stories.length > 0 ? stories : SAMPLE_STORIES).map((s, i) => (
                    <LinearGradient
                      key={i}
                      colors={['rgba(196,144,15,0.12)', 'rgba(196,144,15,0.04)']}
                      style={styles.storyCard}
                    >
                      <View style={styles.storyThumb}>
                        <Text style={styles.storySymbol}>{s.symbol || '🪷'}</Text>
                        <View style={styles.durationBadge}>
                          <Text style={styles.durationText}>{s.duration || '00:00'}</Text>
                        </View>
                      </View>
                      <Text style={styles.storyTitle} numberOfLines={2}>{s.title || s.text}</Text>
                      <Text style={styles.storyDay}>{s.day || 'Day 7'}</Text>
                    </LinearGradient>
                  ))}
                </ScrollView>
              </View>
            )}

            {/* STORIES */}
            {activeTab === 'Stories' && (
              <View style={styles.section}>
                {stories.length === 0
                  ? <Text style={styles.emptyText}>🪷 Stories will appear as session progresses...</Text>
                  : stories.map((s, i) => (
                    <LinearGradient key={i} colors={['rgba(255,255,255,0.92)','rgba(255,255,255,0.75)']} style={styles.teachingCard}>
                      <LabelChip label="story" />
                      <Text style={styles.teachingText}>{s.text}</Text>
                      {s.summary && <Text style={styles.teachingSummary}>{s.summary}</Text>}
                    </LinearGradient>
                  ))}
              </View>
            )}

            <View style={{ height: 160 }} />
          </ScrollView>
        </KeyboardAvoidingView>

        <FloatingPlayer
          session={{ title: session?.title || 'Live Session' }}
          isPlaying={isPlaying}
          onToggle={() => setIsPlaying(!isPlaying)}
        />
      </SafeAreaView>
    </VaishnavaBg>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 14, gap: 12 },
  headerCenter: { flex: 1 },
  headerTitle: { fontSize: 16, fontWeight: '700', color: colors.text },
  headerSub: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  liveRed: { color: colors.liveBadge },
  langRow: { flexDirection: 'row', gap: 10, paddingHorizontal: 20, marginBottom: 12 },
  langBtn: { paddingHorizontal: 16, paddingVertical: 7, borderRadius: 100, borderWidth: 1.5, borderColor: 'rgba(212,160,23,0.35)' },
  langActive: { backgroundColor: 'rgba(212,160,23,0.15)' },
  langActiveText: { color: colors.gold, fontWeight: '700', fontSize: 12 },
  langText: { color: colors.textMuted, fontWeight: '600', fontSize: 12 },
  tabBar: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: 'rgba(196,144,15,0.2)', marginBottom: 4 },
  tab: { flex: 1, alignItems: 'center', paddingVertical: 12 },
  tabText: { fontSize: 12, color: colors.textMuted, fontWeight: '500' },
  tabActive: { color: colors.gold, fontWeight: '700' },
  tabIndicator: { position: 'absolute', bottom: 0, height: 2.5, width: '70%', backgroundColor: colors.gold, borderRadius: 2 },
  card: { borderRadius: 16, padding: 20, marginHorizontal: 20, marginTop: 16, borderWidth: 1, borderColor: 'rgba(212,160,23,0.15)' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  cardTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  spark: { color: colors.gold, fontSize: 16 },
  cardTitle: { fontSize: 15, fontWeight: '700', color: colors.text },
  autoBadge: { backgroundColor: 'rgba(196,144,15,0.12)', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 100 },
  autoBadgeText: { fontSize: 10, color: colors.textMuted },
  bodyText: { fontSize: 15, lineHeight: 24, color: colors.text },
  section: { paddingHorizontal: 20, marginTop: 20 },
  sectionRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 14 },
  sectionHeading: { fontSize: 15, fontWeight: '700', color: colors.text },
  highlightRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 12 },
  highlightText: { flex: 1, fontSize: 14, lineHeight: 22, color: colors.text },
  actions: { flexDirection: 'row', justifyContent: 'center', gap: 32, paddingVertical: 16, borderTopWidth: 1, borderBottomWidth: 1, borderColor: 'rgba(196,144,15,0.15)', marginTop: 16, marginHorizontal: 20 },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  actionText: { fontSize: 13, color: colors.textMuted },
  momentRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  playCircle: { width: 32, height: 32, borderRadius: 16, borderWidth: 1.5, borderColor: colors.gold, justifyContent: 'center', alignItems: 'center' },
  timestamp: { fontSize: 11, color: colors.gold, fontWeight: '600', width: 56 },
  momentText: { flex: 1, fontSize: 13, color: colors.text, lineHeight: 20 },

  // Notes cards
  notesCard: {
    backgroundColor: colors.white,
    borderRadius: 18,
    padding: 18,
    borderWidth: 1,
    borderColor: 'rgba(196,144,15,0.2)',
    shadowColor: colors.gold,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 2,
  },
  notesCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  notesBadgeRow: { marginBottom: 14 },
  notesBadge: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(196,144,15,0.1)',
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 100,
  },
  notesBadgeText: { fontSize: 10, color: colors.gold, fontWeight: '600' },
  enhancedBadge: { backgroundColor: 'rgba(74,138,104,0.12)' },
  enhancedBadgeText: { color: colors.tulasi },
  notesText: { fontSize: 14, lineHeight: 24, color: colors.text },
  notesInput: {
    fontSize: 14,
    lineHeight: 24,
    color: colors.text,
    minHeight: 200,
    textAlignVertical: 'top',
    borderWidth: 1.5,
    borderColor: 'rgba(196,144,15,0.3)',
    borderRadius: 12,
    padding: 14,
    backgroundColor: colors.background,
  },
  editIconBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 100,
    borderWidth: 1.5,
    borderColor: colors.gold,
    backgroundColor: 'rgba(196,144,15,0.08)',
  },
  editIconText: { fontSize: 12, color: colors.gold, fontWeight: '600' },
  editBtnRow: { flexDirection: 'row', gap: 8 },
  cancelBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 100,
    borderWidth: 1,
    borderColor: 'rgba(122,92,60,0.3)',
  },
  cancelBtnText: { fontSize: 12, color: colors.textMuted, fontWeight: '600' },
  saveBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 100,
    backgroundColor: colors.tulasi,
  },
  saveBtnText: { fontSize: 12, color: '#FFF', fontWeight: '700' },

  // Teachings
  teachingCard: { borderRadius: 14, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: 'rgba(196,144,15,0.2)' },
  teachingText: { fontSize: 14, lineHeight: 22, color: colors.text, marginTop: 10 },
  teachingSummary: { fontSize: 12, color: colors.textMuted, marginTop: 6, fontStyle: 'italic' },
  emptyText: { color: colors.textMuted, textAlign: 'center', marginTop: 40, fontSize: 14 },
  storiesSectionHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, marginTop: 28, marginBottom: 14,
  },
  viewAll: { fontSize: 13, color: colors.gold, fontWeight: '600' },
  storyCard: {
    width: 140, borderRadius: 14, marginRight: 12, overflow: 'hidden',
    borderWidth: 1, borderColor: 'rgba(212,160,23,0.2)', marginBottom: 20,
  },
  storyThumb: {
    height: 86, backgroundColor: 'rgba(212,160,23,0.08)',
    justifyContent: 'center', alignItems: 'center',
  },
  storySymbol: { fontSize: 36 },
  durationBadge: {
    position: 'absolute', bottom: 6, right: 6,
    backgroundColor: 'rgba(0,0,0,0.55)',
    paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4,
  },
  durationText: { fontSize: 10, color: '#FFF', fontWeight: '600' },
  storyTitle: { fontSize: 12, fontWeight: '600', color: colors.text, padding: 10, paddingBottom: 4, lineHeight: 18 },
  storyDay: { fontSize: 11, color: colors.textMuted, paddingHorizontal: 10, paddingBottom: 10 },
});
