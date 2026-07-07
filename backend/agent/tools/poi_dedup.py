"""Semantic + spatial POI deduplication — no heavy imports.

Pure functions: name similarity, distance, dedup logic.
Importable without langchain or any framework dependency.
"""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any

_SEPARATOR_RE = re.compile(r"[-—·•|/()（）]")
_MIN_NAME_LEN = 3

# Whitelist: suffix patterns that signal a REAL sub-POI expansion (museum, scenic
# area, temple, etc.) even when no separator character is present.
# "故宫" → "故宫博物院" ✓  "颐和园" → "颐和园风景区" ✓  "灵隐寺" → "灵隐寺飞来峰景区" ✓
# "中山公园" → "中山公园路23号" ✗  "西湖" → "西湖春天餐厅" ✗
_LEGIT_EXPANSION_RE = re.compile(
    r'(?:博物院|博物馆|风景区|风景名胜区|景区|公园|植物园|动物园|水族馆)'
    r'|(?:游乐园|主题乐园|乐园|度假区|度假村)'
    r'|(?:寺|庙|庵|观|宫|殿|塔|楼|阁|堂|祠|坛|教堂|清真寺)'
    r'|(?:纪念馆|纪念堂|故居|故里|陵园|陵墓|遗址|古迹|石窟|石刻|碑林)'
    r'|(?:大学|学院|校区|研究院)'
    r'|(?:飞来峰|北峰|南峰|东峰|西峰|主峰)'
    r'|(?:山庄|温泉|滑雪场|高尔夫)'
    r'|(?:步行街|老街|古街|古镇|古村|古城)'
    r'|(?:海滩|海滨|沙滩|浴场|码头|港口)'
)


def _suffix_starts_with_separator(full: str, prefix: str) -> bool:
    """Check that the remainder after `prefix` starts with a separator or is empty.

    "西湖公园" ⊆ "西湖公园-真趣" → True  ("-真趣" starts with '-')
    "西湖公园" ⊆ "西湖公园"      → True  (remainder is empty)
    "中山公园" ⊆ "中山公园路23号" → False (remainder "路23号" starts with '路')
    """
    after = full[len(prefix):]
    return not after or bool(_SEPARATOR_RE.match(after))


def name_similarity(a: str, b: str) -> float:
    """SequenceMatcher-based name similarity in [0, 1]."""
    return SequenceMatcher(None, a.strip(), b.strip()).ratio()


