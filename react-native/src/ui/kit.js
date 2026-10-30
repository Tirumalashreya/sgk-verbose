// Shared components — implements DESIGN.md §5. Screens compose only these.
import React, { useEffect, useRef } from 'react';
import {
  View, Text, Pressable, Image, ScrollView, Animated, Easing, StyleSheet, Platform, AccessibilityInfo,
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

export function Chip({ c, tone = 'neutral', icon, children }) {
  const color = { neutral: c.muted, review: c.review, ok: c.leaf, live: c.turmeric, error: c.kumkumText }[tone];
  return (
    <View style={[st.chip, { borderColor: color }]}>
      {icon && <Icon name={icon} size={13} color={color} strokeWidth={2} />}
      <Text style={[T.caption, { color, letterSpacing: 0.4, fontSize: 11.5 }, isTelugu(children) && { fontFamily: F.readMed, fontSize: 12 }]}>{children}</Text>
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
  const unresolved = s.asr_report?.uncertain?.length || 0;
  return s.needs_manual_review || unresolved > 0 ? 'review' : 'ready';
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
                width: 10, height: 10, borderRadius: 5,
                backgroundColor: isDone ? c.turmeric : isActive ? c.brassBright : 'transparent',
                borderWidth: 1.5, borderColor: isDone || isActive ? c.turmeric : c.line,
                opacity: isActive ? pulse.interpolate({ inputRange: [0, 1], outputRange: [0.55, 1] }) : 1,
              }} />
              <View style={{ flex: 1, height: 1.5, backgroundColor: i === stages.length - 1 ? 'transparent' : (isDone ? c.turmeric : c.line) }} />
            </View>
            <Text numberOfLines={1} style={[T.caption, { color: isActive ? c.brassBright : isDone ? c.inkSoft : c.muted, marginTop: 6, fontSize: 10, letterSpacing: 0.3 }, isTelugu(labels[key]) && { fontFamily: F.read, fontSize: 10.5 }]}>{labels[key]}</Text>
          </View>
        );
      })}
    </View>
  );
}

/** A verse on its own line: Telugu as spoken, verified original beneath. */
export function VerseBlock({ c, text, original, reference, type }) {
  const isTamil = /[஀-௿]/.test(original || '');
  const isDev = /[ऀ-ॿ]/.test(original || '');
  const [origText, refText] = (original || '').split(' · ');
  return (
    <View style={[st.verse, { borderLeftColor: c.brass, backgroundColor: c.surface }]} accessibilityRole="text">
      {!!type && <Overline c={c} style={{ marginBottom: 6 }}>{type}</Overline>}
      <Text selectable style={[T.verse, { color: c.ink }]}>{text}</Text>
      {!!origText && (
        <Text selectable style={[isTamil ? T.verseTa : isDev ? T.verseDev : T.verse, { color: c.inkSoft, marginTop: 6 }]}>{origText}</Text>
      )}
      {!!(refText || reference) && (
        <View style={{ flexDirection: 'row', marginTop: 8 }}>
          {/* The number alone (e.g. "…1062") reads as a cryptic code — say plainly that it's
             a real pasuram checked against the source collection, not a guess or an id. */}
          <Chip c={c} tone="ok" icon="check">{`ధృవీకరించిన పాశురం · ${refText || reference}`}</Chip>
        </View>
      )}
    </View>
  );
}

/** The notes: paragraphs of the verbatim transcript, verses where spoken.
 *  A verse long enough to stand on its own line becomes its own boxed block
 *  (SHLOKA_LINE); a one- or two-word verse sits inline inside its sentence
 *  instead (SHLOKA_MARK — the same markup, just not alone on its line). */
const SHLOKA_LINE = /^\*\*"(.+?)"\*\*(?:\s*\(([^)]*)\))?$/;
const SHLOKA_MARK = /\*\*"(.+?)"\*\*(?:\s*\(([^)]*)\))?/g;

/** Telugu reads first for an inline verse, whichever field it's actually in;
 *  the other script (if there is one) follows in brackets. Never guesses —
 *  if neither side is in Telugu script, it shows what there is, no bracket. */
function teluguFirst(text, original) {
  if (isTelugu(text)) return { primary: text, bracket: original || '' };
  if (isTelugu(original)) return { primary: original, bracket: text };
  return { primary: text, bracket: '' };
}

export function ReadingText({ c, notes, shlokas = [], roman = false, typeLabel = (x) => x }) {
  const blocks = [];
  let para = [];
  const flush = () => { if (para.length) { blocks.push({ kind: 'p', text: para.join(' ') }); para = []; } };
  for (const raw of (notes || '').split('\n')) {
    const line = raw.trim();
    if (!line) { flush(); continue; }
    const whole = line.match(SHLOKA_LINE);
    if (whole) {
      flush();
      const meta = shlokas.find((s) => (s.text || '').trim() === whole[1].trim());
      blocks.push({ kind: 'verse', text: whole[1], original: whole[2], type: typeLabel(meta?.type) });
      continue;
    }
    const inline = [...line.matchAll(SHLOKA_MARK)];
    if (inline.length) {
      flush();
      const parts = [];
      let last = 0;
      for (const m of inline) {
        if (m.index > last) parts.push({ kind: 'text', text: line.slice(last, m.index) });
        parts.push({ kind: 'verse', text: m[1], original: m[2] });
        last = m.index + m[0].length;
      }
      if (last < line.length) parts.push({ kind: 'text', text: line.slice(last) });
      blocks.push({ kind: 'p-inline', parts });
      continue;
    }
    para.push(line.replace(/\*\*/g, ''));
  }
  flush();
  const baseStyle = roman ? { fontFamily: F.ui, fontSize: 16.5, lineHeight: 28 } : T.read;
  return (
    <View style={{ gap: S.l }}>
      {blocks.map((b, i) => {
        if (b.kind === 'verse') return <VerseBlock key={i} c={c} text={b.text} original={b.original} type={b.type} />;
        if (b.kind === 'p-inline') return (
          <Text key={i} selectable style={[baseStyle, { color: c.ink }]}>
            {b.parts.map((p, j) => {
              if (p.kind === 'text') return p.text;
              const { primary, bracket } = teluguFirst(p.text, p.original);
              return (
                <Text key={j} style={{ fontFamily: F.readMed, color: c.brass }}>
                  {primary}{bracket ? ` (${bracket})` : ''}
                </Text>
              );
            })}
          </Text>
        );
        return <Text key={i} selectable style={[baseStyle, { color: c.ink }]}>{b.text}</Text>;
      })}
    </View>
  );
}

const st = StyleSheet.create({
  column: { width: '100%', maxWidth: S.maxWidth, alignSelf: 'center', paddingHorizontal: S.gutter },
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
  row: { flexDirection: 'row', alignItems: 'center', gap: S.m, paddingVertical: S.m, minHeight: 72 },
  rowMark: { width: 46, height: 46, borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, alignItems: 'center', justifyContent: 'center' },
  verse: { borderLeftWidth: 2, paddingVertical: S.m, paddingHorizontal: S.l, borderRadius: 4 },
});
