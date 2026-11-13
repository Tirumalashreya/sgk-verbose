// Shared components — implements DESIGN.md §5. Screens compose only these.
import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, Pressable, Image, ScrollView, Animated, Easing, StyleSheet, Platform, AccessibilityInfo,
  Modal, TextInput,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Icon from './Icon';
import Kolam from './Kolam';
import { F, T, S, R, MOTION, acharyaPhoto } from '../theme';

const isTelugu = (s) => /[ఀ-౿]/.test(s || '');

/** Screen frame: safe areas, background, optional kolam, centred max-width column. */
export function Screen({ c, kolam = false, scroll = true, children, footer, contentStyle, refreshControl }) {
  const insets = useSafeAreaInsets();
  const Body = scroll ? ScrollView : View;
  return (
    <View style={{ flex: 1, backgroundColor: c.bg }}>
      {kolam && <Kolam color={c.kolam} />}
      <Body
        style={{ flex: 1 }}
        refreshControl={refreshControl}
        contentContainerStyle={scroll ? [st.column, { paddingTop: insets.top + S.l, paddingBottom: insets.bottom + 120 }, contentStyle] : undefined}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {scroll ? children : <View style={[st.column, { flex: 1, paddingTop: insets.top + S.l }, contentStyle]}>{children}</View>}
      </Body>
      {footer}
    </View>
  );
}

/** Fades and lifts children in once (respects Reduce Motion). */
export function Enter({ delay = 0, children, style }) {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    let alive = true;
    AccessibilityInfo.isReduceMotionEnabled?.().then((reduce) => {
      if (!alive) return;
      if (reduce) { v.setValue(1); return; }
      Animated.timing(v, { toValue: 1, duration: MOTION.enter, delay, easing: Easing.out(Easing.cubic), useNativeDriver: true }).start();
    });
    return () => { alive = false; };
  }, []);
  return (
    <Animated.View style={[style, { opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [8, 0] }) }] }]}>
      {children}
    </Animated.View>
  );
}

export function Overline({ c, children, style }) {
  return <Text style={[isTelugu(children) ? T.label : T.caption, { color: c.brass, textTransform: isTelugu(children) ? 'none' : 'uppercase' }, style]}>{children}</Text>;
}

/** Buttons. variant: primary (kumkum), brass, quiet (outline), ghost. */
export function Button({ c, label, icon, onPress, variant = 'primary', disabled, style, accessibilityLabel }) {
  const fill = { primary: c.kumkum, brass: c.brass, quiet: 'transparent', ghost: 'transparent' }[variant];
  const fg = { primary: c.onFill, brass: c.onBrass, quiet: c.ink, ghost: c.brass }[variant];
  return (
    <Pressable
      onPress={onPress} disabled={disabled}
      accessibilityRole="button" accessibilityLabel={accessibilityLabel || label}
      style={({ pressed }) => [st.button, {
        backgroundColor: fill, borderColor: variant === 'quiet' ? c.line : 'transparent',
        opacity: disabled ? 0.45 : pressed ? 0.85 : 1,
      }, style]}
    >
      {icon && <Icon name={icon} size={19} color={fg} />}
      {!!label && <Text style={[T.label, { color: fg, fontSize: 15 }, isTelugu(label) && { fontFamily: F.readMed, letterSpacing: 0 }]}>{label}</Text>}
    </Pressable>
  );
}

export function IconButton({ c, icon, onPress, label, color }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={label} hitSlop={8}
      style={({ pressed }) => [st.iconButton, { opacity: pressed ? 0.6 : 1 }]}>
      <Icon name={icon} size={22} color={color || c.inkSoft} />
    </Pressable>
  );
}