def keep_a_over_b(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Return True if POI `a` is preferable to `b` — higher rating, then more reviews."""
    ra = a.get("rating") or 0
    rb = b.get("rating") or 0
    if ra != rb:
        return ra > rb
    rc_a = a.get("review_count") or 0
    rc_b = b.get("review_count") or 0
    if rc_a != rc_b:
        return rc_a > rc_b
    # tie-break: prefer id-based (stable)
    return str(a.get("id", "")) < str(b.get("id", ""))


def haversine_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """Haversine distance in METERS between two WGS84 points."""
    r = 6_371_000.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    lat_mid = math.radians((lat1 + lat2) / 2)
    dx = dlng * math.cos(lat_mid)
    return r * math.sqrt(dlat**2 + dx**2)


def deduplicate_pois(pois: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove semantically or spatially duplicate POIs.

    Keeps the higher-rated / more-reviewed POI when a conflict is found.

    Rules (applied in order):

    0. **Exact name match** — identical names, keep higher rated.
    1. **Name containment** — "西湖公园" ⊆ "西湖公园-真趣" AND within 500 m.
    2. **Same coords** — distance < 10 m.
    3. **High name similarity** — SeqMatcher > 0.75 AND within 200 m.
    4. **Same base-name** — share the longest prefix before ``-—·•|/`` AND ≤ 150 m
       (catches "西湖公园" vs "西湖公园南门" / "西湖公园-售票处" etc.).
    5. **Sub-POI** — A's name starts with B's full name (e.g. "故宫博物院" starts
       with "故宫") AND within 2 km — keep the more specific one (A) UNLESS B
       has significantly higher rating (≥ 1.0 difference).
    """
    n = len(pois)
    if n <= 1:
        return list(pois)

    discarded: set[int] = set()

    # ── Rule 0: exact name match ──
    for i in range(n):
        if i in discarded:
            continue
        ni = pois[i].get("name", "") or ""
        if not ni:
            continue
        for j in range(i + 1, n):
            if j in discarded:
                continue
            nj = pois[j].get("name", "") or ""
            if nj and ni == nj:
                discarded.add(j if keep_a_over_b(pois[i], pois[j]) else i)
                continue

    for i in range(n):
        if i in discarded:
            continue
        ni = pois[i].get("name", "") or ""
        lng_i = pois[i].get("lng")
        lat_i = pois[i].get("lat")
        if not isinstance(lng_i, (int, float)) or not isinstance(lat_i, (int, float)):
            continue

        for j in range(i + 1, n):
            if j in discarded:
                continue
            nj = pois[j].get("name", "") or ""
            lng_j = pois[j].get("lng")
            lat_j = pois[j].get("lat")
            if not isinstance(lng_j, (int, float)) or not isinstance(lat_j, (int, float)):
                continue

            dist = haversine_m(lng_i, lat_i, lng_j, lat_j)

            # ── Rule 1: name containment + nearby (< 500 m) ──
            # Only dedup when the shorter name is a TRUE prefix of the longer
            # name and the suffix begins with a separator (or is empty).
            # "西湖公园" ⊆ "西湖公园-真趣" → dedup ✓
            # "中山公园" ⊆ "中山公园路23号" → no ✗ (suffix "路" is not a separator)
            if ni and nj and len(ni) >= _MIN_NAME_LEN and len(nj) >= _MIN_NAME_LEN:
                if ni in nj and _suffix_starts_with_separator(nj, ni) and dist < 500:
                    discarded.add(j if keep_a_over_b(pois[i], pois[j]) else i)
                    continue
                if nj in ni and _suffix_starts_with_separator(ni, nj) and dist < 500:
                    discarded.add(j if keep_a_over_b(pois[i], pois[j]) else i)
                    continue

            # ── Rule 2: same coordinates (< 10 m) ──
            if dist < 10:
                discarded.add(j if keep_a_over_b(pois[i], pois[j]) else i)
                continue

            # ── Rule 3: high name similarity + very close (< 200 m) ──
            if ni and nj and dist < 200 and name_similarity(ni, nj) > 0.75:
                discarded.add(j if keep_a_over_b(pois[i], pois[j]) else i)
                continue

            # ── Rule 4: same base-name (before first separator) + nearby ──
            base_i = _SEPARATOR_RE.split(ni)[0].strip()
            base_j = _SEPARATOR_RE.split(nj)[0].strip()
            if base_i and base_j and base_i == base_j and dist < 150:
                discarded.add(j if keep_a_over_b(pois[i], pois[j]) else i)
                continue

            # ── Rule 5: sub-POI (e.g. "故宫博物院" vs "故宫") ──
            # Two conditions must both hold for dedup:
            # a. One name starts with the other, AND the longer name is strictly longer.
            # b. The suffix either starts with a separator character OR matches a
            #    known legitimate expansion pattern (museum, scenic area, temple, etc.).
            # "故宫" → "故宫博物院"  ✓ (博物院 is a legit expansion)
            # "中山公园" → "中山公园路23号" ✗ (路23号 is not an expansion)
            # "西湖" → "西湖春天餐厅" ✗ (春天餐厅 is not an expansion)
            #
            # Distance guard: if the suffix starts with a separator, the two POIs
            # must be within 150 m (same as Rule 4).  "夫子庙" vs "夫子庙-秦淮河画舫"
            # at 1 km are clearly different places.  For non-separator expansions
            # ("故宫" → "故宫博物院") we allow up to 2000 m.
            if ni and nj and dist < 2000:
                shorter_idx: int = -1
                longer_idx: int = -1
                if ni.startswith(nj) and len(ni) > len(nj):
                    after = ni[len(nj):]
                    if _suffix_starts_with_separator(ni, nj) or _LEGIT_EXPANSION_RE.search(after):
                        shorter_idx, longer_idx = j, i
                elif nj.startswith(ni) and len(nj) > len(ni):
                    after = nj[len(ni):]
                    if _suffix_starts_with_separator(nj, ni) or _LEGIT_EXPANSION_RE.search(after):
                        shorter_idx, longer_idx = i, j

                if shorter_idx >= 0:
                    # Separator-based expansions must be close (same as Rule 4)
                    if _suffix_starts_with_separator(
                        pois[longer_idx].get("name", ""),
                        pois[shorter_idx].get("name", ""),
                    ) and dist >= 150:
                        pass  # too far apart — skip dedup
                    else:
                        discarded.add(
                            shorter_idx
                            if keep_a_over_b(pois[longer_idx], pois[shorter_idx])
                            else longer_idx,
                        )
                    continue

    return [p for idx, p in enumerate(pois) if idx not in discarded]
