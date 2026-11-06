// History — every pravachanam, searchable; delete with confirmation.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, TextInput, Pressable, RefreshControl, StyleSheet } from 'react-native';
import { useTheme, F, T, S, R } from '../theme';
import { Screen, Enter, SessionRow, Overline } from '../ui/kit';
import Icon from '../ui/Icon';
import { getSessions, deleteSession, createWebSocket } from '../services/api';
import { confirm } from '../services/platform';

export default function HistoryScreen({ go, t, lang }) {
  const c = useTheme();
  const [sessions, setSessions] = useState([]);
  const [query, setQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);

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

  return (
    <Screen c={c}
      refreshControl={<RefreshControl refreshing={refreshing} tintColor={c.brass}
        onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}>
      <Enter>
        <Text style={[lang === 'te' ? T.displayTe : T.display, { color: c.ink }]}>{t('history')}</Text>
        <Text style={[T.body, { color: c.muted, marginTop: 4 }]}>{sessions.length}</Text>
      </Enter>

      <View style={[st.search, { borderColor: c.line, backgroundColor: c.surface }]}>
        <Icon name="search" size={18} color={c.muted} />
        <TextInput value={query} onChangeText={setQuery} placeholder={t('search')} placeholderTextColor={c.muted}
          style={[T.body, { flex: 1, color: c.ink, minHeight: 44 }]} accessibilityLabel={t('search')} returnKeyType="search" />
      </View>

      <View style={{ marginTop: S.l }}>
        {shown.length === 0 && <Text style={[T.body, { color: c.muted, paddingVertical: S.xl }]}>{t('emptyLibrary')}</Text>}
        {shown.map((s, i) => (
          <View key={s.id || i} style={{ flexDirection: 'row', alignItems: 'center' }}>
            <View style={{ flex: 1 }}>
              <SessionRow c={c} t={t} session={s} divider={i < shown.length - 1}
                onPress={() => go('reading', { session: s })} onLongPress={() => remove(s)} />
            </View>
            <Pressable onPress={() => remove(s)} accessibilityRole="button" accessibilityLabel={`${t('delete')} ${s.title || ''}`}
              hitSlop={6} style={st.del}>
              <Icon name="trash" size={19} color={c.kumkumText} />
            </Pressable>
          </View>
        ))}
      </View>
    </Screen>
  );
}

const st = StyleSheet.create({
  search: { flexDirection: 'row', alignItems: 'center', gap: S.s, borderWidth: StyleSheet.hairlineWidth, borderRadius: R.control, paddingHorizontal: S.m, marginTop: S.xl },
  del: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
});
