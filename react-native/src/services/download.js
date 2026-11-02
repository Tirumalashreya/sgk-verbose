// Export notes as PDF / Word. Phones: native PDF + share sheet. Web: print dialog / file download.
import { isWeb, notify } from './platform';

const ACHARYA = 'Satluri Gopāla Krishnamāchārya';

const esc = (t) => String(t ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const isTelugu = (s) => /[ఀ-౿]/.test(s || '');

// A verse long enough for its own line (SHLOKA_LINE) vs one short enough to
// sit inline inside a sentence (SHLOKA_MARK, the same markup, unanchored) —
// mirrors react-native/src/ui/kit.js's ReadingText, since both parse the
// same notes text independently.
const SHLOKA_LINE = /^\*\*"(.+?)"\*\*(?:\s*\(([^)]*)\))?$/;
const SHLOKA_MARK = /\*\*"(.+?)"\*\*(?:\s*\(([^)]*)\))?/g;

function teluguFirst(text, original) {
  if (isTelugu(text)) return { primary: text, bracket: original || '' };
  if (isTelugu(original)) return { primary: original, bracket: text };
  return { primary: text, bracket: '' };
}

function buildHTML(session, forPrint = false, titleOverride) {
  const title    = esc(titleOverride || session.title || 'Pravachanam');
  const notes    = session.notes || session.transcript || '';   // the notes are the full verbatim transcript
  const headings = session.notes_headings || {};   // {paragraph index -> "మూలం N"}, keyed same as kit.js's ReadingText

  // Shlokas render inline, right where they were spoken (below) — there's no
  // separate summary list here, so a verse is never shown twice on the page.

  // A moolam/para heading belongs to a whole paragraph (a \n\n-separated
  // group, same indexing as the backend's notes_headings), tracked here by
  // counting blank lines — mirrors kit.js's ReadingText exactly.
  let paraIndex = 0, paraStarted = false;
  const headingHTML = () => {
    if (paraStarted) return '';
    paraStarted = true;
    const h = headings[paraIndex];
    return h ? `<h3 class="moolam-heading">${esc(h)}</h3>` : '';
  };
  const noteBlocks = notes.split('\n').map(line => {
    const t = line.trim();
    if (!t) { paraIndex += 1; paraStarted = false; return '<br/>'; }
    const whole = t.match(SHLOKA_LINE);
    if (whole) return `${headingHTML()}<p class="shloka-text"><strong>"${esc(whole[1])}"</strong>${whole[2] ? `<br/><span class="shloka-original">${esc(whole[2])}</span>` : ''}</p>`;
    const inline = [...t.matchAll(SHLOKA_MARK)];
    if (!inline.length) return `${headingHTML()}<p>${esc(t)}</p>`;
    let html = '', last = 0;
    for (const m of inline) {
      html += esc(t.slice(last, m.index));
      const { primary, bracket } = teluguFirst(m[1], m[2]);
      html += `<span class="verse-inline">${esc(primary)}${bracket ? ` (${esc(bracket)})` : ''}</span>`;
      last = m.index + m[0].length;
    }
    html += esc(t.slice(last));
    return `${headingHTML()}<p>${html}</p>`;
  }).join('');

  return `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40">
<head>
  <meta charset="utf-8"/>
  <title>${title}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+Telugu&display=swap');
    body        { font-family: 'Noto Serif Telugu', serif; margin: 40px; color: #2b2419; line-height: 1.8; }
    h1          { font-size: 24px; color: #571f19; margin-bottom: 4px; }
    .meta       { font-size: 12px; color: #9a8c70; margin-bottom: 20px; }
    .summary    { background: #fdf7ee; border-left: 3px solid #e0843b; padding: 10px 14px; margin-bottom: 28px; font-size: 14px; color: #5b513f; border-radius: 4px; }
    .section    { margin-bottom: 36px; }
    .section-title { font-size: 13px; letter-spacing: 2px; color: #b58a3c; text-transform: uppercase; border-bottom: 1px solid #e3d4b2; padding-bottom: 6px; margin-bottom: 16px; }
    h3          { font-size: 16px; color: #7a2e25; margin: 20px 0 6px; }
    .moolam-heading { font-size: 19px; font-weight: 700; color: #8A1C36; margin: 24px 0 8px; }
    /* Notes body: bigger, bold, near-black, by request. Detected verses (the
       boxed ones below and the inline ones mixed into these paragraphs) are
       explicitly kept at their original size/weight, not inherited from this. */
    p           { font-size: 24px; font-weight: 700; color: #140F0A; line-height: 1.7; margin: 0 0 16px; }
    .shloka     { border-left: 2px solid #e0843b; padding-left: 14px; margin-bottom: 22px; }
    .shloka-label { font-size: 10px; letter-spacing: 1.5px; color: #b58a3c; display: block; margin-bottom: 4px; }
    .shloka-text  { font-size: 24px; font-weight: 700; color: #5b513f; margin: 0 0 6px; }
    .shloka-original { font-size: 15px; font-weight: 400; color: #7a2e25; margin: 0; }
    .verse-inline { font-size: 24px; font-weight: 700; color: #7a2e25; }
    ${forPrint ? '@media print { body { margin: 20px; } }' : ''}
  </style>
</head>
<body>
  <h1>${title}</h1>
  <p class="meta">${ACHARYA}</p>

  ${notes ? `
  <div class="section">
    <div class="section-title">Notes</div>
    ${noteBlocks}
  </div>` : ''}
</body>
</html>`;
}

