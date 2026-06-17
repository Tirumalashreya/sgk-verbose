from typing import TypedDict, List, Optional

class VerbaState(TypedDict):
    audio_path: Optional[str]
    youtube_url: Optional[str] 
    transcript: Optional[str]
    detected_language: Optional[str]
    shlokas: Optional[List[dict]]
    segments: Optional[List[dict]]
    summary: Optional[str]
    key_teachings: Optional[List[str]]
    notes: Optional[str]
    enhanced_notes: Optional[str]  
    chunk_index: Optional[int]
    current_agent: Optional[str]
    error: Optional[str]     