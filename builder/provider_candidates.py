"""Review-only provider URL candidate generation.

This module may ask provider search endpoints for likely track matches, but it
never writes source data. The caller receives ranked candidates and decides
which exact links, if any, belong in ``tracks.csv`` or ``config.json``.
"""

from datetime import datetime, timezone
from difflib import SequenceMatcher
import json
import re
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import unicodedata

from gsi_links import normalize_provider_url


ProviderFetcher = Callable[..., dict]
PROVIDERS = ("apple", "spotify")
_WORD_PATTERN = re.compile(r"[^a-z0-9]+")


def _normalize_text(value: str) -> str:
    """Make provider spellings comparable without changing authored values."""
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return _WORD_PATTERN.sub(" ", ascii_text.casefold()).strip()


def _identity(item: dict) -> tuple[str, str, str]:
    return tuple(str(item.get(field) or "").strip() for field in ("artist", "track", "album"))


def unique_signals(items: list[dict]) -> list[dict]:
    """Deduplicate tracks and P53 history while preserving source order."""
    unique: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        identity = _identity(item)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(item)
    return unique


def _similarity(expected: str, actual: str) -> float:
    left = _normalize_text(expected)
    right = _normalize_text(actual)
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _score(source: dict, candidate: dict) -> float:
    """Score identity fields, weighting artist and track above album spelling."""
    fields = (("artist", 0.45), ("track", 0.40), ("album", 0.15))
    available = [(field, weight) for field, weight in fields if source.get(field)]
    total_weight = sum(weight for _, weight in available) or 1.0
    return round(
        sum(_similarity(source.get(field, ""), candidate.get(field, "")) * weight for field, weight in available)
        / total_weight,
        3,
    )


def rank_candidates(source: dict, candidates: list[dict], *, limit: int = 3) -> list[dict]:
    """Return provider candidates with a transparent, non-authoritative score."""
    ranked = []
    for candidate in candidates:
        scored = dict(candidate)
        scored["confidence"] = _score(source, candidate)
        ranked.append(scored)
    return sorted(ranked, key=lambda item: item["confidence"], reverse=True)[:limit]


def _status_for(candidates: list[dict]) -> str:
    if not candidates:
        return "no-match"
    confidence = candidates[0]["confidence"]
    if confidence >= 0.92:
        return "strong-candidate"
    if confidence >= 0.72:
        return "review-candidate"
    return "weak-candidate"


def fetch_json(url: str, *, headers: dict[str, str] | None = None, timeout: float = 12) -> dict:
    """Fetch one JSON response with the standard library and a bounded timeout."""
    request = Request(url, headers={"User-Agent": "GSI provider candidate audit/1.0", **(headers or {})})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _apple_candidates(payload: dict) -> list[dict]:
    return [
        {
            "url": result.get("trackViewUrl", ""),
            "artist": result.get("artistName", ""),
            "track": result.get("trackName", ""),
            "album": result.get("collectionName", ""),
        }
        for result in payload.get("results", [])
        if result.get("trackViewUrl")
    ]


def _spotify_candidates(payload: dict) -> list[dict]:
    return [
        {
            "url": (result.get("external_urls") or {}).get("spotify", ""),
            "artist": ((result.get("artists") or [{}])[0]).get("name", ""),
            "track": result.get("name", ""),
            "album": (result.get("album") or {}).get("name", ""),
        }
        for result in (payload.get("tracks") or {}).get("items", [])
        if (result.get("external_urls") or {}).get("spotify")
    ]


def _query_url(provider: str, item: dict) -> str:
    term = " ".join(value for value in _identity(item) if value)
    if provider == "apple":
        return "https://itunes.apple.com/search?" + urlencode({
            "term": term,
            "entity": "song",
            "media": "music",
            "limit": "10",
        })
    if provider == "spotify":
        return "https://api.spotify.com/v1/search?" + urlencode({
            "q": term,
            "type": "track",
            "limit": "10",
        })
    raise ValueError(f"Unsupported provider: {provider}")


def _provider_result(
    item: dict,
    provider: str,
    *,
    token: str,
    fetcher: ProviderFetcher,
    timeout: float,
) -> dict:
    source_key = f"{provider}_url"
    existing = normalize_provider_url(item.get(source_key, ""), provider)
    if existing:
        return {"status": "existing", "url": existing, "candidates": []}
    if provider == "spotify" and not token:
        return {"status": "token-required", "url": "", "candidates": []}

    headers = {"Authorization": f"Bearer {token}"} if provider == "spotify" else {}
    try:
        payload = fetcher(_query_url(provider, item), headers=headers, timeout=timeout)
        raw_candidates = _apple_candidates(payload) if provider == "apple" else _spotify_candidates(payload)
        candidates = rank_candidates(item, raw_candidates)
        return {
            "status": _status_for(candidates),
            "url": candidates[0]["url"] if candidates else "",
            "candidates": candidates,
        }
    except Exception as error:  # A single provider outage must not lose the report.
        return {"status": "request-error", "url": "", "candidates": [], "error": str(error)}


def collect_provider_candidates(
    items: list[dict],
    *,
    spotify_token: str = "",
    providers: tuple[str, ...] = PROVIDERS,
    fetcher: ProviderFetcher = fetch_json,
    timeout: float = 12,
) -> dict:
    """Build a review report; no source or generated file is changed."""
    signals = []
    for item in unique_signals(items):
        signal = {
            "slug": str(item.get("slug") or "").strip(),
            "artist": str(item.get("artist") or "").strip(),
            "track": str(item.get("track") or "").strip(),
            "album": str(item.get("album") or "").strip(),
            "providers": {},
        }
        for provider in providers:
            if provider not in PROVIDERS:
                raise ValueError(f"Unsupported provider: {provider}")
            signal["providers"][provider] = _provider_result(
                item,
                provider,
                token=spotify_token,
                fetcher=fetcher,
                timeout=timeout,
            )
        signals.append(signal)
    return {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "description": "Review-only provider URL candidates. Nothing here is written back automatically.",
        "signals": signals,
    }
