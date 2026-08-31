# Shravaṇam — SGKS Pravachanam App (React Native / Expo)

A transcription companion for the Telugu spiritual discourses of **Satluri Gopāla
Krishnamāchārya**. Its core job: **transcribe audio** — either *pasted* (a YouTube /
audio link to a recorded pravachanam) or *recorded live* in the hall — into a
**Telugu transcript**. It also auto-detects Sanskrit shlokas, generates structured
notes, and answers questions like *"What did Āchārya gāru say about Dharma?"* —
every answer cited back to the moment and the shloka.

- **Generated content is always Telugu.** Transcripts, notes and shloka meanings
  are produced in Telugu.
- **The interface is bilingual.** A Telugu ⇄ English toggle (top-right of Library)
  switches all UI chrome. While the UI is in English, a small English translation
  line is shown under each Telugu transcript as an aid; in Telugu mode the screen
  shows Telugu only.
- The center button in the tab bar is **Record** (start live transcription) — it
  was previously mislabeled "Listen".

This is the **React Native (Expo)** port of the HTML prototype.

## Screens
- **Library** — the two primary transcription actions (Paste a link · Record live), a Telugu/English toggle, a resume-last card, and recent pravachanams
- **Record (Live)** — dark meditative session, animated waveform, Telugu transcript streaming in, shlokas auto-detected
- **Discourse** — Transcript / Notes / Shlokas tabs (Telugu content; English gloss when UI = English)
- **Ask** — grounded Q&A that cites the moment + shloka

## Run it
```bash
cd react-native
npm install          # or: yarn
npx expo start       # press i (iOS), a (Android), or scan the QR in Expo Go
```
Requires Node 18+ and the [Expo Go](https://expo.dev/go) app (or a simulator).

## Project structure
```
App.js                     # font loading + screen routing
app.json                   # Expo config (icon/splash use the Acharya photo)
assets/acharya.png         # portrait — used in header, live card, discourse
src/
  theme.js                 # colors (C), font names (F), ACHARYA, photo
  i18n.js                  # EN/TE UI strings + makeT(lang) translator
  data.js                  # discourses, live transcript, notes, shlokas, answers
  components/
    Waveform.js            # 28-bar equaliser (Animated, native driver)
    BottomNav.js           # Library · Record · Ask tab bar
  screens/
    LibraryScreen.js
    LiveScreen.js
    DiscourseScreen.js
    AskScreen.js
```

## Notes & next steps
- **Navigation** is a lightweight `useState` router (no extra deps). For deep
  links / gestures, drop in `@react-navigation/native` + a stack/tab navigator —
  the screens already take a `go(screenName)` prop.
- **The AI is mocked.** `src/data.js` holds canned transcripts and answers. To go
  live, wire:
  - *Live transcription* → on-device or streaming ASR (e.g. `expo-av` to record +
    a Telugu/Sanskrit speech-to-text endpoint).
  - *YouTube import* → fetch captions / send audio to your transcription service.
  - *Ask* → send the question + retrieved transcript chunks to an LLM and render
    the returned shloka + citation in the existing message shape
    (`{ text, shloka, cite }`).
- **Fonts**: Marcellus (display), Hanken Grotesk (UI), Noto Serif Devanagari &
  Noto Serif Telugu (scripts) via `@expo-google-fonts/*`.
- **Shlokas** are public-domain (Bhagavad Gītā, Mahābhārata).

## Image rights
`assets/acharya.png` is the photograph you provided. Confirm you have permission
from the SGKS organisation to use the Acharya's likeness and name before
publishing to the App Store / Play Store.
