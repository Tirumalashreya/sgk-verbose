const ACHARYA = 'Satluri Gopāla Krishnamāchārya';

function buildHTML(session, forPrint = false) {
  const title   = session.title    || 'Pravachanam';
  const summary = session.summary  || '';
  const notes   = session.notes    || session.transcript || '';
  const transcript = session.transcript || '';
  const shlokas = session.shlokas  || [];

  const shlokaRows = shlokas.map((s, i) => `
    <div class="shloka">
      <span class="shloka-label">${(s.type || 'Shloka').toUpperCase()} ${i + 1}${s.language ? ' · ' + s.language : ''}</span>
      <p class="shloka-text">${s.text || ''}</p>
      ${s.original ? `<p class="shloka-original">${s.original}</p>` : ''}
    </div>
  `).join('');

  const noteBlocks = notes.split('\n').map(line => {
    const t = line.trim();
    if (!t) return '<br/>';
    const hm = t.match(/^\*{1,2}(.+?)\*{1,2}$/);
    if (hm) return `<h3>${hm[1].trim()}</h3>`;
    return `<p>${t}</p>`;
  }).join('');

  const transcriptBlocks = transcript.split(/[।\n]/)
    .filter(l => l.trim().length > 3)
    .map(l => `<p>${l.trim()}</p>`)
    .join('');

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

  ${transcript ? `
  <div class="section">
    <div class="section-title">Transcript</div>
    ${transcriptBlocks}
  </div>` : ''}

  ${shlokas.length > 0 ? `
  <div class="section">
    <div class="section-title">Shlokas & Pasurams (${shlokas.length})</div>
    ${shlokaRows}
  </div>` : ''}
</body>
</html>`;
}

export function downloadPDF(session) {
  const html = buildHTML(session, true);
  const win = window.open('', '_blank', 'width=800,height=900');
  if (!win) { alert('Allow popups to download PDF'); return; }
  win.document.write(html);
  win.document.close();
  win.onload = () => {
    setTimeout(() => {
      win.focus();
      win.print();
    }, 800);
  };
}

export function downloadDOC(session) {
  const html = buildHTML(session, false);
  const blob = new Blob(['﻿', html], { type: 'application/msword;charset=utf-8' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `${(session.title || 'pravachanam').replace(/[^a-z0-9ఀ-౿ ]/gi, '_')}.doc`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
