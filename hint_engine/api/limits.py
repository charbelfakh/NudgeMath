"""Request input ceilings for the public GraphQL surface.

Every value here bounds work an *unauthenticated* caller can make the server do:
memory held while decoding an image, tokens shipped to a paid model, turns
replayed into a prompt. Without these, one POST can hold hundreds of megabytes
or make a single hint request arbitrarily expensive.

Enforced in the resolvers (precise, good error messages) and, for the whole
body, by a Content-Length guard in ``api/app.py`` (cheap, catches it earlier).
"""

from __future__ import annotations

# A data: URL is base64, so ~4 chars per 3 bytes. 8M chars ≈ 6 MB of image —
# far above any phone photo of a worksheet, far below "the process died".
MAX_IMAGE_CHARS = 8_000_000

# Whole-body ceiling. Slightly above MAX_IMAGE_CHARS to leave room for the
# GraphQL envelope around the largest legal image.
MAX_REQUEST_BYTES = 12_000_000

MAX_PROBLEM_CHARS = 2_000
MAX_ANSWER_CHARS = 500
# grade_level / subject: short free-text labels.
MAX_LABEL_CHARS = 200

# A multi-turn hint thread; every turn is replayed into the prompt on each call.
MAX_HISTORY_TURNS = 20
MAX_HISTORY_TURN_CHARS = 2_000


def check_length(value: str | None, *, limit: int, field: str) -> None:
    """Raise ValueError when ``value`` exceeds ``limit`` characters."""
    if value is not None and len(value) > limit:
        raise ValueError(
            f"{field} is too long ({len(value)} chars; limit {limit})."
        )


def check_image_data_url(image: str) -> None:
    """Reject an oversized image before it is decoded or sent to a vision model."""
    if not image:
        raise ValueError("No image provided.")
    if len(image) > MAX_IMAGE_CHARS:
        raise ValueError(
            f"Image is too large ({len(image)} chars; limit {MAX_IMAGE_CHARS}). "
            "Use a smaller photo or screenshot."
        )


def check_history(turns: list, *, max_turns: int = MAX_HISTORY_TURNS) -> None:
    """Bound the replayed conversation: turn count and per-turn size."""
    if len(turns) > max_turns:
        raise ValueError(
            f"Conversation history is too long ({len(turns)} turns; limit {max_turns})."
        )
    for turn in turns:
        check_length(turn.text, limit=MAX_HISTORY_TURN_CHARS, field="History turn")