/** Large tappable action. hero = the Record tile (kumkum light). */
export function ActionTile({ c, icon, title, hint, onPress, hero, busy, style }) {
  const inner = (
    <>
      <View style={[st.tileRing, { borderColor: hero ? 'rgba(242,200,119,0.55)' : c.line, backgroundColor: hero ? 'rgba(14,11,31,0.18)' : c.raised }]}>
        <Icon name={icon} size={hero ? 26 : 22} color={hero ? c.onFill : c.brass} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={[isTelugu(title) ? T.titleTe : T.title, { color: hero ? c.onFill : c.ink, fontSize: hero ? 22 : 18 }]}>{title}</Text>
        <Text style={[T.body, { color: hero ? 'rgba(245,236,223,0.82)' : c.muted, marginTop: 2 }, isTelugu(hint) && { fontFamily: F.read, fontSize: 14 }]}>{busy || hint}</Text>
      </View>
      <Icon name="chevron" size={18} color={hero ? c.onFill : c.muted} />
    </>
  );
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`${title}. ${hint}`}
      style={({ pressed }) => [{ opacity: pressed ? 0.88 : 1, transform: [{ scale: pressed ? 0.995 : 1 }] }, style]}>
      {hero ? (
        <LinearGradient colors={[c.kumkum, c.kumkumDeep]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[st.tile, st.tileHero]}>
          {inner}
        </LinearGradient>
      ) : (
        <View style={[st.tile, { backgroundColor: c.surface, borderColor: c.line, borderWidth: StyleSheet.hairlineWidth }]}>{inner}</View>
      )}
    </Pressable>
  );
}

/** big: for a status chip that's the main thing on screen (e.g. LiveScreen's
 * top banner while recording/saving) — same chip, legible from across a
 * room on phone or laptop instead of the normal caption-sized badge. */
export function Chip({ c, tone = 'neutral', icon, big, children }) {
  const color = { neutral: c.muted, review: c.review, ok: c.leaf, live: c.turmeric, error: c.kumkumText }[tone];
  return (
    <View style={[st.chip, big && st.chipBig, { borderColor: color }]}>
      {icon && <Icon name={icon} size={big ? 20 : 13} color={color} strokeWidth={2} />}
      <Text style={[T.caption, { color, letterSpacing: 0.4, fontSize: big ? 17 : 11.5 },
        isTelugu(children) && { fontFamily: F.readMed, fontSize: big ? 18 : 12 }]}>{children}</Text>
    </View>
  );
}

/** The Acharya's portrait in a brass ring. */
export function Portrait({ c, size = 52, source = acharyaPhoto }) {
  return (
    <View style={{ width: size + 8, height: size + 8, borderRadius: (size + 8) / 2, borderWidth: 1.5, borderColor: c.brass, alignItems: 'center', justifyContent: 'center' }}>
      <Image source={source} style={{ width: size, height: size, borderRadius: size / 2 }} accessibilityIgnoresInvertColors />
    </View>
  );
}

export function sessionStatus(s) {
  if (!s.notes && !s.transcript) return 'processing';
  // Only a real two-listener disagreement counts as "needs review" — an ASR
  // gap or a low term-dictionary confidence score is a different situation
  // (and with ASR_PROVIDER no longer "dual", there's rarely a second listener
  // to disagree in the first place), so neither should raise this flag.
  const unresolved = s.asr_report?.uncertain?.length || 0;
  return unresolved > 0 ? 'review' : 'ready';
}

export function SessionRow({ c, t, session, onPress, onLongPress, divider = true }) {
  const status = sessionStatus(session);
  const date = session.created_at ? new Date(session.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '';
  const verses = (session.shlokas || []).length;
  return (
    <Pressable onPress={onPress} onLongPress={onLongPress} accessibilityRole="button" accessibilityLabel={session.title}
      style={({ pressed }) => [st.row, divider && { borderBottomColor: c.line, borderBottomWidth: StyleSheet.hairlineWidth }, { opacity: pressed ? 0.7 : 1 }]}>
      <View style={[st.rowMark, { backgroundColor: c.raised, borderColor: c.line }]}>
        <Icon name="lotus" size={22} color={c.brass} />
      </View>
      <View style={{ flex: 1, gap: 4 }}>
        <Text numberOfLines={1} style={[isTelugu(session.title) ? T.titleTe : T.title, { color: c.ink, fontSize: 17, lineHeight: 24 }]}>{session.title || 'Pravachanam'}</Text>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: S.s, flexWrap: 'wrap' }}>
          <Text style={[T.body, { color: c.muted, fontSize: 13 }]}>{date}{verses ? ` · ${verses} ${t('verses')}` : ''}</Text>
          {status === 'review' && <Chip c={c} tone="review" icon="alert">{t('needsReview')}</Chip>}
          {status === 'processing' && <Chip c={c} tone="live">{t('processing')}</Chip>}
        </View>
      </View>
      <Icon name="chevron" size={18} color={c.muted} />
    </Pressable>
  );
}

