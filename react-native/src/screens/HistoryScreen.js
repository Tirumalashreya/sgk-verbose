// History — every pravachanam, searchable; multi-file merge with numbering; Word download; delete.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, TextInput, Pressable, RefreshControl, Modal, ScrollView, ActivityIndicator, StyleSheet } from 'react-native';
import { useTheme, F, T, S, R } from '../theme';
import { Screen, Enter, SessionRow, Button } from '../ui/kit';
import Icon from '../ui/Icon';
import { getSessions, getSession, deleteSession, mergeSessions, createWebSocket } from '../services/api';
import { downloadDOC } from '../services/download';
import { confirm, notify } from '../services/platform';

export default function HistoryScreen({ go, t, lang }) {
  const c = useTheme();
  const [sessions, setSessions] = useState([]);
  const [query, setQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  // Merge state
  const [mergeMode, setMergeMode] = useState(false);
  const [selectedMergeIds, setSelectedMergeIds] = useState([]);
  const [menuSession, setMenuSession] = useState(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [merging, setMerging] = useState(false);

  const load = useCallback(async () => {
    try { setSessions(((await getSessions()).sessions || []).slice().reverse()); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    let ws;
    createWebSocket((data) => {
      if (data.type === 'session_complete' || data.type === 'chunk_complete') load();
    }).then((w) => { ws = w; }).catch(() => {});
    return () => { ws?.close?.(); };
  }, [load]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? sessions.filter((s) => (s.title || '').toLowerCase().includes(q)) : sessions;
  }, [sessions, query]);

  const remove = async (s) => {
    if (!(await confirm(s.title || 'Pravachanam', t('deleteConfirm'), t('delete')))) return;
    try { await deleteSession(s.id); setSessions((l) => l.filter((x) => x.id !== s.id)); } catch {}
  };

  const startMergeFrom = (s) => {
    setMenuSession(null);
    setMergeMode(true);
    setSelectedMergeIds([s.id]);
  };

  const toggleSelectMerge = (s) => {
    setSelectedMergeIds((prev) => {
      const idx = prev.indexOf(s.id);
      if (idx !== -1) {
        return prev.filter((id) => id !== s.id);
      }
      return [...prev, s.id];
    });
  };

  const cancelMergeMode = () => {
    setMergeMode(false);
    setSelectedMergeIds([]);
    setShowConfirmModal(false);
    setMerging(false);
  };

  const executeMerge = async () => {
    if (selectedMergeIds.length < 2) return;
    setMerging(true);
    try {
      await mergeSessions(selectedMergeIds);
      notify(t('history'), `Merging ${selectedMergeIds.length} recordings...`);
      cancelMergeMode();
      await load();
    } catch (e) {
      setMerging(false);
      notify(t('history'), String(e.message || 'Merge failed'));
    }
  };

  const handleDownloadWord = async (s) => {
    try {
      let fullSession = s;
      if (!fullSession?.notes || fullSession.notes.length < 50) {
        const res = await getSession(s.id);
        if (res?.session) fullSession = res.session;
      }
      await downloadDOC(fullSession);
    } catch (e) {
      notify(t('notes'), String(e.message || 'Download failed'));
    }
  };

  return (
    <Screen c={c}
      refreshControl={<RefreshControl refreshing={refreshing} tintColor={c.brass}
        onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}>
      <Enter>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View>
            <Text style={[lang === 'te' ? T.displayTe : T.display, { color: c.ink }]}>{t('notes')}</Text>
            <Text style={[T.body, { color: c.muted, marginTop: 4 }]}>
              {sessions.length} {sessions.length === 1 ? 'recording' : 'recordings'}
            </Text>
          </View>
          {!mergeMode && sessions.length >= 2 && (
            <Pressable
              onPress={() => { setMergeMode(true); setSelectedMergeIds([]); }}
              style={[st.mergeHeaderBtn, { borderColor: c.brass, backgroundColor: c.surface }]}
              accessibilityRole="button"
            >
              <Icon name="merge" size={16} color={c.brass} />
              <Text style={{ fontFamily: F.readMed, fontSize: 13, color: c.brass, fontWeight: '700' }}>Merge</Text>
            </Pressable>
          )}
        </View>
      </Enter>

      {/* Merge Mode Banner */}
      {mergeMode && (
        <View style={[st.mergeBanner, { backgroundColor: c.raised, borderColor: c.brass }]}>
          <View style={{ flex: 1 }}>
            <Text style={{ fontFamily: F.readBold, fontSize: 15, color: c.brass }}>
              Select recordings to merge (in sequence):
            </Text>
            <Text style={{ fontSize: 12.5, color: c.muted, marginTop: 2 }}>
              {selectedMergeIds.length === 0
                ? 'Tap recording to select (stamped with #1, #2...)'
                : `${selectedMergeIds.length} recordings selected (Merge Order: 1 to ${selectedMergeIds.length})`}
            </Text>
          </View>
          <Pressable onPress={cancelMergeMode} style={{ padding: 6 }}>
            <Text style={{ color: c.kumkumText, fontWeight: '700', fontSize: 13 }}>Cancel</Text>
          </Pressable>
        </View>
      )}

      {/* Search Bar */}
      <View style={[st.search, { borderColor: c.line, backgroundColor: c.surface }]}>
        <Icon name="search" size={18} color={c.muted} />
        <TextInput value={query} onChangeText={setQuery} placeholder={t('search')} placeholderTextColor={c.muted}
          style={[T.body, { flex: 1, color: c.ink, minHeight: 44 }]} accessibilityLabel={t('search')} returnKeyType="search" />
      </View>

      {/* Sessions List */}
      <View style={{ marginTop: S.l, paddingBottom: mergeMode ? 90 : 20 }}>
        {shown.length === 0 && <Text style={[T.body, { color: c.muted, paddingVertical: S.xl }]}>{t('emptyLibrary')}</Text>}
        {shown.map((s, i) => {
          const selIdx = selectedMergeIds.indexOf(s.id);
          const isSelected = selIdx !== -1;
          const orderNum = selIdx + 1;

          return (
            <View key={s.id || i} style={[st.rowContainer, isSelected && { backgroundColor: c.raised, borderRadius: R.control }]}>
              {mergeMode && (
                <Pressable onPress={() => toggleSelectMerge(s)} style={st.badgeTapArea}>
                  <View
                    style={[
                      st.orderBadge,
                      {
                        backgroundColor: isSelected ? c.brass : 'transparent',
                        borderColor: isSelected ? c.brass : c.line,
                      },
                    ]}
                  >
                    <Text style={[st.orderBadgeText, { color: isSelected ? c.onBrass : c.muted }]}>
                      {isSelected ? orderNum : '+'}
                    </Text>
                  </View>
                </Pressable>
              )}

              <View style={{ flex: 1 }}>
                <SessionRow
                  c={c}
                  t={t}
                  session={s}
                  divider={i < shown.length - 1}
                  onPress={() => (mergeMode ? toggleSelectMerge(s) : go('reading', { session: s }))}
                  onLongPress={() => (mergeMode ? toggleSelectMerge(s) : setMenuSession(s))}
                />
              </View>

              {!mergeMode && (
                <Pressable
                  onPress={() => setMenuSession(s)}
                  accessibilityRole="button"
                  accessibilityLabel={`Actions for ${s.title || ''}`}
                  hitSlop={8}
                  style={st.moreBtn}
                >
                  <Icon name="moreVertical" size={20} color={c.brass} />
                </Pressable>
              )}
            </View>
          );
        })}
      </View>

      {/* Bottom Floating Bar in Merge Mode */}
      {mergeMode && (
        <View style={[st.floatingBar, { backgroundColor: c.surface, borderColor: c.brass, shadowColor: '#000' }]}>
          <View style={{ flex: 1 }}>
            <Text style={{ fontFamily: F.readBold, fontSize: 14, color: c.ink }}>
              Selected: {selectedMergeIds.length} recordings
            </Text>
            <Text style={{ fontSize: 12, color: c.muted }}>
              {selectedMergeIds.length >= 2 ? 'Ready to merge in order' : 'Select at least 2 recordings'}
            </Text>
          </View>
          <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
            <Button c={c} variant="quiet" label="Cancel" onPress={cancelMergeMode} />
            <Button
              c={c}
              variant="brass"
              label={`Merge (${selectedMergeIds.length})`}
              onPress={() => setShowConfirmModal(true)}
              disabled={selectedMergeIds.length < 2 || merging}
            />
          </View>
        </View>
      )}

      {/* Actions Modal (Three Dots ⋮) */}
      <Modal visible={!!menuSession} transparent animationType="fade" onRequestClose={() => setMenuSession(null)}>
        <Pressable style={st.modalOverlay} onPress={() => setMenuSession(null)}>
          <Pressable style={[st.actionSheet, { backgroundColor: c.surface, borderColor: c.line }]} onPress={(e) => e.stopPropagation()}>
            <Text style={[st.sheetTitle, { color: c.ink, fontFamily: F.readBold }]} numberOfLines={2}>
              {menuSession?.title || 'Pravachanam'}
            </Text>
            <View style={{ height: StyleSheet.hairlineWidth, backgroundColor: c.line, marginVertical: S.s }} />

            <Pressable
              style={st.sheetItem}
              onPress={() => menuSession && startMergeFrom(menuSession)}
            >
              <Icon name="merge" size={20} color={c.brass} />
              <View style={{ flex: 1 }}>
                <Text style={[st.sheetItemText, { color: c.ink, fontFamily: F.readMed }]}>Merge with other recordings</Text>
                <Text style={{ fontSize: 12, color: c.muted }}>Set as #1 and select other recordings to merge</Text>
              </View>
            </Pressable>

            <Pressable
              style={st.sheetItem}
              onPress={() => {
                const s = menuSession;
                setMenuSession(null);
                s && handleDownloadWord(s);
              }}
            >
              <Icon name="share" size={20} color={c.brass} />
              <View style={{ flex: 1 }}>
                <Text style={[st.sheetItemText, { color: c.ink, fontFamily: F.readMed }]}>Download Word (.doc)</Text>
                <Text style={{ fontSize: 12, color: c.muted }}>Open directly in Microsoft Word with bold styling</Text>
              </View>
            </Pressable>

            <Pressable
              style={st.sheetItem}
              onPress={() => {
                const s = menuSession;
                setMenuSession(null);
                s && remove(s);
              }}
            >
              <Icon name="trash" size={20} color={c.kumkumText} />
              <View style={{ flex: 1 }}>
                <Text style={[st.sheetItemText, { color: c.kumkumText, fontFamily: F.readMed }]}>Delete recording</Text>
              </View>
            </Pressable>

            <Pressable
              style={[st.sheetCancelBtn, { borderColor: c.line }]}
              onPress={() => setMenuSession(null)}
            >
              <Text style={{ color: c.muted, fontWeight: '700', fontSize: 14 }}>Close</Text>
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>

      {/* Confirmation Modal Before Merge */}
      <Modal visible={showConfirmModal} transparent animationType="slide" onRequestClose={() => !merging && setShowConfirmModal(false)}>
        <View style={st.modalOverlay}>
          <View style={[st.confirmCard, { backgroundColor: c.surface, borderColor: c.brass }]}>
            <Text style={{ fontFamily: F.readBold, fontSize: 18, color: c.brass, marginBottom: 4 }}>
              Merge Recordings ({selectedMergeIds.length} files)
            </Text>
            <Text style={{ fontSize: 13, color: c.muted, marginBottom: S.m }}>
              Notes and audio will be joined in your selected sequence:
            </Text>

            <ScrollView style={{ maxHeight: 220, marginBottom: S.m }}>
              {selectedMergeIds.map((id, idx) => {
                const sess = sessions.find((x) => x.id === id);
                return (
                  <View key={id} style={st.confirmRow}>
                    <View style={[st.orderBadgeSmall, { backgroundColor: c.brass }]}>
                      <Text style={[st.orderBadgeSmallText, { color: c.onBrass }]}>{idx + 1}</Text>
                    </View>
                    <Text style={{ fontFamily: F.readMed, fontSize: 14, color: c.ink, flex: 1 }} numberOfLines={1}>
                      {sess?.title || 'Pravachanam'}
                    </Text>
                  </View>
                );
              })}
            </ScrollView>

            {merging ? (
              <View style={{ alignItems: 'center', paddingVertical: S.m }}>
                <ActivityIndicator color={c.brass} size="large" />
                <Text style={{ marginTop: S.s, fontFamily: F.readMed, fontSize: 14, color: c.brass }}>
                  Merging recordings... Please wait
                </Text>
              </View>
            ) : (
              <View style={{ flexDirection: 'row', gap: 8 }}>
                <Button c={c} variant="quiet" label="Cancel" onPress={() => setShowConfirmModal(false)} style={{ flex: 1 }} />
                <Button c={c} variant="brass" label="Merge" onPress={executeMerge} style={{ flex: 1 }} />
              </View>
            )}
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

const st = StyleSheet.create({
  search: { flexDirection: 'row', alignItems: 'center', gap: S.s, borderWidth: StyleSheet.hairlineWidth, borderRadius: R.control, paddingHorizontal: S.m, marginTop: S.xl },
  del: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  moreBtn: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  rowContainer: { flexDirection: 'row', alignItems: 'center', paddingVertical: 2, paddingHorizontal: 4 },
  mergeHeaderBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6 },
  mergeBanner: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: R.control, padding: S.m, marginTop: S.m },
  badgeTapArea: { paddingHorizontal: 8, paddingVertical: 12, justifyContent: 'center', alignItems: 'center' },
  orderBadge: { width: 32, height: 32, borderRadius: 16, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center' },
  orderBadgeText: { fontFamily: F.readBold, fontSize: 15, fontWeight: '700' },
  orderBadgeSmall: { width: 24, height: 24, borderRadius: 12, alignItems: 'center', justifyContent: 'center', marginRight: 8 },
  orderBadgeSmallText: { fontSize: 12, fontWeight: '700' },
  floatingBar: { position: 'absolute', bottom: 16, left: 16, right: 16, flexDirection: 'row', alignItems: 'center', borderWidth: 1.5, borderRadius: R.panel, padding: S.m, elevation: 8, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 10 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: S.m },
  actionSheet: { width: '100%', maxWidth: 440, borderRadius: R.panel, borderWidth: 1, padding: S.l },
  sheetTitle: { fontSize: 16, marginBottom: 4 },
  sheetItem: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 12 },
  sheetItemText: { fontSize: 15 },
  sheetCancelBtn: { marginTop: S.m, paddingVertical: 10, borderWidth: 1, borderRadius: R.control, alignItems: 'center' },
  confirmCard: { width: '100%', maxWidth: 480, borderRadius: R.panel, borderWidth: 1.5, padding: S.l },
  confirmRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6, borderBottomWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(0,0,0,0.06)' },
});
