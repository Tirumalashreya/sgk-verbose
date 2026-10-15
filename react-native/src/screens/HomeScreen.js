// Home — three ways in (record, upload, link) and recent pravachanams.
import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, TextInput, Pressable, RefreshControl, StyleSheet } from 'react-native';
import { useTheme, F, T, S, R, ACHARYA_TE, ACHARYA } from '../theme';
import { Screen, Enter, ActionTile, SessionRow, Portrait, Overline, Button } from '../ui/kit';
import { getSessions } from '../services/api';
import { pickAudioFile } from '../services/platform';

const isTe = (s) => /[ఀ-౿]/.test(s || '');

export default function HomeScreen({ go, t, lang, setLang, upload }) {
  const c = useTheme();
  const [sessions, setSessions] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);
  const [url, setUrl] = useState('');

  const load = useCallback(async () => {
    try { setSessions(((await getSessions()).sessions || []).slice().reverse()); } catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const busy = upload && ['uploading', 'processing'].includes(upload.status);
  const onUpload = async () => {
    if (busy) return go('live');                       // show the upload already running
    const f = await pickAudioFile();
    if (f) go('live', { upload: f });
  };
  const onLink = () => {
    const u = url.trim();
    if (!/^https?:\/\//i.test(u)) return;
    setUrl(''); setLinkOpen(false);
    go('live', { link: u });
  };

  return (
    <Screen c={c} kolam={c.mode === 'hall'}
      refreshControl={<RefreshControl refreshing={refreshing} tintColor={c.brass}
        onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}>
      <Enter style={st.header}>
        <Portrait c={c} size={46} />
        <View style={{ flex: 1 }}>
          <Text style={[lang === 'te' ? T.displayTe : T.title, { color: c.ink, fontSize: lang === 'te' ? 24 : 22 }]}>{t('appName')}</Text>
          <Text style={[{ fontFamily: F.read, fontSize: 12.5, lineHeight: 20 }, { color: c.muted }]} numberOfLines={1}>{lang === 'te' ? ACHARYA_TE : ACHARYA}</Text>
        </View>
        <Pressable onPress={() => setLang(lang === 'te' ? 'en' : 'te')} accessibilityRole="button"
          accessibilityLabel={lang === 'te' ? 'Switch to English' : 'తెలుగుకు మార్చండి'}
          style={[st.lang, { borderColor: c.line, backgroundColor: c.surface }]}>
          <Text style={{ fontFamily: lang === 'te' ? F.uiSemi : F.readMed, fontSize: 14, color: c.brass }}>{lang === 'te' ? 'EN' : 'తె'}</Text>
        </Pressable>
      </Enter>

      <Enter delay={60}>
        <Text style={[lang === 'te' ? T.displayTe : T.display, { color: c.ink, marginTop: S.x3 }]}>{t('greeting')}</Text>
        <Text style={[isTe(t('homeIntro')) ? { fontFamily: F.read, fontSize: 15, lineHeight: 27 } : T.body, { color: c.inkSoft, marginTop: S.s, maxWidth: 560 }]}>{t('homeIntro')}</Text>
      </Enter>

      <View style={{ gap: S.m, marginTop: S.xxl }}>
        <Enter delay={120}><ActionTile c={c} hero icon="mic" title={t('record')} hint={t('recordHint')} onPress={() => go('live')} /></Enter>
        <Enter delay={170}>
          <ActionTile c={c} icon="upload" title={t('upload')} hint={t('uploadHint')} onPress={onUpload}
            busy={busy ? `${upload.status === 'uploading' ? '…' : t('uploaded')} · ${upload.name}` : null} />
        </Enter>
        <Enter delay={220}>
          {!linkOpen ? (
            <ActionTile c={c} icon="link" title={t('link')} hint={t('linkHint')} onPress={() => setLinkOpen(true)} />
          ) : (
            <View style={[st.linkBox, { backgroundColor: c.surface, borderColor: c.brass }]}>
              <TextInput value={url} onChangeText={setUrl} placeholder={t('linkPlaceholder')} placeholderTextColor={c.muted}
                autoFocus autoCapitalize="none" autoCorrect={false} keyboardType="url" returnKeyType="go" onSubmitEditing={onLink}
                style={[T.body, st.input, { color: c.ink, borderColor: c.line, backgroundColor: c.bg }]} accessibilityLabel={t('link')} />
              <View style={{ flexDirection: 'row', gap: S.s }}>
                <Button c={c} variant="quiet" label={t('cancel')} onPress={() => { setLinkOpen(false); setUrl(''); }} style={{ flex: 1 }} />
                <Button c={c} variant="brass" label={t('start')} onPress={onLink} disabled={!/^https?:\/\//i.test(url.trim())} style={{ flex: 1 }} />
              </View>
            </View>
          )}
        </Enter>
      </View>

      <Enter delay={280} style={{ marginTop: S.x4 }}>
        <View style={st.sectionHead}>
          <Overline c={c}>{t('recent')}</Overline>
          {sessions.length > 3 && (
            <Pressable onPress={() => go('history')} hitSlop={10} accessibilityRole="link">
              <Text style={[T.label, { color: c.brass }]}>{t('seeAll')}</Text>
            </Pressable>
          )}
        </View>
        {sessions.length === 0 ? (
          <Text style={[T.body, { color: c.muted, paddingVertical: S.l }]}>{t('emptyLibrary')}</Text>
        ) : sessions.slice(0, 3).map((s, i, arr) => (
          <SessionRow key={s.id || i} c={c} t={t} session={s} divider={i < arr.length - 1} onPress={() => go('reading', { session: s })} />
        ))}
      </Enter>
    </Screen>
  );
}

const st = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: S.m },
  lang: { width: 44, height: 44, borderRadius: 22, borderWidth: 1, alignItems: 'center', justifyContent: 'center' },
  linkBox: { borderWidth: 1, borderRadius: R.panel, padding: S.l, gap: S.m },
  input: { minHeight: 48, borderWidth: 1, borderRadius: R.control, paddingHorizontal: S.m },
  sectionHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: S.s },
});