/** Processing steps as a line of nodes; done = turmeric, current pulses. */
export function StagePath({ c, stages, labels, done, active }) {
  const pulse = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(pulse, { toValue: 1, duration: 900, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      Animated.timing(pulse, { toValue: 0, duration: 900, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
    ]));
    loop.start();
    return () => loop.stop();
  }, []);
  return (
    <View accessibilityRole="progressbar" accessibilityLabel={labels[active] || ''} style={{ flexDirection: 'row', alignItems: 'flex-start' }}>
      {stages.map((key, i) => {
        const isDone = done.has(key), isActive = key === active;
        return (
          <View key={key} style={{ flex: 1, alignItems: 'center' }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', width: '100%' }}>
              <View style={{ flex: 1, height: 1.5, backgroundColor: i === 0 ? 'transparent' : (isDone || isActive ? c.turmeric : c.line) }} />
              <Animated.View style={{
                width: 13, height: 13, borderRadius: 6.5,
                backgroundColor: isDone ? c.turmeric : isActive ? c.brassBright : 'transparent',
                borderWidth: 1.5, borderColor: isDone || isActive ? c.turmeric : c.line,
                opacity: isActive ? pulse.interpolate({ inputRange: [0, 1], outputRange: [0.55, 1] }) : 1,
              }} />
              <View style={{ flex: 1, height: 1.5, backgroundColor: i === stages.length - 1 ? 'transparent' : (isDone ? c.turmeric : c.line) }} />
            </View>
            <Text numberOfLines={2} style={[T.label, { color: isActive ? c.brassBright : isDone ? c.inkSoft : c.muted, marginTop: 8, fontSize: 13, textAlign: 'center' }, isTelugu(labels[key]) && { fontFamily: F.readMed, fontSize: 13.5 }]}>{labels[key]}</Text>
          </View>
        );
      })}
    </View>
  );
}

/** A verse on its own line: Telugu as spoken, highlighted. Native Sanskrit/Tamil original omitted per user requirement. */
export function VerseBlock({ c, text, original, reference, type }) {
  return (
    <View style={[st.verse, { borderLeftColor: c.brass, backgroundColor: c.surface }]} accessibilityRole="text">
      {!!type && <Overline c={c} style={{ marginBottom: 6 }}>{type}</Overline>}
      <Text selectable style={[T.verse, { color: c.ink }]}>{text}</Text>
    </View>
  );
}

/** The notes: paragraphs of the verbatim transcript, verses where spoken.
 *  A verse long enough to stand on its own line becomes its own boxed block
 *  (SHLOKA_LINE); a one- or two-word verse sits inline inside its sentence
 *  instead (SHLOKA_MARK — the same markup, just not alone on its line). */
const SHLOKA_LINE = /^\*\*"(.+?)"\*\*(?:\s*\(([^)]*)\))?$/;
const SHLOKA_MARK = /\*\*"(.+?)"\*\*(?:\s*\(([^)]*)\))?/g;

const stripUnwantedBrackets = (s) => (s || '').replace(/\s*\([^)]*[\u0900-\u097f\u0b80-\u0bff][^)]*\)/g, '');

/** Telugu reads first for an inline verse, whichever field it's actually in;
 *  the other script (if there is one) follows in brackets. Never guesses —
 *  if neither side is in Telugu script, it shows what there is, no bracket.
 *  Tamil and Sanskrit scripts in brackets are omitted per user preference. */
function teluguFirst(text, original) {
  let primary = text;
  let bracket = original || '';
  if (isTelugu(original) && !isTelugu(text)) {
    primary = original;
    bracket = text;
  }
  if (/[஀-௿\u0900-\u097f]/.test(bracket)) {
    bracket = '';
  }
  return { primary, bracket };
}

