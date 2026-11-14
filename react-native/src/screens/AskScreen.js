// Ask — finds the passage in the pravachanams where something was said (search
// over the stored notes). Honest: shows what was found, nothing invented.
import React, { useRef, useState } from 'react';
import { View, Text, TextInput, Pressable, ActivityIndicator, StyleSheet } from 'react-native';
import Sanscript from '@indic-transliteration/sanscript';
import { useTheme, F, T, S, R } from '../theme';
import { Screen, Enter, Button, Overline } from '../ui/kit';
import TeluguKeypad from '../ui/TeluguKeypad';
import { searchRag } from '../services/api';
import { notify } from '../services/platform';

const isTe = (s) => /[ఀ-౿]/.test(s || '');

const CASUAL_WORDS = {
  sri: 'శ్రీ', shri: 'శ్రీ', shree: 'శ్రీ',
  swami: 'స్వామి', swamy: 'స్వామి',
  ramanuja: 'రామానుజ', ramanujulu: 'రామానుజులు',
  saranagati: 'శరణాగతి', sharanagati: 'శరణాగతి',
  gadyam: 'గద్యం',
  bhagavan: 'భగవాన్', bhagavanthudu: 'భగవంతుడు',
  namaskaram: 'నమస్కారం', namaste: 'నమస్తే',
  pravachanam: 'ప్రవచనం', pravachanams: 'ప్రవచనాలు',
  vedantam: 'వేదాంతం', veda: 'వేద', vedam: 'వేదం',
  bhakti: 'భక్తి', gnana: 'జ్ఞాన', jnana: 'జ్ఞాన',
  shloka: 'శ్లోకం', sloka: 'శ్లోకం',
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

export default function AskScreen({ t, lang }) {
  const c = useTheme();
  const [q, setQ] = useState('');
  const [selection, setSelection] = useState({ start: 0, end: 0 });
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState([]);   // [{ question, passage }]

  // Telugu input aids
  const [teluguAidOn, setTeluguAidOn] = useState(true);  // on by default so typing "saranagati " auto-converts
  const [showKeypad, setShowKeypad] = useState(false);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);

  const onQueryChange = (text) => {
    if (!teluguAidOn) {
      setQ(text);
      return;
    }
    const match = text.match(/([a-zA-Z]+)(\s)$/);
    if (match) {
      const englishWord = match[1];
      const space = match[2];
      const teluguWord = transliterateWord(englishWord);
      const converted = text.slice(0, match.index) + teluguWord + space;
      setQ(converted);
      return;
    }
    setQ(text);
  };

  const insertKeypadChar = (char) => {
    const start = selection.start ?? q.length;
    const end = selection.end ?? q.length;
    const before = q.slice(0, start);
    const after = q.slice(end);
    const nextText = before + char + after;
    const nextPos = start + char.length;
    setQ(nextText);
    setSelection({ start: nextPos, end: nextPos });
  };

  const backspaceKeypad = () => {
    const start = selection.start ?? q.length;
    const end = selection.end ?? q.length;
    if (start !== end) {
      const nextText = q.slice(0, start) + q.slice(end);
      setQ(nextText);
      setSelection({ start, end: start });
      return;
    }
    if (start === 0) return;
    const before = q.slice(0, start - 1);
    const after = q.slice(end);
    setQ(before + after);
    setSelection({ start: start - 1, end: start - 1 });
  };

  const toggleVoice = () => {
    if (listening) {
      recognitionRef.current?.stop?.();
      setListening(false);
      return;
    }
    const SpeechRec = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);
    if (!SpeechRec) {
      notify(t('ask'), 'Voice typing is not supported in this browser.');
      return;
    }
    try {
      const rec = new SpeechRec();
      rec.lang = 'te-IN';
      rec.continuous = false;
      rec.interimResults = false;
      setListening(true);
      rec.onresult = (e) => {
        const transcript = e.results?.[0]?.[0]?.transcript;
        if (transcript) {
          setQ((prev) => (prev ? prev + ' ' + transcript : transcript));
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

  const ask = async () => {
    const question = q.trim();
    if (!question || busy) return;
    setBusy(true);
    try {
      const { result } = await searchRag(question);
      const found = result && !/^No relevant information/i.test(result);
      setResults((r) => [{ question, passage: found ? result : null }, ...r]);
      setQ('');
    } catch {
      setResults((r) => [{ question, passage: null }, ...r]);
    } finally { setBusy(false); }
  };

  return (
    <Screen c={c}>
      <Enter>
        <Text style={[lang === 'te' ? T.displayTe : T.display, { color: c.ink }]}>{t('askTitle')}</Text>
        <Text style={[isTe(t('askHint')) ? { fontFamily: F.read, fontSize: 15, lineHeight: 26 } : T.body, { color: c.inkSoft, marginTop: S.s }]}>{t('askHint')}</Text>
      </Enter>

      <View style={[st.box, { borderColor: c.brass, backgroundColor: c.surface }]}>
        <TextInput
          value={q}
          onChangeText={onQueryChange}
          onSelectionChange={(e) => setSelection(e.nativeEvent.selection)}
          selection={selection}
          placeholder={t('askPlaceholder')}
          placeholderTextColor={c.muted}
          multiline
          style={[isTe(q) ? { fontFamily: F.read, fontSize: 16, lineHeight: 28 } : T.body, st.input, { color: c.ink }]}
          accessibilityLabel={t('askTitle')}
          onSubmitEditing={ask}
          blurOnSubmit
          returnKeyType="search"
        />

        {/* Telugu Typing Aids Bar */}
        <View style={{ flexDirection: 'row', gap: S.s, flexWrap: 'wrap' }}>
          <Pressable
            onPress={() => setTeluguAidOn((v) => !v)}
            accessibilityRole="button"
            accessibilityState={{ selected: teluguAidOn }}
            style={[st.aidToggle, { borderColor: c.brass, backgroundColor: teluguAidOn ? c.brass : 'transparent', flex: 1, minWidth: 100, paddingVertical: 8 }]}
          >
            <Text style={[T.label, { color: teluguAidOn ? c.onBrass : c.brass, textAlign: 'center', fontSize: 12 }]}>
              {teluguAidOn ? '✓ ' + t('teluguAid') : t('teluguAid')}
            </Text>
          </Pressable>

          <Pressable
            onPress={() => setShowKeypad((v) => !v)}
            accessibilityRole="button"
            accessibilityState={{ selected: showKeypad }}
            style={[st.aidToggle, { borderColor: c.brass, backgroundColor: showKeypad ? c.brass : 'transparent', flex: 1, minWidth: 120, paddingVertical: 8 }]}
          >
            <Text style={[T.label, { color: showKeypad ? c.onBrass : c.brass, textAlign: 'center', fontSize: 12 }]}>
              {showKeypad ? '✓ తెలుగు కీబోర్డ్' : '⌨️ తెలుగు కీబోర్డ్'}
            </Text>
          </Pressable>

          <Pressable
            onPress={toggleVoice}
            accessibilityRole="button"
            style={[st.aidToggle, { borderColor: listening ? c.kumkum : c.brass, backgroundColor: listening ? c.kumkum : 'transparent', flex: 1, minWidth: 90, paddingVertical: 8 }]}
          >
            <Text style={[T.label, { color: listening ? '#fff' : c.brass, textAlign: 'center', fontSize: 12 }]}>
              {listening ? '🔴 ' + t('teluguVoiceListening') : '🎙️ ' + t('teluguVoice')}
            </Text>
          </Pressable>
        </View>

        {showKeypad && (
          <TeluguKeypad onInsert={insertKeypadChar} onBackspace={backspaceKeypad} onClose={() => setShowKeypad(false)} />
        )}

        <Button c={c} variant="brass" icon="search" label={t('ask')} onPress={ask} disabled={!q.trim() || busy} />
      </View>

      {busy && <ActivityIndicator color={c.brass} style={{ marginTop: S.xl }} />}

      <View style={{ marginTop: S.xl, gap: S.xl }}>
        {results.map((r, i) => (
          <Enter key={results.length - i}>
            <Text style={[isTe(r.question) ? T.titleTe : T.title, { color: c.ink, fontSize: 18 }]}>{r.question}</Text>
            {r.passage ? (
              <View style={[st.passage, { borderLeftColor: c.brass }]}>
                <Overline c={c}>{t('fromNotes')}</Overline>
                <Text selectable style={[T.read, { color: c.ink, marginTop: S.s }]}>{r.passage}</Text>
              </View>
            ) : (
              <Text style={[T.body, { color: c.muted, marginTop: S.s }]}>{t('askNothing')}</Text>
            )}
          </Enter>
        ))}
      </View>
    </Screen>
  );
}

const st = StyleSheet.create({
  box: { marginTop: S.xl, borderWidth: 1, borderRadius: R.panel, padding: S.m, gap: S.m },
  input: { minHeight: 64, textAlignVertical: 'top', paddingHorizontal: S.s, paddingTop: S.s },
  aidToggle: { borderWidth: 1, borderRadius: 20, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 10 },
  passage: { borderLeftWidth: 2, paddingLeft: S.l, marginTop: S.m },
});
