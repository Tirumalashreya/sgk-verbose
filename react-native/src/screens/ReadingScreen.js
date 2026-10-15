// Reading — the complete verbatim notes, calm and legible. Follows the phone's
// light/dark setting (Manuscript by day, Hall at night).
import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme, F, T, S, R } from '../theme';
import { Screen, Enter, IconButton, Chip, Overline, ReadingText, VerseBlock, sessionStatus } from '../ui/kit';
import { getSessions } from '../services/api';
import { downloadPDF, downloadDOC } from '../services/download';
import { notify } from '../services/platform';

const isTe = (s) => /[ఀ-౿]/.test(s || '');

export default function ReadingScreen({ go, back, t, session: given }) {
  const c = useTheme();
  const [session, setSession] = useState(given || null);
  const [tab, setTab] = useState('notes');
  const [showReview, setShowReview] = useState(false);

  useEffect(() => {
    if (given) { setSession(given); return; }
    getSessions().then((d) => { const l = d.sessions || []; setSession(l[l.length - 1] || null); }).catch(() => {});
  }, [given]);

  if (!session) {
    return (
      <Screen c={c}>
        <Text style={[T.body, { color: c.muted, marginTop: S.x4, textAlign: 'center' }]}>{t('emptyLibrary')}</Text>
      </Screen>
    );
  }

  const shlokas = session.shlokas || [];
  const uncertain = session.asr_report?.uncertain || [];
  const review = sessionStatus(session) === 'review';
  const date = session.created_at ? new Date(session.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' }) : '';
  const exportAs = async (kind) => {
    try { await (kind === 'pdf' ? downloadPDF(session) : downloadDOC(session)); }
    catch (e) { notify(kind.toUpperCase(), String(e.message || e)); }
  };
  const tabs = [['notes', t('notes')], ['roman', t('roman')], ['verses', `${t('versesTab')} · ${shlokas.length}`]];

  return (
    <Screen c={c}>
      <View style={st.bar}>
        <IconButton c={c} icon="back" label={t('back')} onPress={() => back() || go('history')} />
        <View style={{ flexDirection: 'row' }}>
          <Pressable onPress={() => exportAs('pdf')} accessibilityRole="button" accessibilityLabel={`${t('exportPdf')} export`} style={st.export}>
            <Text style={[T.label, { color: c.brass }]}>{t('exportPdf')}</Text>
          </Pressable>
          <Pressable onPress={() => exportAs('doc')} accessibilityRole="button" accessibilityLabel={`${t('exportDoc')} export`} style={st.export}>
            <Text style={[T.label, { color: c.brass }]}>{t('exportDoc')}</Text>
          </Pressable>
        </View>
      </View>

      <Enter>
        <Text selectable style={[isTe(session.title) ? T.displayTe : T.display, { color: c.ink, marginTop: S.s }]}>{session.title || 'Pravachanam'}</Text>
        <View style={st.meta}>
          <Text style={[T.body, { color: c.muted, fontSize: 13.5 }]}>{date}{shlokas.length ? ` · ${shlokas.length} ${t('verses')}` : ''}</Text>
          {!review && <Chip c={c} tone="ok" icon="check">{t('ready')}</Chip>}
        </View>
      </Enter>

      {review && (
        <Pressable onPress={() => setShowReview((v) => !v)} accessibilityRole="button" accessibilityState={{ expanded: showReview }}
          style={[st.review, { borderColor: c.review, backgroundColor: c.surface }]}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.s }}>
            <Chip c={c} tone="review" icon="alert">{uncertain.length ? t('reviewSpots')(uncertain.length) : t('needsReview')}</Chip>
          </View>
          <Text style={[isTe(t('reviewHint')) ? { fontFamily: F.read, fontSize: 14, lineHeight: 24 } : T.body, { color: c.inkSoft, marginTop: S.s }]}>{t('reviewHint')}</Text>
          {showReview && uncertain.map((u, i) => (
            <View key={i} style={[st.spot, { borderTopColor: c.line }]}>
              <Text style={[T.read, { color: c.muted, fontSize: 14, lineHeight: 24 }]}>…{u.context}…</Text>
              <Text style={[T.read, { color: c.ink, fontSize: 15 }]}><Text style={[T.caption, { color: c.brass }]}>A  </Text>{u.sarvam || '—'}</Text>
              <Text style={[T.read, { color: c.ink, fontSize: 15 }]}><Text style={[T.caption, { color: c.brass }]}>B  </Text>{u.gemini || '—'}</Text>
            </View>
          ))}
        </Pressable>
      )}

      {!!session.summary && (
        <View style={[st.summary, { borderColor: c.line }]}>
          <Overline c={c}>{t('summary')}</Overline>
          <Text selectable style={[T.read, { color: c.inkSoft, fontSize: 15.5, lineHeight: 29, marginTop: S.s }]}>{session.summary}</Text>
        </View>
      )}

      <View style={[st.tabs, { borderColor: c.line, backgroundColor: c.surface }]} accessibilityRole="tablist">
        {tabs.map(([id, label]) => {
          const on = tab === id;
          return (
            <Pressable key={id} onPress={() => setTab(id)} accessibilityRole="tab" accessibilityState={{ selected: on }}
              style={[st.tab, on && { backgroundColor: c.raised, borderColor: c.brass }]}>
              <Text style={[isTe(label) ? { fontFamily: F.readMed, fontSize: 14 } : T.label, { color: on ? c.ink : c.muted }]}>{label}</Text>
            </Pressable>
          );
        })}
      </View>

      <View style={{ marginTop: S.xl }}>
        {tab === 'notes' && <ReadingText c={c} notes={session.notes || session.transcript} shlokas={shlokas} />}
        {tab === 'roman' && <ReadingText c={c} notes={session.transliterated_notes || ''} shlokas={shlokas} roman />}
        {tab === 'verses' && (shlokas.length === 0
          ? <Text style={[T.body, { color: c.muted }]}>{t('noVerses')}</Text>
          : <View style={{ gap: S.m }}>{shlokas.map((s, i) => (
              <VerseBlock key={i} c={c} text={s.text} original={s.original} type={s.type}
                reference={s.reference ? `నాలాయిర దివ్య ప్రబంధం ${s.reference.number}` : null} />
            ))}</View>)}
      </View>
    </Screen>
  );
}

const st = StyleSheet.create({
  bar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginHorizontal: -S.s },
  export: { minWidth: 52, height: 44, alignItems: 'center', justifyContent: 'center', paddingHorizontal: S.s },
  meta: { flexDirection: 'row', alignItems: 'center', gap: S.s, marginTop: S.s, flexWrap: 'wrap' },
  review: { marginTop: S.xl, borderWidth: 1, borderRadius: R.panel, padding: S.l },
  spot: { borderTopWidth: StyleSheet.hairlineWidth, marginTop: S.m, paddingTop: S.m, gap: 4 },
  summary: { marginTop: S.xl, borderLeftWidth: 2, paddingLeft: S.l, paddingVertical: S.xs },
  tabs: { flexDirection: 'row', marginTop: S.xxl, borderWidth: StyleSheet.hairlineWidth, borderRadius: R.control, padding: 4 },
  tab: { flex: 1, minHeight: 40, borderRadius: R.control - 2, borderWidth: 1, borderColor: 'transparent', alignItems: 'center', justifyContent: 'center' },
});
