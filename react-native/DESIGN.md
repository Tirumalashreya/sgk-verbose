# DESIGN.md — SGKS Notes visual system

Direction: **rich & immersive, the pravachanam stage.** The colours come from the intro photo:
indigo velvet behind the Acharya, marigold gold of the garland, the maroon cloth, cream — then, when reading, calm
and clear like a well-printed palm-leaf manuscript. Tokens live in `src/theme.js`; this file is
the contract they implement.

## 1. Visual theme
- **One light look, everywhere.** *Manuscript* (warm ivory, indigo ink, maroon, marigold gold —
  the colours of the intro photo) is used on every screen. *Hall* (dark indigo) is used only on
  the Intro, as the fade over the full-page photo.
- **Light sources, not decoration.** Warmth comes from glow (the deepam, brass edges, soft
  radial light), never from neon glows, purple gradients or drop-shadow halos.
- **Pattern sparingly.** A faint kolam dot-grid texture on large dark surfaces and a single
  temple-arch (gopuram) silhouette as an ornament. Never behind reading text.

## 2. Colour (tinted — no pure black, no pure white)
| Token | Hall (dark) | Manuscript (light) | Use |
|---|---|---|---|
| `bg` | `#0E0B1F` indigo velvet | `#F4EEE2` ivory | screen background |
| `surface` | `#17132D` | `#FCF8F0` | panels, list rows |
| `raised` | `#211C3D` | `#FFFEFA` | the one elevated element per screen |
| `ink` | `#F5ECDF` cream | `#1E1A36` indigo ink | primary text |
| `inkSoft` | `#D8CCBC` | `#433D5C` | secondary text |
| `muted` | `#A39AB8` | `#625C74` | captions (≥4.5:1 on its bg) |
| `line` | `#332C52` | `#DCCFB6` | hairlines |
| `brass` | `#E3B35C` marigold | `#7E5A12` | accents, focus, selected |
| `brassBright` | `#F2C877` | `#B8862C` | flame highlight, active state |
| `kumkum` | `#8E1E3A` maroon | `#861C36` | fill for the primary action (Record), destructive |
| `kumkumText` | `#F08A9C` lotus | `#861C36` | red *text* (e.g. a Delete label) |
| `turmeric` | `#EE9A3A` | `#A3570F` | progress, live indicators |
| `leaf` | `#88C49C` | `#2C6A43` | verified / done |
| `review` | `#EAC060` | `#875800` | needs-review badges |

Rules: text on a coloured fill uses `ink` of the *opposite* mode (never grey on colour).
`turmeric` is for bars/dots only, never text. Every text/background pair above meets WCAG AA
(checked: ≥4.5:1 text, ≥3:1 UI shapes).
Gradients only brass→turmeric or kumkum→deep-kumkum, at most one per screen.

## 3. Typography
| Role | Font | Size / line-height |
|---|---|---|
| Display (Latin) | Marcellus | 30/36, letter-spacing 0.5 |
| Display (Telugu) | Suravaram | 28/40 |
| Title | Marcellus | 21/28 |
| Reading (Telugu body) | Noto Serif Telugu 400 | 17/33 (1.95) — max 38em measure |
| Verse (Telugu line) | Noto Serif Telugu 500 | 17/32 |
| Verse original (Sanskrit) | Noto Serif Devanagari 500 | 16/30 |
| Verse original (Tamil) | Noto Serif Tamil 500 | 15/28 |
| UI label | Hanken Grotesk 600 | 13/18, letter-spacing 0.3 |
| Caption / overline | Hanken Grotesk 600 | 11/14, letter-spacing 1.2, uppercase (Latin only) |
| Body (Latin) | Hanken Grotesk 400 | 15/22 |
Hierarchy never skips a level. Telugu never uppercase/letter-spaced.

## 4. Spacing, shape, elevation
- 4-pt grid: 4, 8, 12, 16, 20, 24, 32, 40, 56. Screen gutter 20 (phone), content max-width 720.
- Radius: 10 (controls), 18 (panels), 999 (pills). One radius family per screen.
- Touch targets ≥ 44×44. Primary actions ≥ 56 tall.
- Elevation by tone (surface → raised), not shadows; one soft shadow allowed for the floating
  record control. **No cards nested in cards.**

## 5. Components
- **Action tile** — large tappable panel: icon in a brass ring, Telugu title, English hint.
  The Record tile is the hero (kumkum gradient); Upload and Link are calm surfaces.
- **Session row** — title, date, duration/verse count, status chip (Processing / Needs review /
  Ready). Swipe or long-press to delete (confirm dialog).
- **Verse block** — left brass rule 2px, Telugu line in Verse style, original script beneath in
  its own font, reference chip (e.g. "నాలాయిర దివ్య ప్రబంధం 1073") when verified.
- **Stage path** — the processing steps as a single line of small nodes that fill with turmeric
  as each step completes; current node pulses gently.
- **Deepam (3D)** — Live screen centrepiece: a brass oil lamp whose flame height, sway and glow
  follow the speaker's voice level; calm idle flicker when silent.
- **Review chip** — `review` colour, shows the count of unresolved spots; never hidden.

## 6. Motion
- Easing: `Easing.out(Easing.cubic)` for entrances (220–320 ms); `Easing.inOut(Easing.sin)` for
  breathing/ambient loops (2–4 s). **No bounce/elastic.**
- Ambient motion only where it means something: the flame (voice), the live dot, the current stage.
- Respect Reduce Motion: replace loops with static states.

## 7. Iconography & imagery
- Line icons drawn in SVG, 1.75 stroke, rounded caps, brass or ink colour.
- The Acharya's portrait appears in a brass ring (Intro, Home header, Live).
- No emoji in UI.

## 8. Do / don't
- Do: let reading screens be quiet; give long Telugu text room; show verse sources.
- Don't: grey text on colour, pure #000/#fff, purple/blue gradients, glow halos, nested cards,
  side-tab borders, headings inside the notes, decorative motion on reading screens.
