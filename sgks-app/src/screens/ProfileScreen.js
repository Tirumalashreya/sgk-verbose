import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '../theme/colors';
import VaishnavaBg from '../components/VaishnavaBg';

const STATS = [
  { label: 'Sessions', value: '48' },
  { label: 'Hours', value: '62' },
  { label: 'Shlokas', value: '318' },
];

const SETTINGS = [
  { icon: 'globe-outline', label: 'Language', value: 'English' },
  { icon: 'notifications-outline', label: 'Notifications', toggle: true },
  { icon: 'download-outline', label: 'Offline Mode', toggle: true },
  { icon: 'text-outline', label: 'Text Size', value: 'Medium' },
];

const MENU = [
  { icon: 'bookmark-outline', label: 'Bookmarks' },
  { icon: 'heart-outline', label: 'Liked Sessions' },
  { icon: 'share-social-outline', label: 'Share App' },
  { icon: 'help-circle-outline', label: 'Help & Support' },
  { icon: 'information-circle-outline', label: 'About' },
];

export default function ProfileScreen() {
  const [notifications, setNotifications] = useState(true);
  const [offline, setOffline] = useState(false);

  return (
    <VaishnavaBg>
      <SafeAreaView style={{ flex: 1 }}>
        <ScrollView showsVerticalScrollIndicator={false}>

          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.headerTitle}>
              <Text style={styles.lotusSmall}>❀ </Text>
              Profile
            </Text>
          </View>

          {/* Avatar + name */}
          <View style={styles.avatarSection}>
            <LinearGradient
              colors={['#D4A017', '#A87800']}
              style={styles.avatarRing}
            >
              <View style={styles.avatar}>
                <Text style={styles.avatarOm}>ॐ</Text>
              </View>
            </LinearGradient>
            <Text style={styles.userName}>Sri Devotee</Text>
            <Text style={styles.userEmail}>venkatananduri3@gmail.com</Text>

            <View style={styles.langToggle}>
              <TouchableOpacity style={[styles.langBtn, styles.langActive]}>
                <Text style={styles.langActiveText}>ENGLISH</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.langBtn}>
                <Text style={styles.langText}>తెలుగు</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Stats */}
          <LinearGradient
            colors={['rgba(212,160,23,0.12)', 'rgba(212,160,23,0.04)']}
            style={styles.statsCard}
          >
            {STATS.map((s, i) => (
              <View key={i} style={[styles.statItem, i < STATS.length - 1 && styles.statDivider]}>
                <Text style={styles.statValue}>{s.value}</Text>
                <Text style={styles.statLabel}>{s.label}</Text>
              </View>
            ))}
          </LinearGradient>

          {/* Settings */}
          <Text style={styles.sectionTitle}>Preferences</Text>
          <View style={styles.menuCard}>
            {SETTINGS.map((item, i) => (
              <View key={i} style={[styles.menuRow, i < SETTINGS.length - 1 && styles.menuDivider]}>
                <View style={styles.menuLeft}>
                  <View style={styles.menuIconBox}>
                    <Ionicons name={item.icon} size={18} color={colors.gold} />
                  </View>
                  <Text style={styles.menuLabel}>{item.label}</Text>
                </View>
                {item.toggle !== undefined ? (
                  <Switch
                    value={item.label === 'Notifications' ? notifications : offline}
                    onValueChange={(v) => item.label === 'Notifications' ? setNotifications(v) : setOffline(v)}
                    trackColor={{ false: 'rgba(255,255,255,0.15)', true: colors.gold }}
                    thumbColor="#FFF"
                  />
                ) : (
                  <View style={styles.menuRight}>
                    <Text style={styles.menuValue}>{item.value}</Text>
                    <Ionicons name="chevron-forward" size={14} color={colors.textMuted} />
                  </View>
                )}
              </View>
            ))}
          </View>

          {/* Menu */}
          <Text style={styles.sectionTitle}>More</Text>
          <View style={styles.menuCard}>
            {MENU.map((item, i) => (
              <TouchableOpacity key={i} style={[styles.menuRow, i < MENU.length - 1 && styles.menuDivider]}>
                <View style={styles.menuLeft}>
                  <View style={styles.menuIconBox}>
                    <Ionicons name={item.icon} size={18} color={colors.gold} />
                  </View>
                  <Text style={styles.menuLabel}>{item.label}</Text>
                </View>
                <Ionicons name="chevron-forward" size={14} color={colors.textMuted} />
              </TouchableOpacity>
            ))}
          </View>

          {/* Footer */}
          <View style={styles.footer}>
            <Text style={styles.footerOm}>ॐ</Text>
            <Text style={styles.footerText}>Sgks Live Notes</Text>
            <Text style={styles.footerVersion}>Version 1.0.0 · AI that listens. Wisdom that stays.</Text>
          </View>

          <View style={{ height: 100 }} />
        </ScrollView>
      </SafeAreaView>
    </VaishnavaBg>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  headerTitle: { fontSize: 20, fontWeight: '700', color: colors.text },
  lotusSmall: { fontSize: 18, color: colors.gold },
  avatarSection: { alignItems: 'center', paddingVertical: 24 },
  avatarRing: {
    width: 90,
    height: 90,
    borderRadius: 45,
    padding: 3,
    marginBottom: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatar: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: '#0D2244',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarOm: { fontSize: 36, color: colors.gold },
  userName: { fontSize: 20, fontWeight: '700', color: colors.text, marginBottom: 4 },
  userEmail: { fontSize: 13, color: colors.textMuted, marginBottom: 16 },
  langToggle: { flexDirection: 'row', gap: 10 },
  langBtn: {
    paddingHorizontal: 18,
    paddingVertical: 8,
    borderRadius: 100,
    borderWidth: 1.5,
    borderColor: 'rgba(212,160,23,0.4)',
  },
  langActive: { backgroundColor: 'rgba(212,160,23,0.2)' },
  langActiveText: { color: colors.gold, fontWeight: '700', fontSize: 13 },
  langText: { color: 'rgba(255,255,255,0.4)', fontWeight: '600', fontSize: 13 },
  statsCard: {
    flexDirection: 'row',
    marginHorizontal: 20,
    borderRadius: 18,
    padding: 20,
    marginBottom: 28,
    borderWidth: 1,
    borderColor: 'rgba(212,160,23,0.25)',
  },
  statItem: { flex: 1, alignItems: 'center' },
  statDivider: {
    borderRightWidth: 1,
    borderRightColor: 'rgba(212,160,23,0.2)',
  },
  statValue: { fontSize: 24, fontWeight: '800', color: colors.gold, marginBottom: 4 },
  statLabel: { fontSize: 12, color: colors.textMuted, fontWeight: '500' },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.textMuted,
    letterSpacing: 1,
    paddingHorizontal: 20,
    marginBottom: 10,
    textTransform: 'uppercase',
  },
  menuCard: {
    marginHorizontal: 20,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 18,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    marginBottom: 24,
    overflow: 'hidden',
  },
  menuRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
  },
  menuDivider: {
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  menuLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  menuIconBox: {
    width: 34,
    height: 34,
    borderRadius: 10,
    backgroundColor: 'rgba(212,160,23,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  menuLabel: { fontSize: 15, color: colors.text, fontWeight: '500' },
  menuRight: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  menuValue: { fontSize: 13, color: colors.textMuted },
  footer: { alignItems: 'center', paddingVertical: 20 },
  footerOm: { fontSize: 32, color: colors.gold, opacity: 0.5, marginBottom: 6 },
  footerText: { fontSize: 15, fontWeight: '700', color: colors.text, marginBottom: 4 },
  footerVersion: { fontSize: 11, color: colors.textMuted, textAlign: 'center' },
});
