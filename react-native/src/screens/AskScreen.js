import React, { useState, useRef } from 'react';
import { View, Text, ScrollView, Pressable, ActivityIndicator } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { C, F } from '../theme';
import { SUGGESTIONS, ANSWERS } from '../data';

export default function AskScreen({ go, t, lang }) {
  const insets = useSafeAreaInsets();
  const [messages, setMessages] = useState([]);
  const [typing, setTyping] = useState(false);
  const scRef = useRef(null);
  const sugLabel = (s) => (lang === 'te' ? s.te : s.label);

  const ask = (id, label) => {
    setMessages((m) => [...m, { role: 'user', text: label }]);
    setTyping(true);
    setTimeout(() => {
      setMessages((m) => [...m, ANSWERS[id]]);
      setTyping(false);
    }, 1500);
  };

  const empty = messages.length === 0 && !typing;

  return (
    <View style={{ flex: 1, backgroundColor: C.paper }}>
      <View style={{ paddingTop: insets.top + 6, paddingHorizontal: 22, flexDirection: 'row', alignItems: 'center', paddingBottom: 12 }}>
        <Pressable onPress={() => go('library')} style={{ marginRight: 10 }}><Text style={{ fontSize: 26, color: C.maroon }}>‹</Text></Pressable>
        <View>
          <Text style={{ fontFamily: F.serif, fontSize: 21, color: C.ink }}>{t('askTitle')}</Text>
          <Text style={{ fontSize: 11.5, color: C.muted, marginTop: 3 }}>{t('askSub')}</Text>
        </View>
      </View>

      <ScrollView
        ref={scRef}
        onContentSizeChange={() => scRef.current?.scrollToEnd({ animated: true })}
        style={{ flex: 1 }}
        contentContainerStyle={{ paddingHorizontal: 22, paddingBottom: 16 }}
        showsVerticalScrollIndicator={false}
      >
        {empty && (
          <View style={{ marginTop: 10 }}>
            <View style={{ width: 74, height: 74, alignSelf: 'center', marginVertical: 16, alignItems: 'center', justifyContent: 'center' }}>
              <View style={{ position: 'absolute', width: 74, height: 74, borderRadius: 37, borderWidth: 1, borderColor: '#cdb27a' }} />
              <View style={{ position: 'absolute', width: 56, height: 56, borderRadius: 28, borderWidth: 1, borderColor: '#e0cb98' }} />
              <Text style={{ fontFamily: F.dev, fontSize: 26, color: C.maroon }}>ॐ</Text>
            </View>
            <Text style={{ textAlign: 'center', fontSize: 13.5, color: C.inkSoft, lineHeight: 21, maxWidth: 260, alignSelf: 'center', marginBottom: 22 }}>
              {t('askEmpty')}
            </Text>
            <Text style={{ fontSize: 11, letterSpacing: 1, color: C.gold, marginBottom: 10 }}>{t('tryAsking')}</Text>
            {SUGGESTIONS.map((s) => (
              <Pressable key={s.id} onPress={() => ask(s.id, sugLabel(s))} style={{ padding: 14, borderRadius: 14, backgroundColor: C.card, borderWidth: 1, borderColor: C.line, marginBottom: 10 }}>
                <Text style={{ fontSize: 14, color: C.ink }}>{sugLabel(s)}</Text>
              </Pressable>
            ))}
          </View>
        )}

        {messages.map((m, i) =>
          m.role === 'user' ? (
            <LinearGradient key={i} colors={['#7a2e25', '#601f18']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={{ alignSelf: 'flex-end', maxWidth: '80%', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 18, borderBottomRightRadius: 4, marginBottom: 14 }}>
              <Text style={{ color: C.cream, fontSize: 14, lineHeight: 21 }}>{m.text}</Text>
            </LinearGradient>
          ) : (
            <View key={i} style={{ alignSelf: 'flex-start', maxWidth: '90%', marginBottom: 14 }}>
              <Text style={{ fontSize: 14, lineHeight: 23, color: C.ink }}>{m.text}</Text>
              {m.shloka && (
                <View style={{ borderRadius: 14, padding: 14, backgroundColor: C.card, borderWidth: 1, borderColor: C.line, marginTop: 10 }}>
                  <Text style={{ fontSize: 10, letterSpacing: 1.5, color: C.gold, marginBottom: 7 }}>{m.shloka.ref.toUpperCase()}</Text>
                  <Text style={{ fontFamily: F.dev, fontSize: 15.5, lineHeight: 28, color: C.maroon }}>{m.shloka.dev}</Text>
                  <Text style={{ fontSize: 11.5, color: '#a8924f', fontStyle: 'italic', marginTop: 6 }}>{m.shloka.translit}</Text>
                </View>
              )}
              <Pressable onPress={() => go('discourse')} style={{ flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', marginTop: 10, paddingVertical: 7, paddingHorizontal: 12, borderRadius: 99, backgroundColor: '#f1e6cf', borderWidth: 1, borderColor: '#e0cb98' }}>
                <View style={{ width: 5, height: 5, backgroundColor: C.saffron, marginRight: 7, transform: [{ rotate: '45deg' }] }} />
                <Text style={{ fontSize: 11.5, color: C.maroon }}>{m.cite}</Text>
              </Pressable>
            </View>
          )
        )}

        {typing && (
          <View style={{ alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 16, borderRadius: 18, backgroundColor: C.card, borderWidth: 1, borderColor: C.line, marginBottom: 14 }}>
            <ActivityIndicator size="small" color={C.goldSoft} />
            <Text style={{ fontSize: 12, color: C.muted, marginLeft: 8 }}>{t('searching')}</Text>
          </View>
        )}
      </ScrollView>

      {/* input */}
      <View style={{ paddingHorizontal: 18, paddingTop: 10, paddingBottom: insets.bottom + 14, backgroundColor: C.paper }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', paddingLeft: 18, paddingRight: 8, paddingVertical: 8, borderRadius: 99, backgroundColor: C.card, borderWidth: 1, borderColor: '#e0cb98' }}>
          <Text style={{ flex: 1, fontSize: 14, color: '#a99c80' }}>{t('askPlaceholder')}</Text>
          <Pressable onPress={() => ask('dharma', sugLabel(SUGGESTIONS[0]))}>
            <LinearGradient colors={['#e0843b', '#c25a26']} style={{ width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' }}>
              <Text style={{ color: '#fff4e2', fontSize: 16 }}>↑</Text>
            </LinearGradient>
          </Pressable>
        </View>
      </View>
    </View>
  );
}
