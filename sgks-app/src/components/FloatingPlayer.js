import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';

export default function FloatingPlayer({ session, isPlaying, onToggle }) {
  if (!session) return null;
  return (
    <View style={styles.container}>
      <View style={styles.left}>
        <View style={styles.imgPlaceholder}>
          <Ionicons name="musical-notes" size={18} color={colors.gold} />
        </View>
        <View style={styles.info}>
          <Text style={styles.title} numberOfLines={1}>{session.title || 'Live Session'}</Text>
          <View style={styles.liveRow}>
            <View style={styles.liveDot} />
            <Text style={styles.liveText}>Live</Text>
          </View>
        </View>
      </View>
      <View style={styles.waveform}>
        {[4,8,12,6,10,14,8,6,10,8].map((h, i) => (
          <View key={i} style={[styles.bar, { height: h }]} />
        ))}
      </View>
      <TouchableOpacity style={styles.pauseBtn} onPress={onToggle}>
        <Ionicons name={isPlaying ? 'pause' : 'play'} size={20} color={colors.dark} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 80,
    left: 16,
    right: 16,
    backgroundColor: colors.darkCard,
    borderRadius: 16,
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 8,
  },
  left: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  imgPlaceholder: {
    width: 44,
    height: 44,
    borderRadius: 8,
    backgroundColor: '#2D1B1B',
    justifyContent: 'center',
    alignItems: 'center',
  },
  info: { marginLeft: 10, flex: 1 },
  title: { color: '#FFF', fontSize: 13, fontWeight: '600' },
  liveRow: { flexDirection: 'row', alignItems: 'center', marginTop: 3 },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.liveBadge, marginRight: 5 },
  liveText: { color: colors.textMuted, fontSize: 11 },
  waveform: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    marginHorizontal: 12,
  },
  bar: { width: 3, backgroundColor: colors.gold, borderRadius: 2, opacity: 0.8 },
  pauseBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.gold,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
