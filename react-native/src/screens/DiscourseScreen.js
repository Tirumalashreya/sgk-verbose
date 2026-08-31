import React, { useState } from 'react';
import { View, Text, Image, ScrollView, Pressable } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { C, F, acharyaPhoto } from '../theme';
import { downloadPDF, downloadDOC } from '../services/download';

function parseNoteParagraphs(text) {
  const blocks = [];
  let paraLines = [];

  const flush = () => {
    if (paraLines.length > 0) {
      blocks.push({ type: 'para', text: paraLines.join(' ') });
      paraLines = [];
    }
  };

  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line) { flush(); continue; }

    // **heading** → heading block
    const headingMatch = line.match(/^\*{1,2}(.+?)\*{1,2}$/);
    if (headingMatch) {
      flush();
      blocks.push({ type: 'heading', text: headingMatch[1].trim() });
      continue;
    }
    paraLines.push(line);
  }
  flush();
  return blocks;
}

const TABS = ['transcript', 'notes', 'transliterated', 'shlokas'];
const TAB_LABELS = { transcript: 'Transcript', notes: 'Notes', transliterated: 'Roman', shlokas: 'Shlokas' };

export default function DiscourseScreen({ go, t, lang, sessionData }) {
  const insets = useSafeAreaInsets();
  const [tab, setTab] = useState('transcript');

  const session = sessionData || {};
  const shlokas = session.shlokas || [];
  const segments = session.segments || [];
  const transcript = session.transcript || '';
  const notes = session.notes || '';
  const transliteratedNotes = session.transliterated_notes || '';
  const summary = session.summary || '';

  return (
    <View style={{ flex: 1, backgroundColor: C.paper }}>
      {/* Header */}
      <View style={{ paddingTop: insets.top + 6, paddingHorizontal: 22 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Pressable onPress={() => go('library')}>
            <Text style={{ fontSize: 26, color: C.maroon }}>‹</Text>
          </Pressable>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Text style={{ fontFamily: F.sansSemi, fontSize: 11, color: C.gold, letterSpacing: 1.5 }}>
              {shlokas.length} SHLOKAS
            </Text>
            <Pressable
              onPress={() => downloadPDF(session)}
              style={{ paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8, backgroundColor: 'rgba(122,46,37,0.08)', borderWidth: 1, borderColor: 'rgba(122,46,37,0.2)' }}
            >
              <Text style={{ fontSize: 11, color: C.maroon, fontFamily: F.sansSemi }}>PDF</Text>
            </Pressable>
            <Pressable
              onPress={() => downloadDOC(session)}
              style={{ paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8, backgroundColor: 'rgba(181,138,60,0.1)', borderWidth: 1, borderColor: 'rgba(181,138,60,0.25)' }}
            >
              <Text style={{ fontSize: 11, color: C.gold, fontFamily: F.sansSemi }}>DOC</Text>
            </Pressable>
          </View>
        </View>
        <Text style={{ fontFamily: F.serif, fontSize: 22, color: C.ink, marginTop: 10 }} numberOfLines={2}>
          {session.title || 'Pravachanam'}
        </Text>
        <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 7 }}>
          <Image source={acharyaPhoto} style={{ width: 22, height: 22, borderRadius: 11, marginRight: 8, borderWidth: 1, borderColor: '#e0cb98' }} />
          <Text style={{ fontSize: 12.5, color: C.muted }}>Satluri Gopāla Krishnamāchārya</Text>
        </View>

        {/* Summary strip */}
        {summary ? (
          <View style={{ backgroundColor: C.card, borderLeftWidth: 3, borderLeftColor: C.saffron, borderRadius: 8, padding: 10, marginTop: 12 }}>
            <Text style={{ fontSize: 13, color: C.inkSoft, lineHeight: 20 }}>{summary}</Text>
          </View>
        ) : null}

        {/* Tabs */}
        <View style={{ flexDirection: 'row', marginTop: 14, borderBottomWidth: 1, borderBottomColor: C.line }}>
          {TABS.map((key) => (
            <Pressable key={key} onPress={() => setTab(key)} style={{ marginRight: 24, paddingBottom: 10, borderBottomWidth: 2, borderBottomColor: tab === key ? C.maroon : 'transparent' }}>
              <Text style={{ fontFamily: F.sansSemi, fontSize: 14, color: tab === key ? C.maroon : '#a99c80' }}>
                {TAB_LABELS[key]}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingHorizontal: 22, paddingTop: 18, paddingBottom: 120 }} showsVerticalScrollIndicator={false}>

        {/* TRANSCRIPT — raw what was said */}
        {tab === 'transcript' && (
          <View>
            {transcript ? (
              transcript.split(/[।\n]/).map((line, i) => line.trim().length > 3 && (
                <Text key={i} style={{ fontFamily: F.telugu, fontSize: 16, lineHeight: 30, color: C.ink, marginBottom: 12 }}>
                  {line.trim()}
                </Text>
              ))
            ) : (
              <Text style={{ color: C.muted, textAlign: 'center', marginTop: 40 }}>No transcript available.</Text>
            )}
          </View>
        )}

        {/* NOTES — paragraphs with headings */}
        {tab === 'notes' && (
          <View>
            {notes ? (
              parseNoteParagraphs(notes).map((block, i) =>
                block.type === 'heading' ? (
                  <Text key={i} style={{ fontFamily: F.serif, fontSize: 17, color: C.maroon, marginTop: i === 0 ? 0 : 22, marginBottom: 8 }}>
                    {block.text}
                  </Text>
                ) : (
                  <Text key={i} style={{ fontFamily: F.telugu, fontSize: 15.5, lineHeight: 30, color: C.ink, marginBottom: 16 }}>
                    {block.text}
                  </Text>
                )
              )
            ) : (
              <Text style={{ color: C.muted, textAlign: 'center', marginTop: 40 }}>No notes available.</Text>
            )}
          </View>
        )}

        {/* ROMAN (transliterated Telugu) */}
        {tab === 'transliterated' && (
          <View>
            {transliteratedNotes ? (
              parseNoteParagraphs(transliteratedNotes).map((block, i) =>
                block.type === 'heading' ? (
                  <Text key={i} style={{ fontFamily: F.serif, fontSize: 17, color: C.maroon, marginTop: i === 0 ? 0 : 22, marginBottom: 8 }}>
                    {block.text}
                  </Text>
                ) : (
                  <Text key={i} style={{ fontFamily: F.sans, fontSize: 15, lineHeight: 26, color: C.ink, marginBottom: 16 }}>
                    {block.text}
                  </Text>
                )
              )
            ) : (
              <Text style={{ color: C.muted, textAlign: 'center', marginTop: 40 }}>No transliterated notes available.</Text>
            )}
          </View>
        )}

        {/* SHLOKAS */}
        {tab === 'shlokas' && (
          <View>
            {shlokas.length === 0 ? (
              <Text style={{ color: C.muted, textAlign: 'center', marginTop: 40 }}>No shlokas detected.</Text>
            ) : (
              shlokas.map((s, i) => (
                <View key={i} style={{ marginBottom: 28 }}>
                  <Text style={{ fontFamily: F.sansSemi, fontSize: 10, letterSpacing: 1.5, color: C.gold, marginBottom: 8 }}>
                    {(s.type || 'SHLOKA').toUpperCase()} · {s.language || ''}
                  </Text>
                  <Text style={{ fontFamily: F.telugu, fontSize: 16, lineHeight: 30, color: C.inkSoft }}>
                    "{s.text}"
                  </Text>
                  {s.original ? (
                    <Text style={{ fontFamily: F.telugu, fontSize: 16, lineHeight: 30, color: C.maroon, marginTop: 8 }}>
                      {s.original}
                    </Text>
                  ) : null}
                </View>
              ))
            )}
          </View>
        )}
      </ScrollView>
    </View>
  );
}
