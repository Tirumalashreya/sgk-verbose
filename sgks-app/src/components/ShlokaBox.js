import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '../theme/colors';

export default function ShlokaBox({ shloka, meaning, source }) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>✦ SLOKA OF THE SESSION ✦</Text>
      <LinearGradient
        colors={['rgba(212,160,23,0.15)', 'rgba(212,160,23,0.05)', 'rgba(212,160,23,0.12)']}
        style={styles.box}
      >
        <View style={styles.boxBorder} />
        <Text style={styles.omTop}>ॐ</Text>
        <Text style={styles.shlokaText}>{shloka}</Text>
        {source ? <Text style={styles.source}>— {source}</Text> : null}
      </LinearGradient>
      {meaning ? (
        <View style={styles.meaningContainer}>
          <Text style={styles.meaningLabel}>MEANING (AI GENERATED)</Text>
          <Text style={styles.meaningText}>{meaning}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginHorizontal: 20, marginBottom: 24 },
  label: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.gold,
    letterSpacing: 1.5,
    marginBottom: 12,
    textAlign: 'center',
  },
  box: {
    borderRadius: 16,
    padding: 28,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(212,160,23,0.4)',
    overflow: 'hidden',
  },
  boxBorder: {
    position: 'absolute',
    left: 0, top: 0, bottom: 0,
    width: 4,
    backgroundColor: colors.gold,
    borderTopLeftRadius: 16,
    borderBottomLeftRadius: 16,
  },
  omTop: {
    fontSize: 24,
    color: colors.gold,
    marginBottom: 12,
    opacity: 0.7,
  },
  shlokaText: {
    fontSize: 19,
    lineHeight: 36,
    color: colors.text,
    textAlign: 'center',
    fontStyle: 'italic',
    fontWeight: '500',
  },
  source: {
    marginTop: 16,
    fontSize: 13,
    color: colors.gold,
    fontWeight: '600',
    textAlign: 'center',
  },
  meaningContainer: { marginTop: 20 },
  meaningLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.saffron,
    letterSpacing: 1.5,
    marginBottom: 8,
  },
  meaningText: {
    fontSize: 15,
    lineHeight: 24,
    color: colors.text,
  },
});
