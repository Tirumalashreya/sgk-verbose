// Design tokens — the implementation of DESIGN.md. Change DESIGN.md first.
import { useColorScheme } from 'react-native';

export const palettes = {
  // Hall: lamp-lit temple at dusk (Intro, Live, and reading in dark mode)
  hall: {
    mode: 'hall',
    bg: '#120D09', surface: '#1C1510', raised: '#271D15',
    ink: '#F2E7D3', inkSoft: '#CDBEA2', muted: '#9C8B6E', line: '#3A2C20',
    brass: '#D9A84E', brassBright: '#F3C672',
    kumkum: '#B03A2B', kumkumDeep: '#7E2418', kumkumText: '#E86A57',
    turmeric: '#E9922E', leaf: '#7FB08A', review: '#E6B450',
    onFill: '#F2E7D3',          // text on kumkum / dark fills
    onBrass: '#120D09',         // text on brass fills
    kolam: 'rgba(217,168,78,0.07)',
  },
  // Manuscript: palm-leaf paper for reading by day
  manuscript: {
    mode: 'manuscript',
    bg: '#F6EEDD', surface: '#FBF5E9', raised: '#FFFDF7',
    ink: '#2A1F14', inkSoft: '#4E4131', muted: '#6E604A', line: '#E2D3B4',
    brass: '#8C6420', brassBright: '#B07D24',
    kumkum: '#9A2A1C', kumkumDeep: '#6E1D13', kumkumText: '#9A2A1C',
    turmeric: '#B8641A', leaf: '#2F6B3F', review: '#8A5A00',
    onFill: '#F6EEDD',
    onBrass: '#FFFDF7',
    kolam: 'rgba(140,100,32,0.08)',
  },
};

export const F = {
  display: 'Marcellus_400Regular',
  displayTe: 'Suravaram_400Regular',
  read: 'NotoSerifTelugu_400Regular',
  readMed: 'NotoSerifTelugu_500Medium',
  dev: 'NotoSerifDevanagari_500Medium',
  tamil: 'NotoSerifTamil_500Medium',
  ui: 'HankenGrotesk_400Regular',
  uiMed: 'HankenGrotesk_500Medium',
  uiSemi: 'HankenGrotesk_600SemiBold',
  uiBold: 'HankenGrotesk_700Bold',
};

// Type scale (DESIGN.md §3). Spread into a Text style: [T.title, { color: c.ink }]
export const T = {
  display:   { fontFamily: F.display, fontSize: 30, lineHeight: 36, letterSpacing: 0.5 },
  displayTe: { fontFamily: F.displayTe, fontSize: 28, lineHeight: 40 },
  title:     { fontFamily: F.display, fontSize: 21, lineHeight: 28 },
  titleTe:   { fontFamily: F.readMed, fontSize: 19, lineHeight: 30 },
  read:      { fontFamily: F.read, fontSize: 17, lineHeight: 33 },
  verse:     { fontFamily: F.readMed, fontSize: 17, lineHeight: 32 },
  verseDev:  { fontFamily: F.dev, fontSize: 16, lineHeight: 30 },
  verseTa:   { fontFamily: F.tamil, fontSize: 15, lineHeight: 28 },
  label:     { fontFamily: F.uiSemi, fontSize: 13, lineHeight: 18, letterSpacing: 0.3 },
  body:      { fontFamily: F.ui, fontSize: 15, lineHeight: 22 },
  caption:   { fontFamily: F.uiSemi, fontSize: 11, lineHeight: 14, letterSpacing: 1.2 },
};

export const S = { xs: 4, s: 8, m: 12, l: 16, xl: 20, xxl: 24, x3: 32, x4: 40, x5: 56, gutter: 20, maxWidth: 720 };
export const R = { control: 10, panel: 18, pill: 999 };
export const MOTION = { enter: 280, quick: 180, breathe: 2800 };

/** Theme for the current screen: reading screens follow the phone setting;
 *  immersive screens (Intro, Live) always use the Hall palette. */
export function useTheme(forceMode) {
  const scheme = useColorScheme();
  const mode = forceMode || (scheme === 'light' ? 'manuscript' : 'hall');
  return palettes[mode];
}

export const ACHARYA = 'Satluri Gopāla Krishnamāchārya';
export const ACHARYA_TE = 'సత్లూరి గోపాల కృష్ణమాచార్య';   // spelling as already used in the app — confirm
export const acharyaLogo = require('../assets/acharya.png');           // the app logo / icon photo
export const acharyaPhoto = require('../assets/acharya_home.png');
export const acharyaIntroPhoto = require('../assets/acharya_pravachanam.png');
