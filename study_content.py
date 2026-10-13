"""Small, dependency-free helpers for retrieving useful course-note excerpts."""
from __future__ import annotations

import re
from pathlib import PurePath

_STOPWORDS = {
    "the", "and", "for", "what", "how", "why", "with", "from", "this", "that",
    "are", "was", "were", "you", "your", "have", "has", "had", "can", "could",
    "does", "did", "into", "about", "when", "where", "which", "will", "would",
    "explain", "please", "tell", "give", "show", "make", "using", "use",
}


def stored_material_metadata(filename: str) -> tuple[str, str]:
    """Return (opaque document ID, original filename) for <id>__<original>.txt."""
    name = PurePath(filename).name
    if not name.endswith(".txt"):
        return "", ""
    stem = name[:-4]
    doc_id, separator, original = stem.partition("__")
    if not separator or not re.fullmatch(r"[a-f0-9]{16}", doc_id) or not original:
        return "", ""
    return doc_id, original


def chunk_note_text(text: str, max_chars: int = 1800, overlap: int = 180) -> list[str]:
    """Split long notes into overlapping, word-boundary chunks, including single-paragraph files."""
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    max_chars = max(300, int(max_chars))
    overlap = max(0, min(int(overlap), max_chars // 3))
    chunks: list[str] = []
    start = 0
    size = len(normalized)

    while start < size:
        tentative_end = min(start + max_chars, size)
        end = tentative_end
        if tentative_end < size:
            # Prefer natural boundaries near the target, but never allow tiny chunks.
            floor = start + int(max_chars * 0.55)
            boundaries = [
                normalized.rfind("\n", floor, tentative_end),
                normalized.rfind(". ", floor, tentative_end) + 1,
                normalized.rfind("? ", floor, tentative_end) + 1,
                normalized.rfind("! ", floor, tentative_end) + 1,
                normalized.rfind(" ", floor, tentative_end),
            ]
            best = max(boundaries)
            if best >= floor:
                end = best
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= size:
            break
        next_start = max(start + 1, end - overlap)
        # Start at a word boundary to avoid cutting through terms.
        whitespace = normalized.find(" ", next_start, min(next_start + 80, size))
        newline = normalized.find("\n", next_start, min(next_start + 80, size))
        candidates = [position for position in (whitespace, newline) if position >= 0]
        start = min(candidates) + 1 if candidates else next_start
    return chunks


def _terms(text: str) -> list[str]:
    # Unicode-aware tokenization supports notes and questions in many languages.
    return [term for term in re.findall(r"[^\W_]{2,}", str(text or "").casefold(), flags=re.UNICODE)
            if term not in _STOPWORDS]


def retrieve_relevant_chunks(materials: list[dict], question: str, limit: int = 3,
                             max_context_chars: int = 6000) -> str:
    """Rank chunks by token overlap and return a bounded, source-labelled context block."""
    query_terms = set(_terms(question))
    if not query_terms:
        return ""

    scored: list[tuple[float, int, str, str]] = []
    sequence = 0
    for material in materials:
        name = str(material.get("name") or "Course notes")[:180]
        for chunk in chunk_note_text(material.get("text", "")):
            chunk_terms = _terms(chunk)
            if not chunk_terms:
                continue
            token_set = set(chunk_terms)
            overlap = query_terms & token_set
            if not overlap:
                continue
            # Mildly prefer excerpts matching more of the question and repeated key terms.
            score = len(overlap) + (sum(chunk_terms.count(term) > 1 for term in overlap) * 0.15)
            scored.append((score, sequence, name, chunk))
            sequence += 1

    scored.sort(key=lambda item: (-item[0], item[1]))
    selected: list[str] = []
    used = 0
    for _, _, name, chunk in scored:
        block = f"[Student note: {name}]\n{chunk}"
        # Avoid returning the same overlapping text twice for nearby chunks.
        if any(block[-180:] == prior[-180:] for prior in selected if len(block) > 180):
            continue
        allowance = max_context_chars - used
        if allowance <= 0:
            break
        if len(block) > allowance:
            block = block[:allowance]
        selected.append(block)
        used += len(block) + 2
        if len(selected) >= max(1, int(limit)):
            break
    return "\n\n".join(selected)