const fileName = (session, ext, customName) =>
  `${(customName || session.title || 'pravachanam').replace(/[^a-z0-9\u0C00-\u0C7F ]/gi, '_').trim() || 'pravachanam'}.${ext}`;

export async function downloadPDF(session, customName) {
  const html = buildHTML(session, true, customName);
  if (isWeb) {
    const win = window.open('', '_blank', 'width=800,height=900');
    if (!win) { notify('Pop-up blocked', 'Allow pop-ups for this site to save the PDF.'); return; }
    win.document.write(html);
    win.document.close();
    win.onload = () => setTimeout(() => { win.focus(); win.print(); }, 800);
    return;
  }
  const Print = await import('expo-print');
  const Sharing = await import('expo-sharing');
  const FileSystemLegacy = await import('expo-file-system/legacy');
  const { uri } = await Print.printToFileAsync({ html });
  const destUri = FileSystemLegacy.cacheDirectory + fileName(session, 'pdf', customName);
  // Both a file-to-file copy (the new File/Directory class API, then the
  // legacy copyAsync) failed reading expo-print's own output on Android, with
  // the real reason finally visible: "java.io.IOException: Location
  // '.../cache/Print/<uuid>.pdf' isn't readable." — the file expo-print just
  // wrote, unreadable to a direct file-copy immediately after. Reading it as
  // base64 text instead of copying the file handle goes through a different
  // native code path (a content stream, not a raw file-to-file copy), which
  // Expo's own community has used as a workaround for exactly this.
  const base64 = await FileSystemLegacy.readAsStringAsync(uri, { encoding: 'base64' });
  await FileSystemLegacy.writeAsStringAsync(destUri, base64, { encoding: 'base64' });
  await Sharing.shareAsync(destUri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf', dialogTitle: fileName(session, 'pdf', customName) });
}

export async function downloadDOC(session, customName) {
  const html = buildHTML(session, false, customName);
  if (isWeb) {
    const blob = new Blob(['\ufeff', html], { type: 'application/msword;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName(session, 'doc', customName);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return;
  }
  const { File, Paths } = await import('expo-file-system');
  const Sharing = await import('expo-sharing');
  const file = new File(Paths.cache, fileName(session, 'doc', customName));
  if (file.exists) file.delete();
  file.create();
  await file.write('\ufeff' + html);   // SDK 58: File.write() is async now \u2014 unawaited, the share below could fire early
  await Sharing.shareAsync(file.uri, { mimeType: 'application/msword', UTI: 'com.microsoft.word.doc', dialogTitle: fileName(session, 'doc', customName) });
}