export function ReadingText({ c, notes, shlokas = [], roman = false, typeLabel = (x) => x, headings = {} }) {
  const blocks = [];
  let para = [];
  // notes.split('\n') walks line by line, but a moolam/para heading belongs
  // to a whole paragraph (a \n\n-separated group, same indexing as the
  // backend's notes_headings) — a paragraph can still span several `blocks`
  // entries here (a verse line forces its own block), so the heading is
  // only attached once, to that paragraph's first block.
  let paraIndex = 0;
  let paraStarted = false;
  const markHeadingIfFirst = () => {
    if (!paraStarted) {
      const h = headings[paraIndex];
      if (h) blocks.push({ kind: 'heading', text: h });
      paraStarted = true;
    }
  };
  const flush = () => { if (para.length) { markHeadingIfFirst(); blocks.push({ kind: 'p', text: para.join(' ') }); para = []; } };
  for (const raw of (notes || '').split('\n')) {
    const line = raw.trim();
    if (!line) { flush(); paraIndex += 1; paraStarted = false; continue; }
    const whole = line.match(SHLOKA_LINE);
    if (whole) {
      flush();
      markHeadingIfFirst();
      const meta = shlokas.find((s) => (s.text || '').trim() === whole[1].trim());
      blocks.push({ kind: 'verse', text: whole[1], original: '', type: typeLabel(meta?.type) });
      continue;
    }
    const inline = [...line.matchAll(SHLOKA_MARK)];
    if (inline.length) {
      flush();
      markHeadingIfFirst();
      const parts = [];
      let last = 0;
      for (const m of inline) {
        if (m.index > last) parts.push({ kind: 'text', text: line.slice(last, m.index) });
        parts.push({ kind: 'verse', text: m[1], original: '' });
        last = m.index + m[0].length;
      }
      if (last < line.length) parts.push({ kind: 'text', text: line.slice(last) });
      blocks.push({ kind: 'p-inline', parts });
      continue;
    }
    para.push(stripUnwantedBrackets(line).replace(/\*\*/g, ''));
  }
  flush();
  // Bigger, bold, near-black for the notes body, by request — detected verses
  // (both the boxed ones, a separate component entirely, and inline ones
  // right below) must stay exactly as they already were, not inherit this.
  const baseStyle = roman ? { fontFamily: F.ui, fontSize: 16.5, lineHeight: 28 } : T.readBig;
  const bodyColor = roman ? c.ink : '#140F0A';
  return (
    <View style={{ gap: S.l }}>
      {blocks.map((b, i) => {
        if (b.kind === 'heading') return (
          <Text key={i} selectable style={{ fontFamily: F.readBold, fontSize: 19, color: c.kumkum, marginBottom: -S.s }}>{b.text}</Text>
        );
        if (b.kind === 'verse') return <VerseBlock key={i} c={c} text={b.text} original={b.original} type={b.type} />;
        if (b.kind === 'p-inline') return (
          <Text key={i} selectable style={[baseStyle, { color: bodyColor }]}>
            {b.parts.map((p, j) => {
              if (p.kind === 'text') return stripUnwantedBrackets(p.text);
              const { primary, bracket } = teluguFirst(p.text, p.original);
              return (
                <Text key={j} style={{ fontFamily: F.readBold, fontSize: T.readBig.fontSize, color: c.brass }}>
                  {primary}{bracket ? ` (${bracket})` : ''}
                </Text>
              );
            })}
          </Text>
        );
        return <Text key={i} selectable style={[baseStyle, { color: bodyColor }]}>{stripUnwantedBrackets(b.text)}</Text>;
      })}
    </View>
  );
}

/** Replaces the old Cancel/OK confirm() for export — that overloaded Cancel
 *  to mean "plain" and OK to mean "with timestamps", which read as "cancel
 *  the export" to anyone not told otherwise. This is an explicit choice
 *  (radio buttons) plus a rename field, with one clearly-labelled action. */
