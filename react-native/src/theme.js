// Design tokens — the implementation of DESIGN.md. Change DESIGN.md first.

export const palettes = {
  // Hall: the pravachanam stage — indigo velvet, marigold gold, maroon cloth,
  // cream (Intro, Live, and reading in dark mode). Taken from the intro photo.
  hall: {
    mode: 'hall',
    bg: '#0E0B1F', surface: '#17132D', raised: '#211C3D',
    ink: '#F5ECDF', inkSoft: '#D8CCBC', muted: '#A39AB8', line: '#332C52',
    brass: '#E3B35C', brassBright: '#F2C877',
    kumkum: '#8E1E3A', kumkumDeep: '#5E1226', kumkumText: '#F08A9C',
    turmeric: '#EE9A3A', leaf: '#88C49C', review: '#EAC060',
    onFill: '#F5ECDF',          // text on maroon / dark fills
    onBrass: '#0E0B1F',         // text on gold fills
    kolam: 'rgba(227,179,92,0.07)',
  },
  // Manuscript: the app's one everyday look — warm ivory, indigo ink (the velvet),
  // maroon (the cloth) and marigold gold, in sync with the intro photo.
  manuscript: {
    mode: 'manuscript',
    bg: '#F4EEE2', surface: '#FCF8F0', raised: '#FFFEFA',
    ink: '#1E1A36', inkSoft: '#433D5C', muted: '#625C74', line: '#DCCFB6',
    brass: '#7E5A12', brassBright: '#B8862C',
    kumkum: '#8A1C36', kumkumDeep: '#5E1226', kumkumText: '#8A1C36',
    turmeric: '#A3570F', leaf: '#2C6A43', review: '#875800',
    onFill: '#FFFCF6',
    onBrass: '#FFFEFA',
    kolam: 'rgba(30,26,54,0.045)',
  },
};

export const F = {
  display: 'Marcellus_400Regular',
  displayTe: 'Suravaram_400Regular',
  read: 'NotoSerifTelugu_400Regular',
  readMed: 'NotoSerifTelugu_500Medium',
  readBold: 'NotoSerifTelugu_700Bold',
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
  // The notes body specifically — bigger and bold, by request. Detected
  // verses must stay exactly as they already were, so this is deliberately
  // its own token, not a change to `read` (which other screens still use).
  readBig:   { fontFamily: F.readBold, fontSize: 24, lineHeight: 42 },
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

/** Theme for the current screen: one light look everywhere. Only the Intro, which
 *  sits on the photo, uses the dark Hall palette directly. */
export function useTheme(forceMode) {
  return palettes[forceMode || 'manuscript'];
}

export const ACHARYA = 'Satluri Gopāla Krishnamāchārya';
export const ACHARYA_TE = 'సాత్లూరి గోపాల కృష్ణమాచార్య';
export const acharyaLogo = require('../assets/acharya.png');           // the app logo / icon photo
export const acharyaPhoto = require('../assets/acharya_home.png');
export const acharyaIntroPhoto = require('../assets/acharya_pravachanam.png');
