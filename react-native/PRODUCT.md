# PRODUCT.md — Shravaṇam (SGKS Notes)

Durable product truth. Read before changing any screen. Visual rules live in DESIGN.md.

## Purpose
Turn the Telugu pravachanams of **Sriman Satuluri Gopāla Krishnamāchārya** into an
**exact, word-for-word written record** that devotees can read, keep, share and publish.
The app listens (live in the hall, an uploaded file, or a YouTube link) and produces notes
that are the complete verbatim transcript — never a rewrite.

## Audience
- Devotees attending or following the discourses; many read Telugu fluently, some prefer the
  Roman transliteration. Ages range widely — many are older readers on phones.
- Volunteers who publish the notes and need to trust every word.

## Operating context
- Live: inside a hall or home satsang, phone held or placed near the speaker, often for 1–2 hours.
- Reading: later, at home, on a phone at night or a laptop by day; long Telugu text.
- Mixed languages: Telugu narration with Sanskrit shlokas and Tamil pasurams (Divya Prabandham).

## Non-negotiables (product truths)
1. **The notes are the full verbatim transcript.** No summarising, paraphrasing or invented
   headings inside the notes. The summary is optional, separate and clearly labelled.
2. **Verses appear exactly where spoken**, on their own line, with the original script only when
   it is verified (Devanagari by direct conversion; Tamil only when matched in the Divya Prabandham).
3. **Never hide uncertainty.** Spots where the two listeners disagreed and the judge could not
   decide, or that need review, are visible — not silently guessed.
4. **One recording → one set of notes.**
5. **Works on iPhone, Android and web** from one codebase (Expo).

## Brand voice
Reverent, warm, calm, precise. Telugu-first, English as a gentle aid. Short, plain labels
("Record", "Upload", "Notes", "Verses") — no hype, no emoji in interface text.

## Evidence that shaped the product
- Verbatim fidelity is verified in code (validation step reproduces the transcript exactly).
- Two independent listeners (Sarvam V4 + Gemini) with an audio judge produced the most faithful
  transcripts in testing; Whisper and open models dropped speech and were removed.
