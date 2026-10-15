// Ask — finds the passage in the pravachanams where something was said (search
// over the stored notes). Honest: shows what was found, nothing invented.
import React, { useState } from 'react';
import { View, Text, TextInput, ActivityIndicator, StyleSheet } from 'react-native';
import { useTheme, F, T, S, R } from '../theme';
import { Screen, Enter, Button, Overline } from '../ui/kit';
import { searchRag } from '../services/api';

const isTe = (s) => /[ఀ-౿]/.test(s || '');

export default function AskScreen({ t, lang }) {
  const c = useTheme();
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState([]);   // [{ question, passage }]

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
        <TextInput value={q} onChangeText={setQ} placeholder={t('askPlaceholder')} placeholderTextColor={c.muted}
          multiline style={[isTe(q) ? { fontFamily: F.read, fontSize: 16, lineHeight: 28 } : T.body, st.input, { color: c.ink }]}
          accessibilityLabel={t('askTitle')} onSubmitEditing={ask} blurOnSubmit returnKeyType="search" />
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
  passage: { borderLeftWidth: 2, paddingLeft: S.l, marginTop: S.m },
});
