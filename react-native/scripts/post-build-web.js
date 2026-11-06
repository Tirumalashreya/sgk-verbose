const fs = require('fs');
const path = require('path');

const distDir = path.join(__dirname, '..', 'dist');
const htmlFile = path.join(distDir, 'index.html');

if (fs.existsSync(htmlFile)) {
  let html = fs.readFileSync(htmlFile, 'utf8');
  
  const headMeta = `
  <link rel="icon" type="image/x-icon" href="/favicon.ico" />
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
  <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
  <link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png" />
  <link rel="icon" type="image/png" sizes="512x512" href="/icon-512.png" />
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
  <link rel="manifest" href="/manifest.json" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="apple-mobile-web-app-title" content="SGK'S Notes" />
  <meta name="application-name" content="SGK'S Notes" />
  <meta name="theme-color" content="#2a2340" />
`;

  // Avoid duplicate injection
  if (!html.includes('/apple-touch-icon.png')) {
    html = html.replace('</head>', `${headMeta}\n</head>`);
    fs.writeFileSync(htmlFile, html, 'utf8');
    console.log('[post-build] Injected icon, touch-icon, and manifest meta tags into dist/index.html');
  }
} else {
  console.warn('[post-build] dist/index.html not found');
}
