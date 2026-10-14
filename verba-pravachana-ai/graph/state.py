from typing import TypedDict, List, Optional

class VerbaState(TypedDict):
    audio_path: Optional[str]
    youtube_url: Optional[str] 
    transcript: Optional[str]
    raw_transcript: Optional[str]          # ASR output before term fixes
    asr_provider: Optional[str]            # dual | gemini | sarvam | google
    asr_report: Optional[dict]             # two-listener agreement, judge decisions, unresolved spots
    transcription_gaps: Optional[int]      # audio pieces ASR failed on, shown as [?]
    detected_language: Optional[str]
    shlokas: Optional[List[dict]]
    segments: Optional[List[dict]]
    summary: Optional[str]
    key_teachings: Optional[List[str]]
    notes: Optional[str]
    enhanced_notes: Optional[str]
    transliterated_notes: Optional[str]
    chunk_index: Optional[int]
    current_agent: Optional[str]
    error: Optional[str]
    video_title: Optional[str]
    transcript_segments: Optional[List[dict]]
    caption_text: Optional[str]
    validation_passed: Optional[bool]
    validation_errors: Optional[List[dict]]
    needs_manual_review: Optional[bool]
