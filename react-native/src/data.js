// Demo content for the Shravanam app.
// Shlokas are public-domain (Bhagavad Gītā / Mahābhārata).

export const LIBRARY = [
  { id: 'dharma', glyph: 'ध', title: 'Dharma — The Inner Law', meta: 'Āchārya gāru · 21 Jun', dur: '38 min', count: '6 shlokas' },
  { id: 'bhakti', glyph: 'भ', title: 'Bhakti & Surrender', meta: 'Āchārya gāru · 18 Jun', dur: '52 min', count: '9 shlokas' },
  { id: 'karma', glyph: 'क', title: 'Karma Yoga in Daily Life', meta: 'Āchārya gāru · 14 Jun', dur: '41 min', count: '7 shlokas' },
  { id: 'atman', glyph: 'आ', title: 'The Nature of the Ātman', meta: 'Āchārya gāru · 09 Jun', dur: '47 min', count: '5 shlokas' },
];

export const LIVE_LINES = [
  { kind: 'speech', te: 'ధర్మాన్ని మనం బయట వెతకనవసరం లేదు — అది మన హృదయంలోనే ఉంది.', en: 'We need not seek dharma outside — it dwells within the heart.' },
  { kind: 'speech', te: 'మన ప్రతి కర్మలోనూ, ఫలాపేక్ష లేకుండా చేసే పనిలోనూ అది ప్రకాశిస్తుంది.', en: 'It shines in every action done without craving its fruit.' },
  { kind: 'shloka', ref: 'Bhagavad Gītā 4.7', dev: 'यदा यदा हि धर्मस्य ग्लानिर्भवति भारत।', translit: 'yadā yadā hi dharmasya glānir bhavati bhārata' },
  { kind: 'speech', te: 'భగవంతుడు ఇక్కడ ఒక వాగ్దానం చేస్తున్నాడు, భారతా.', en: 'Here the Lord makes a promise, O Bhārata.' },
  { kind: 'speech', te: 'ధర్మం క్షీణించినప్పుడల్లా, ఆయన తానే అవతరిస్తాడు.', en: 'Whenever dharma declines, He Himself descends.' },
];

export const NOTES = [
  { num: '01', title: 'Dharma is inward, not imposed', body: 'Āchārya gāru distinguished dharma from mere rule-following. It is the svabhāva — the intrinsic nature of the Self — recognised in stillness, not enforced from outside.' },
  { num: '02', title: 'Action without attachment', body: 'Right action performed without craving for results is itself worship. The fruit belongs to the Divine; the effort belongs to us.' },
  { num: '03', title: 'The promise of descent', body: 'Citing Gītā 4.7, he taught that whenever dharma weakens, the Divine manifests to restore balance — within history and within the seeker.' },
  { num: '04', title: 'Dharma protects its protector', body: 'He closed on the maxim dharmo rakṣati rakṣitaḥ — guard dharma, and dharma guards you.' },
];

export const SHLOKAS = [
  { ref: 'Bhagavad Gītā 4.7', time: '14:20', dev: 'यदा यदा हि धर्मस्य ग्लानिर्भवति भारत।', translit: 'yadā yadā hi dharmasya glānir bhavati bhārata', te: 'ఎప్పుడెప్పుడు ధర్మానికి హాని కలుగుతుందో, ఓ భారతా...', en: 'Whenever there is a decline of dharma, O Bhārata, and a rise of adharma — then I manifest Myself.' },
  { ref: 'Bhagavad Gītā 2.47', time: '21:05', dev: 'कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।', translit: 'karmaṇy-evādhikāras te mā phaleṣu kadācana', te: 'కర్మ చేయుటయందే నీకు అధికారము, ఫలములయందు ఎన్నడూ లేదు.', en: 'You have a right to action alone, never to its fruits. Let not the fruit be your motive.' },
  { ref: 'Mahābhārata · Vana Parva', time: '33:40', dev: 'धर्मो रक्षति रक्षितः।', translit: 'dharmo rakṣati rakṣitaḥ', te: 'రక్షింపబడిన ధర్మము రక్షించును.', en: 'Dharma, when protected, protects. Guard it, and it becomes your guardian.' },
];

export const SUGGESTIONS = [
  { id: 'dharma', label: 'What did Āchārya gāru say about Dharma?', te: 'ధర్మం గురించి ఆచార్య గారు ఏం చెప్పారు?' },
  { id: 'karma', label: 'Show me every shloka on Karma', te: 'కర్మపై ప్రతి శ్లోకాన్ని చూపించు' },
  { id: 'summary', label: 'Summarise today\u2019s teaching in three lines', te: 'నేటి బోధనను మూడు వాక్యాలలో సంగ్రహించు' },
];

export const ANSWERS = {
  dharma: {
    role: 'ai',
    text: 'In today\u2019s pravachanam, Āchārya gāru taught that dharma is not an external rule but the very nature of the Self — recognised in stillness and expressed through action performed without craving its fruit. He anchored this in the Gītā:',
    shloka: { ref: 'Bhagavad Gītā 4.7 · 14:20', dev: 'यदा यदा हि धर्मस्य ग्लानिर्भवति भारत।', translit: 'yadā yadā hi dharmasya glānir bhavati bhārata' },
    cite: 'Dharma — The Inner Law · 14:20',
  },
  karma: {
    role: 'ai',
    text: 'He returned to Karma twice. The central verse was Gītā 2.47 — your right is to the action, never to its fruit. Worship, he said, is effort offered without attachment to outcome.',
    shloka: { ref: 'Bhagavad Gītā 2.47 · 21:05', dev: 'कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।', translit: 'karmaṇy-evādhikāras te mā phaleṣu kadācana' },
    cite: 'Dharma — The Inner Law · 21:05',
  },
  summary: {
    role: 'ai',
    text: 'Three lines: (1) Dharma is inward — the nature of the Self, not an imposed rule. (2) Act without craving the fruit; that effort is worship. (3) Guard dharma, and dharma guards you — dharmo rakṣati rakṣitaḥ.',
    cite: 'Dharma — The Inner Law · summary',
  },
};
