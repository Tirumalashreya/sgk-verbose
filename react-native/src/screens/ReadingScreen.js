// Reading — the complete verbatim notes, calm and legible. Follows the phone's
// light/dark setting (Manuscript by day, Hall at night).
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, Pressable, TextInput, StyleSheet } from 'react-native';
import Sanscript from '@indic-transliteration/sanscript';
import { useTheme, F, T, S, R } from '../theme';
import Icon from '../ui/Icon';
import { Screen, Enter, IconButton, Chip, Button, ReadingText, VerseBlock, sessionStatus, ExportDialog } from '../ui/kit';
import { getSessions, getTimestampedNotes, updateNotes, updateSessionTitle, downloadSessionAudio } from '../services/api';
import { downloadPDF, downloadDOC } from '../services/download';
import { notify } from '../services/platform';

const isTe = (s) => /[ఀ-౿]/.test(s || '');

const CASUAL_WORDS = {
  namaskaram: 'నమస్కారం',
  namaskaralu: 'నమస్కారాలు',
  swami: 'స్వామి',
  swamy: 'స్వామి',
  acharya: 'ఆచార్య',
  acharyulu: 'ఆచార్యులు',
  pravachanam: 'ప్రవచనం',
  shloka: 'శ్లోకం',
  shlokam: 'శ్లోకం',
  shlokalu: 'శ్లోకాలు',
  ramanuja: 'రామానుజ',
  krishna: 'కృష్ణ',
  rama: 'రామ',
  govinda: 'గోవింద',
  venkateshwara: 'వేంకటేశ్వర',
  venkateswara: 'వేంకటేశ్వర',
  sri: 'శ్రీ',
  shri: 'శ్రీ',
  shree: 'శ్రీ',
  guru: 'గురు',
  guruvu: 'గురువు',
  bhagavan: 'భగవాన్',
  bhagavanthudu: 'భగవంతుడు',
  devudu: 'దేవుడు',
  telugu: 'తెలుగు',
  namaste: 'నమస్తే',
};

function transliterateWord(w) {
  if (!w || !/^[a-zA-Z]+$/.test(w)) return w;
  const lower = w.toLowerCase();
  if (CASUAL_WORDS[lower]) return CASUAL_WORDS[lower];
  try {
    const itrans = lower
      .replace(/aa/g, 'A')
      .replace(/ee/g, 'I')
      .replace(/oo/g, 'U');
    return Sanscript.t(itrans, 'itrans', 'telugu') || w;
  } catch {
    return w;
  }
}

