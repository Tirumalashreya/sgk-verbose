import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

const labelMap = {
  teaching: { bg: colors.labelTeaching, text: colors.labelTeachingText, label: 'Teaching' },
  shloka: { bg: colors.labelShloka, text: colors.labelShlokaText, label: 'Sloka' },
  story: { bg: colors.labelStory, text: colors.labelStoryText, label: 'Story' },
  philosophy: { bg: colors.labelPhilosophy, text: colors.labelPhilosophyText, label: 'Philosophy' },
  devotional: { bg: colors.labelDevotional, text: colors.labelDevotionalText, label: 'Devotional' },
};

export default function LabelChip({ label }) {
  const style = labelMap[label] || labelMap.teaching;
  return (
    <View style={[styles.chip, { backgroundColor: style.bg }]}>
      <Text style={[styles.text, { color: style.text }]}>{style.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 100,
    alignSelf: 'flex-start',
  },
  text: { fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },
});
