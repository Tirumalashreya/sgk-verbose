// Export notes as PDF / Word. Phones: native PDF + share sheet. Web: print dialog / file download.
import { isWeb, notify } from './platform';

const ACHARYA = 'Satluri Gopāla Krishnamāchārya';

const esc = (t) => String(t ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function buildHTML(session, forPrint = false) {
  const title   = esc(session.title || 'Pravachanam');
  const summary = esc(session.summary || '');
  const notes   = session.notes || session.transcript || '';   // the notes are the full verbatim transcript
  const shlokas = session.shlokas || [];

  const shlokaRows = shlokas.map((s, i) => `
    <div class="shloka">
      <span class="shloka-label">${esc((s.type || 'Shloka').toUpperCase())} ${i + 1}${s.language ? ' · ' + esc(s.language) : ''}</span>
      <p class="shloka-text">${esc(s.text)}</p>
      ${s.original ? `<p class="shloka-original">${esc(s.original)}</p>` : ''}
    </div>
  `).join('');

  const noteBlocks = notes.split('\n').map(line => {
    const t = line.trim();
    if (!t) return '<br/>';
    const sm = t.match(/^\*\*"(.+?)"\*\*(?:\s*\(([^)]*)\))?$/);
    if (sm) return `<p class="shloka-text"><strong>"${esc(sm[1])}"</strong>${sm[2] ? `<br/><span class="shloka-original">${esc(sm[2])}</span>` : ''}</p>`;
    return `<p>${esc(t)}</p>`;
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
    p           { font-size: 15px; margin: 0 0 12px; }
    .shloka     { border-left: 2px solid #e0843b; padding-left: 14px; margin-bottom: 22px; }
    .shloka-label { font-size: 10px; letter-spacing: 1.5px; color: #b58a3c; display: block; margin-bottom: 4px; }
    .shloka-text  { font-size: 15px; color: #5b513f; margin: 0 0 6px; }
    .shloka-original { font-size: 15px; color: #7a2e25; margin: 0; }
    ${forPrint ? '@media print { body { margin: 20px; } }' : ''}
  </style>
</head>
<body>
  <h1>${title}</h1>
  <p class="meta">${ACHARYA}</p>
  ${summary ? `<div class="summary">${summary}</div>` : ''}

  ${notes ? `
  <div class="section">
    <div class="section-title">Notes</div>
    ${noteBlocks}
  </div>` : ''}

  ${shlokas.length > 0 ? `
  <div class="section">
    <div class="section-title">Shlokas & Pasurams (${shlokas.length})</div>
    ${shlokaRows}
  </div>` : ''}
</body>
</html>`;
}

const fileName = (session, ext) =>
  `${(session.title || 'pravachanam').replace(/[^a-z0-9\u0C00-\u0C7F ]/gi, '_').trim() || 'pravachanam'}.${ext}`;

export async function downloadPDF(session) {
  const html = buildHTML(session, true);
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
  const { uri } = await Print.printToFileAsync({ html });
  await Sharing.shareAsync(uri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf', dialogTitle: fileName(session, 'pdf') });
}

export async function downloadDOC(session) {
  const html = buildHTML(session, false);
  if (isWeb) {
    const blob = new Blob(['\ufeff', html], { type: 'application/msword;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName(session, 'doc');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return;
  }
  const { File, Paths } = await import('expo-file-system');
  const Sharing = await import('expo-sharing');
  const file = new File(Paths.cache, fileName(session, 'doc'));
  if (file.exists) file.delete();
  file.create();
  file.write('\ufeff' + html);
  await Sharing.shareAsync(file.uri, { mimeType: 'application/msword', UTI: 'com.microsoft.word.doc', dialogTitle: fileName(session, 'doc') });
}