export default function ReadingScreen({ go, back, t, session: given }) {
  const c = useTheme();
  const [session, setSession] = useState(given || null);
  const [tab, setTab] = useState('notes');
  const [showReview, setShowReview] = useState(false);
  // 'idle' | 'loading' | 'ready' | 'unavailable' | 'error'
  const [tsStatus, setTsStatus] = useState('idle');
  const [tsNotes, setTsNotes] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [selection, setSelection] = useState({ start: 0, end: 0 });
  const [teluguAidOn, setTeluguAidOn] = useState(false);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);
  const [romanInput, setRomanInput] = useState('');
  const [exportKind, setExportKind] = useState(null);   // 'pdf' | 'doc' | null (dialog closed)

  const teluguPreview = useMemo(() => {
    if (!romanInput.trim()) return '';
    return transliterateWord(romanInput.trim());
  }, [romanInput]);

  const onDraftChange = (text) => {
    if (!teluguAidOn) {
      setDraft(text);
      return;
    }
    const match = text.match(/([a-zA-Z]+)(\s)$/);
    if (match) {
      const converted = transliterateWord(match[1]);
      const replaced = text.slice(0, -match[0].length) + converted + match[2];
      setDraft(replaced);
      return;
    }
    setDraft(text);
  };

  const toggleVoice = () => {
    if (listening) {
      recognitionRef.current?.stop?.();
      setListening(false);
      return;
    }
    const SpeechRecognition = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);
    if (!SpeechRecognition) {
      notify(t('edit'), t('teluguVoiceUnsupported'));
      return;
    }
    try {
      const rec = new SpeechRecognition();
      rec.lang = 'te-IN';
      rec.continuous = false;
      rec.interimResults = false;
      rec.onstart = () => setListening(true);
      rec.onresult = (event) => {
        const spoken = event.results?.[0]?.[0]?.transcript;
        if (spoken) {
          const insert = spoken + ' ';
          setDraft((prev) => {
            const start = selection.start || prev.length;
            const end = selection.end || prev.length;
            const next = prev.slice(0, start) + insert + prev.slice(end);
            setSelection({ start: start + insert.length, end: start + insert.length });
            return next;
          });
        }
      };
      rec.onerror = () => setListening(false);
      rec.onend = () => setListening(false);
      recognitionRef.current = rec;
      rec.start();
    } catch {
      setListening(false);
    }
  };

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
  // sessionStatus() only returns 'review' for a real two-listener
  // disagreement now (an ASR gap or low confidence score no longer counts),
  // so the hint can safely always describe that one real situation.
  const review = sessionStatus(session) === 'review';
  const reviewHint = t('reviewHint');
  const date = session.created_at ? new Date(session.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' }) : '';

  const loadTimestamps = async () => {
    if (tsStatus === 'loading' || tsStatus === 'ready') return;
    setTsStatus('loading');
    try {
      const notes = await getTimestampedNotes(session.id);
      setTsNotes(notes);
      setTsStatus('ready');
    } catch (e) {
      setTsStatus(String(e.message) === 'unavailable' ? 'unavailable' : 'error');
    }
  };
  const selectTab = (id) => { setTab(id); if (id === 'timestamps') loadTimestamps(); };

  const startEdit = () => {
    setDraft(session.notes || session.transcript || '');
    setTitleDraft(session.title || '');
    setEditing(true);
    setTeluguAidOn(false);
    setRomanInput('');
  };
  const cancelEdit = () => { setEditing(false); setTeluguAidOn(false); setRomanInput(''); };
  const saveEdit = async () => {
    setSaving(true);
    try {
      const cleanTitle = titleDraft.trim() || session.title;
      await updateNotes(session.id, draft, cleanTitle);
      setSession((s) => ({ ...s, title: cleanTitle, notes: draft, enhanced_notes: draft, edited: true }));
      setTsStatus('idle'); setTsNotes(null);   // the cached timestamped version no longer matches
      setEditing(false); setTeluguAidOn(false); setRomanInput('');
    } catch (e) {
      notify(t('edit'), String(e.message) || t('editFailed'));
    } finally {
      setSaving(false);
    }
  };

  const saveTitle = async () => {
    const cleanTitle = titleDraft.trim();
    if (!cleanTitle) return;
    try {
      await updateSessionTitle(session.id, cleanTitle);
      setSession((s) => ({ ...s, title: cleanTitle, edited: true }));
      setRenaming(false);
    } catch (e) {
      notify(t('editTitle'), String(e.message || e));
    }
  };
  // Inserts the live Telugu preview at wherever the cursor last was in the
  // notes box, then moves the cursor past what it just inserted — so typing
  // word after word in the aid reads naturally into the real notes.
  const insertTelugu = () => {
    if (!teluguPreview) return;
    const insert = teluguPreview + ' ';
    const { start, end } = selection;
    const next = draft.slice(0, start) + insert + draft.slice(end);
    const caret = start + insert.length;
    setDraft(next);
    setSelection({ start: caret, end: caret });
    setRomanInput('');
  };

  const [audioLoading, setAudioLoading] = useState(false);

  const handleAudioDownload = async () => {
    if (audioLoading) return;
    setAudioLoading(true);
    notify(t('downloadAudio'), t('audioDownloading'));
    try {
      await downloadSessionAudio(session.id, session.title);
    } catch (e) {
      notify(t('downloadAudio'), t('audioError'));
    } finally {
      setAudioLoading(false);
    }
  };

  const exportAs = (kind) => setExportKind(kind);   // opens the dialog; the actual download happens on Generate

  const handleExportGenerate = async ({ fileName, withTimestamps }) => {
    const kind = exportKind;
    setExportKind(null);
    let toExport = session;
    if (withTimestamps) {
      try {
        const notes = tsStatus === 'ready' && tsNotes ? tsNotes : await getTimestampedNotes(session.id);
        toExport = { ...session, notes };
      } catch (e) {
        notify(kind.toUpperCase(), String(e.message) === 'unavailable' ? t('timestampsUnavailable') : String(e.message || e));
        return;
      }
    }
    try { await (kind === 'pdf' ? downloadPDF(toExport, fileName) : downloadDOC(toExport, fileName)); }
    catch (e) { notify(kind.toUpperCase(), String(e.message || e)); }
  };
  const tabs = [['notes', t('notes')], ['verses', `${t('versesTab')} · ${shlokas.length}`],
    ['timestamps', t('timestampsTab')]];

  return (
    <Screen c={c}>
      <View style={st.bar}>
        <IconButton c={c} icon="back" label={t('back')} onPress={() => (editing ? cancelEdit() : (back() || go('history')))} />
        <View style={{ flexDirection: 'row' }}>
          {tab === 'notes' && !editing && (
            <Pressable onPress={startEdit} accessibilityRole="button" accessibilityLabel={`${t('edit')} ${t('notes')}`} style={st.export}>
              <Text style={[T.label, { color: c.brass }]}>{t('edit')}</Text>
            </Pressable>
          )}
          {!editing && <>
            <Pressable onPress={() => exportAs('pdf')} accessibilityRole="button" accessibilityLabel={`${t('exportPdf')} export`} style={st.export}>
              <Text style={[T.label, { color: c.brass }]}>{t('exportPdf')}</Text>
            </Pressable>
            <Pressable onPress={() => exportAs('doc')} accessibilityRole="button" accessibilityLabel={`${t('exportDoc')} export`} style={st.export}>
              <Text style={[T.label, { color: c.brass }]}>{t('exportDoc')}</Text>
            </Pressable>
            <Pressable onPress={handleAudioDownload} accessibilityRole="button" accessibilityLabel="Download Audio" style={st.export} disabled={audioLoading}>
              <Text style={[T.label, { color: c.brass }]}>{audioLoading ? '…' : t('downloadAudio')}</Text>
            </Pressable>
          </>}
        </View>
      </View>

      <Enter>
        {renaming ? (
          <View style={{ marginTop: S.s, marginBottom: S.s }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.s }}>
              <TextInput
                value={titleDraft}
                onChangeText={setTitleDraft}
                autoFocus
                placeholder={t('titlePlaceholder')}
                placeholderTextColor={c.muted}
                style={[
                  isTe(titleDraft) ? T.displayTe : T.display,
                  {
                    flex: 1,
                    color: c.ink,
                    borderBottomWidth: 1.5,
                    borderColor: c.brass,
                    paddingVertical: 4,
                  },
                ]}
              />
              <Pressable
                onPress={saveTitle}
                hitSlop={8}
                style={{
                  paddingHorizontal: 12,
                  paddingVertical: 6,
                  borderRadius: R.control,
                  backgroundColor: c.brass,
                }}
              >
                <Text style={[T.label, { color: '#fff', fontSize: 13 }]}>{t('editSave')}</Text>
              </Pressable>
              <Pressable
                onPress={() => setRenaming(false)}
                hitSlop={8}
                style={{
                  paddingHorizontal: 8,
                  paddingVertical: 6,
                }}
              >
                <Icon name="close" size={18} color={c.muted} />
              </Pressable>
            </View>
          </View>
        ) : editing ? (
          <View style={{ marginTop: S.s, marginBottom: S.m }}>
            <Text style={[T.caption, { color: c.muted, marginBottom: 4 }]}>{t('editTitle')}</Text>
            <TextInput
              value={titleDraft}
              onChangeText={setTitleDraft}
              placeholder={t('titlePlaceholder')}
              placeholderTextColor={c.muted}
              style={[
                isTe(titleDraft) ? T.displayTe : T.display,
                {
                  color: c.ink,
                  borderBottomWidth: 1.5,
                  borderColor: c.brass,
                  paddingVertical: 4,
                },
              ]}
            />
          </View>
        ) : (
          <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: S.s, gap: S.s, flexWrap: 'wrap' }}>
            <Text selectable style={[isTe(session.title) ? T.displayTe : T.display, { color: c.ink, flexShrink: 1 }]}>
              {session.title || 'Pravachanam'}
            </Text>
            <Pressable
              onPress={() => { setTitleDraft(session.title || ''); setRenaming(true); }}
              accessibilityRole="button"
              accessibilityLabel={t('editTitle')}
              hitSlop={8}
              style={{ padding: 4 }}
            >
              <Icon name="edit" size={18} color={c.brass} />
            </Pressable>
          </View>
        )}
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
          <Text style={[isTe(reviewHint) ? { fontFamily: F.read, fontSize: 14, lineHeight: 24 } : T.body, { color: c.inkSoft, marginTop: S.s }]}>{reviewHint}</Text>
          {showReview && uncertain.map((u, i) => (
            <View key={i} style={[st.spot, { borderTopColor: c.line }]}>
              <Text style={[T.read, { color: c.muted, fontSize: 14, lineHeight: 24 }]}>…{u.context}…</Text>
              <Text style={[T.read, { color: c.ink, fontSize: 15 }]}><Text style={[T.caption, { color: c.brass }]}>A  </Text>{u.sarvam || '—'}</Text>
              <Text style={[T.read, { color: c.ink, fontSize: 15 }]}><Text style={[T.caption, { color: c.brass }]}>B  </Text>{u.gemini || '—'}</Text>
            </View>
          ))}
        </Pressable>
      )}

      <View style={[st.tabs, { borderColor: c.line, backgroundColor: c.surface }]} accessibilityRole="tablist">
        {tabs.map(([id, label]) => {
          const on = tab === id;
          return (
            <Pressable key={id} onPress={() => selectTab(id)} accessibilityRole="tab" accessibilityState={{ selected: on }}
              style={[st.tab, on && { backgroundColor: c.raised, borderColor: c.brass }]}>
              <Text style={[isTe(label) ? { fontFamily: F.readMed, fontSize: 14 } : T.label, { color: on ? c.ink : c.muted }]}>{label}</Text>
            </Pressable>
          );
        })}
      </View>

      <View style={{ marginTop: S.xl }}>
        {tab === 'notes' && editing && (
          <View style={{ gap: S.m }}>
            <TextInput
              value={draft}
              onChangeText={onDraftChange}
              onSelectionChange={(e) => setSelection(e.nativeEvent.selection)}
              selection={selection}
              multiline
              autoFocus
              autoCorrect={false}
              autoCapitalize="none"
              spellCheck={false}
              lang="te"
              accessibilityLabel={t('notes')}
              style={[T.read, st.editInput, { color: c.ink, borderColor: c.brass, backgroundColor: c.surface }]}
            />
            <View style={{ flexDirection: 'row', gap: S.s }}>
              <Pressable onPress={() => setTeluguAidOn((v) => !v)} accessibilityRole="button" accessibilityState={{ selected: teluguAidOn }}
                style={[st.aidToggle, { borderColor: c.brass, backgroundColor: teluguAidOn ? c.brass : 'transparent', flex: 1, paddingVertical: 10 }]}>
                <Text style={[T.label, { color: teluguAidOn ? c.onBrass : c.brass, textAlign: 'center' }]}>
                  {teluguAidOn ? '✓ ' + t('teluguAid') : t('teluguAid')}
                </Text>
              </Pressable>
              <Pressable onPress={toggleVoice} accessibilityRole="button"
                style={[st.aidToggle, { borderColor: listening ? c.kumkum : c.brass, backgroundColor: listening ? c.kumkum : 'transparent', flex: 1, paddingVertical: 10 }]}>
                <Text style={[T.label, { color: listening ? '#fff' : c.brass, textAlign: 'center' }]}>
                  {listening ? '🔴 ' + t('teluguVoiceListening') : '🎙️ ' + t('teluguVoice')}
                </Text>
              </Pressable>
            </View>
            {teluguAidOn && (
              <View style={[st.aidPanel, { borderColor: c.line, backgroundColor: c.surface }]}>
                <Text style={[T.body, { color: c.muted, fontSize: 12.5, marginBottom: S.xs }]}>{t('teluguAidHint')}</Text>
                <TextInput
                  value={romanInput}
                  onChangeText={setRomanInput}
                  onSubmitEditing={insertTelugu}
                  blurOnSubmit={false}
                  autoCorrect={false}
                  autoCapitalize="none"
                  spellCheck={false}
                  placeholder={t('teluguAidPlaceholder')}
                  placeholderTextColor={c.muted}
                  accessibilityLabel={t('teluguAid')}
                  style={[T.body, st.aidInput, { color: c.ink, borderColor: c.line, backgroundColor: c.raised }]}
                />
                <View style={[st.aidPreviewRow, { borderColor: c.line }]}>
                  <Text style={[T.read, { color: c.ink, fontSize: 20, flex: 1 }]}>{teluguPreview || ' '}</Text>
                  <Button c={c} variant="brass" label={t('teluguAidInsert')} onPress={insertTelugu} disabled={!teluguPreview} />
                </View>
              </View>
            )}
            <View style={{ flexDirection: 'row', gap: S.s }}>
              <Button c={c} variant="quiet" label={t('editCancel')} onPress={cancelEdit} style={{ flex: 1 }} disabled={saving} />
              <Button c={c} variant="brass" label={saving ? t('editSaved') + '…' : t('editSave')} onPress={saveEdit} style={{ flex: 1 }} disabled={saving} />
            </View>
          </View>
        )}
        {tab === 'notes' && !editing && (
          <View style={{ gap: S.m }}>
            {session.edited && (
              <View style={{ flexDirection: 'row' }}><Chip c={c} tone="ok" icon="check">{t('editedBadge')}</Chip></View>
            )}
            <ReadingText c={c} notes={session.notes || session.transcript} shlokas={shlokas} typeLabel={t('verseType')} headings={session.notes_headings || {}} />
          </View>
        )}
        {tab === 'verses' && (shlokas.length === 0
          ? <Text style={[T.body, { color: c.muted }]}>{t('noVerses')}</Text>
          : <View style={{ gap: S.m }}>{shlokas.map((s, i) => (
              <VerseBlock key={i} c={c} text={s.text} original={s.original} type={t('verseType')(s.type)}
                reference={s.reference ? `నాలాయిర దివ్య ప్రబంధం ${s.reference.number}` : null} />
            ))}</View>)}
        {tab === 'timestamps' && (
          tsStatus === 'loading' ? <Text style={[T.body, { color: c.muted, textAlign: 'center', marginTop: S.xl }]}>{t('timestampsBuilding')}</Text>
          : tsStatus === 'unavailable' ? <Text style={[T.body, { color: c.muted, textAlign: 'center', marginTop: S.xl }]}>{t('timestampsUnavailable')}</Text>
          : tsStatus === 'error' ? <Text style={[T.body, { color: c.kumkumText, textAlign: 'center', marginTop: S.xl }]}>{t('timestampsUnavailable')}</Text>
          : tsStatus === 'ready' ? <ReadingText c={c} notes={tsNotes} shlokas={shlokas} typeLabel={t('verseType')} />
          : null
        )}
      </View>
      <ExportDialog c={c} t={t} visible={!!exportKind} defaultFileName={session.title || 'pravachanam'}
        onCancel={() => setExportKind(null)} onGenerate={handleExportGenerate} />
    </Screen>
  );
}

