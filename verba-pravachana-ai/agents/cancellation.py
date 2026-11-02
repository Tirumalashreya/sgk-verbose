"""A shared, process-wide set of cancelled uploads, keyed by content digest.
Kept separate from api.py so agents/*.py (gemini_asr.py in particular, which
runs the longest, most worth-interrupting loop) can check it without an
import cycle back into api.py."""

class UploadCancelled(Exception):
    """Raised when a user discarded an upload mid-processing — caught
    specifically so it's reported as a clean cancellation, not an error."""


_cancelled: set[str] = set()


def cancel(digest: str) -> None:
    _cancelled.add(digest)


def is_cancelled(digest: str | None) -> bool:
    return bool(digest) and digest in _cancelled


def clear(digest: str | None) -> None:
    if digest:
        _cancelled.discard(digest)
