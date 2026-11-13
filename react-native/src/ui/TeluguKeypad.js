// Telugu Visual Keypad (Option B) for easy typing and spelling corrections
import React, { useState } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { useTheme, F, T, S, R } from '../theme';

const SIGNS = [
  '్', 'ా', 'ి', 'ీ', 'ు', 'ూ', 'ృ', 'ౄ', 'ె', 'ే', 'ై', 'ొ', 'ో', 'ౌ', 'ం', 'ః', 'ఁ',
  '్క', '్ఖ', '్గ', '్ఘ', '్చ', '్ఛ', '్జ', '్ట', '్ఠ', '్డ', '్ణ', '్త', '్థ', '్ద', '్ధ',
  '్న', '్ప', '్ఫ', '్బ', '్భ', '్మ', '్య', '్ర', '్ల', '్వ', '్శ', '్ష', '్స', '్హ', '్ళ', '్ఱ'
];

const CONSONANTS = [
  'క', 'ఖ', 'గ', 'ఘ', 'ఙ',
  'చ', 'ఛ', 'జ', 'ఝ', 'ఞ',
  'ట', 'ఠ', 'డ', 'ఢ', 'ణ',
  'త', 'థ', 'ద', 'ధ', 'న',
  'ప', 'ఫ', 'బ', 'భ', 'మ',
  'య', 'ర', 'ల', 'వ', 'శ',
  'ష', 'స', 'హ', 'ళ', 'క్ష', 'ఱ'
];

const VOWELS = [
  'అ', 'ఆ', 'ఇ', 'ఈ', 'ఉ', 'ఊ', 'ఋ', 'ౠ',
  'ఎ', 'ఏ', 'ఐ', 'ఒ', 'ఓ', 'ఔ', 'అం', 'అః'
];

const TABS = [
  { id: 'signs', label: 'గుణింతాలు & వత్తులు' },
  { id: 'consonants', label: 'హల్లులు (క-ఱ)' },
  { id: 'vowels', label: 'అచ్చులు (అ-ఔ)' },
];

export default function TeluguKeypad({ onInsert, onBackspace, onClose }) {
  const c = useTheme();
  const [activeTab, setActiveTab] = useState('signs');

  const chars = activeTab === 'signs' ? SIGNS : activeTab === 'consonants' ? CONSONANTS : VOWELS;

  return (
    <View style={[st.container, { backgroundColor: c.surface, borderColor: c.brass }]}>
      {/* Tab selection header */}
      <View style={[st.tabRow, { borderBottomColor: c.line }]}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6, paddingHorizontal: S.xs }}>
          {TABS.map((tab) => {
            const on = activeTab === tab.id;
            return (
              <Pressable
                key={tab.id}
                onPress={() => setActiveTab(tab.id)}
                style={[
                  st.tabBtn,
                  {
                    backgroundColor: on ? c.brass : 'transparent',
                    borderColor: on ? c.brass : c.line,
                  },
                ]}
              >
                <Text style={{ fontFamily: F.readMed, fontSize: 13, color: on ? c.onBrass : c.ink }}>
                  {tab.label}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>
        {onClose && (
          <Pressable onPress={onClose} style={[st.closeBtn, { borderColor: c.line }]} accessibilityLabel="Close keyboard">
            <Text style={{ fontSize: 14, color: c.muted, fontWeight: '700' }}>✕</Text>
          </Pressable>
        )}
      </View>

      {/* Characters grid */}
      <View style={st.grid}>
        {chars.map((char, index) => (
          <Pressable
            key={index}
            onPress={() => onInsert(char)}
            style={({ pressed }) => [
              st.key,
              {
                backgroundColor: pressed ? c.brassSoft || c.raised : c.raised,
                borderColor: c.line,
              },
            ]}
          >
            <Text style={[st.keyText, { color: c.ink }]}>{char}</Text>
          </Pressable>
        ))}
      </View>

      {/* Control row: Space, Backspace, Punctuation */}
      <View style={[st.controlRow, { borderTopColor: c.line }]}>
        <Pressable
          onPress={() => onInsert(' ')}
          style={[st.controlBtn, { flex: 2, backgroundColor: c.raised, borderColor: c.line }]}
        >
          <Text style={[st.controlText, { color: c.ink }]}>స్పేస్ (Space)</Text>
        </Pressable>
        <Pressable
          onPress={onBackspace}
          style={[st.controlBtn, { flex: 1, backgroundColor: c.raised, borderColor: c.line }]}
          accessibilityLabel="Backspace"
        >
          <Text style={[st.controlText, { color: c.kumkumText || c.ink, fontWeight: '700' }]}>⌫ డిలీట్</Text>
        </Pressable>
        {['.', ',', '?', '"'].map((p) => (
          <Pressable
            key={p}
            onPress={() => onInsert(p)}
            style={[st.punctKey, { backgroundColor: c.raised, borderColor: c.line }]}
          >
            <Text style={{ fontSize: 16, fontWeight: '700', color: c.ink }}>{p}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  container: {
    borderWidth: 1.5,
    borderRadius: R.panel,
    padding: S.s,
    marginTop: S.s,
    marginBottom: S.m,
  },
  tabRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingBottom: S.xs,
    borderBottomWidth: StyleSheet.hairlineWidth,
    marginBottom: S.s,
  },
  tabBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
  },
  closeBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderLeftWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    justifyContent: 'center',
    maxHeight: 180,
    overflow: 'scroll',
    paddingVertical: 4,
  },
  key: {
    minWidth: 42,
    height: 42,
    paddingHorizontal: 8,
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  keyText: {
    fontFamily: F.readMed,
    fontSize: 20,
    textAlign: 'center',
  },
  controlRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingTop: S.s,
    marginTop: S.s,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  controlBtn: {
    height: 40,
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  controlText: {
    fontFamily: F.readMed,
    fontSize: 13,
  },
  punctKey: {
    width: 36,
    height: 40,
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