export function ExportDialog({ c, t, visible, defaultFileName, onCancel, onGenerate }) {
  const [fileName, setFileName] = useState(defaultFileName || '');
  const [withTimestamps, setWithTimestamps] = useState(false);

  useEffect(() => {
    if (visible) { setFileName(defaultFileName || ''); setWithTimestamps(false); }
  }, [visible, defaultFileName]);

  const options = [
    [false, t('exportPlain')],
    [true, t('exportWithTimestamps')],
  ];

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <Pressable style={st.dialogBackdrop} onPress={onCancel}>
        <Pressable style={[st.dialogCard, { backgroundColor: c.bg, borderColor: c.line }]} onPress={(e) => e.stopPropagation()}>
          <Text style={[isTelugu(t('exportTimestampTitle')) ? T.titleTe : T.title, { color: c.ink }]}>{t('exportTimestampTitle')}</Text>

          <Text style={[T.label, { color: c.muted, marginTop: S.l, marginBottom: S.xs }]}>{t('exportFileName')}</Text>
          <TextInput
            value={fileName}
            onChangeText={setFileName}
            placeholder={t('exportFileNamePlaceholder')}
            placeholderTextColor={c.muted}
            style={[st.dialogInput, { color: c.ink, borderColor: c.line, backgroundColor: c.surface }, isTelugu(fileName) && { fontFamily: F.read }]}
          />

          <View style={{ marginTop: S.l, gap: S.s }}>
            {options.map(([val, label]) => (
              <Pressable
                key={label} onPress={() => setWithTimestamps(val)}
                accessibilityRole="radio" accessibilityState={{ selected: withTimestamps === val }}
                style={st.radioRow}
              >
                <View style={[st.radioOuter, { borderColor: withTimestamps === val ? c.kumkum : c.line }]}>
                  {withTimestamps === val && <View style={[st.radioInner, { backgroundColor: c.kumkum }]} />}
                </View>
                <Text style={[isTelugu(label) ? T.body : T.body, { color: c.ink }, isTelugu(label) && { fontFamily: F.read, fontSize: 15 }]}>{label}</Text>
              </Pressable>
            ))}
          </View>

          <Text style={[T.caption, { color: c.muted, marginTop: S.m }, isTelugu(t('exportTimestampHint')) && { fontFamily: F.read, fontSize: 13 }]}>{t('exportTimestampHint')}</Text>

          <View style={{ flexDirection: 'row', gap: S.s, marginTop: S.xl }}>
            <Button c={c} label={t('cancel')} variant="quiet" onPress={onCancel} style={{ flex: 1 }} />
            <Button c={c} label={t('generate')} variant="primary" disabled={!fileName.trim()}
              onPress={() => onGenerate({ fileName: fileName.trim(), withTimestamps })} style={{ flex: 1 }} />
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const st = StyleSheet.create({
  column: { width: '100%', maxWidth: S.maxWidth, alignSelf: 'center', paddingHorizontal: S.gutter },
  dialogBackdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', alignItems: 'center', justifyContent: 'center', padding: S.xl },
  dialogCard: { width: '100%', maxWidth: 420, borderRadius: R.panel, borderWidth: 1, padding: S.xl },
  dialogInput: { minHeight: 48, borderRadius: R.control, borderWidth: 1, paddingHorizontal: S.l, fontSize: 16 },
  radioRow: { flexDirection: 'row', alignItems: 'center', gap: S.s, paddingVertical: S.xs },
  radioOuter: { width: 22, height: 22, borderRadius: 11, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
  radioInner: { width: 12, height: 12, borderRadius: 6 },
  button: {
    minHeight: 52, paddingHorizontal: S.xl, borderRadius: R.control, borderWidth: 1,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: S.s,
  },
  iconButton: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  tile: { flexDirection: 'row', alignItems: 'center', gap: S.l, padding: S.xl, borderRadius: R.panel, minHeight: 84 },
  tileHero: {
    minHeight: 112,
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOpacity: 0.28, shadowRadius: 18, shadowOffset: { width: 0, height: 10 } },
      android: { elevation: 6 },
      default: {},
    }),
  },
  tileRing: { width: 52, height: 52, borderRadius: 26, borderWidth: 1, alignItems: 'center', justifyContent: 'center' },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 9, paddingVertical: 3, borderRadius: R.pill, borderWidth: 1 },
  chipBig: { gap: 8, paddingHorizontal: 16, paddingVertical: 8, borderWidth: 1.5 },
  row: { flexDirection: 'row', alignItems: 'center', gap: S.m, paddingVertical: S.m, minHeight: 72 },
  rowMark: { width: 46, height: 46, borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, alignItems: 'center', justifyContent: 'center' },
  verse: { borderLeftWidth: 2, paddingVertical: S.m, paddingHorizontal: S.l, borderRadius: 4 },
});