const st = StyleSheet.create({
  bar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginHorizontal: -S.s },
  export: { minWidth: 52, height: 44, alignItems: 'center', justifyContent: 'center', paddingHorizontal: S.s },
  meta: { flexDirection: 'row', alignItems: 'center', gap: S.s, marginTop: S.s, flexWrap: 'wrap' },
  review: { marginTop: S.xl, borderWidth: 1, borderRadius: R.panel, padding: S.l },
  spot: { borderTopWidth: StyleSheet.hairlineWidth, marginTop: S.m, paddingTop: S.m, gap: 4 },
  tabs: { flexDirection: 'row', marginTop: S.xxl, borderWidth: StyleSheet.hairlineWidth, borderRadius: R.control, padding: 4 },
  tab: { flex: 1, minHeight: 44, borderRadius: R.control - 2, borderWidth: 1, borderColor: 'transparent', alignItems: 'center', justifyContent: 'center' },
  editInput: { minHeight: 320, borderWidth: 1, borderRadius: R.panel, padding: S.l, textAlignVertical: 'top' },
  aidToggle: { alignSelf: 'flex-start', borderWidth: 1, borderRadius: R.pill, paddingHorizontal: S.l, paddingVertical: S.s },
  aidPanel: { borderWidth: 1, borderRadius: R.panel, padding: S.l, gap: S.s },
  aidInput: { borderWidth: 1, borderRadius: R.control, padding: S.m, fontSize: 16 },
  aidPreviewRow: { flexDirection: 'row', alignItems: 'center', gap: S.m, borderTopWidth: StyleSheet.hairlineWidth, paddingTop: S.m },
});
