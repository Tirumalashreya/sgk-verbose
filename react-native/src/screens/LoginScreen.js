// Login — the fixed username/password the backend was given (APP_USERS),
// not a signup flow. Shown once at launch (credentials then stay on the
// device) and again any time a request comes back 401 — e.g. the password
// was changed on the backend.
import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet } from 'react-native';
import { useTheme, F, T, S, R } from '../theme';
import { Screen, Enter, Button, Portrait } from '../ui/kit';
import { tryLogin, saveCredentials } from '../services/api';

const isTe = (s) => /[ఀ-౿]/.test(s || '');

export default function LoginScreen({ t, onLoggedIn }) {
  const c = useTheme();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    const u = username.trim();
    if (!u || !password) return;
    setBusy(true); setError('');
    try {
      const ok = await tryLogin(u, password);
      if (!ok) { setError(t('loginFailed')); setBusy(false); return; }
      await saveCredentials(u, password);
      onLoggedIn();
    } catch (e) {
      setError(String(e.message || e));
      setBusy(false);
    }
  };

  return (
    <Screen c={c} scroll={false}>
      <View style={st.center}>
        <Portrait c={c} size={96} />
        <Enter delay={60} style={{ alignItems: 'center', marginTop: S.l }}>
          <Text style={[isTe(t('loginTitle')) ? T.displayTe : T.display, { color: c.ink, textAlign: 'center' }]}>
            {t('loginTitle')}
          </Text>
          <Text style={[isTe(t('loginHint')) ? { fontFamily: F.read, fontSize: 14.5, lineHeight: 24 } : T.body,
            { color: c.inkSoft, textAlign: 'center', marginTop: S.s, maxWidth: 320 }]}>
            {t('loginHint')}
          </Text>
        </Enter>

        <View style={{ width: '100%', maxWidth: 360, marginTop: S.x3, gap: S.m }}>
          <TextInput
            value={username} onChangeText={(v) => { setUsername(v); setError(''); }}
            placeholder={t('username')} placeholderTextColor={c.muted}
            autoCapitalize="none" autoCorrect={false}
            style={[st.input, { color: c.ink, borderColor: c.line, backgroundColor: c.surface }]}
          />
          <TextInput
            value={password} onChangeText={(v) => { setPassword(v); setError(''); }}
            placeholder={t('password')} placeholderTextColor={c.muted}
            secureTextEntry autoCapitalize="none" autoCorrect={false}
            onSubmitEditing={submit}
            style={[st.input, { color: c.ink, borderColor: c.line, backgroundColor: c.surface }]}
          />
          {!!error && <Text style={[T.body, { color: c.kumkumText }]}>{error}</Text>}
          <Button c={c} label={busy ? t('loggingIn') : t('login')} variant="primary"
            disabled={busy || !username.trim() || !password} onPress={submit} />
        </View>
      </View>
    </Screen>
  );
}

const st = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: S.xl },
  input: { minHeight: 52, borderRadius: R.control, borderWidth: 1, paddingHorizontal: S.l, fontSize: 16 },
});
