#!/usr/bin/env python3
"""
insights_lab.py - Evidence-backed Instagram Insights & Trial Reels analyzer.

Adds practical value missing from static hook/caption linters:
1. Computes per-reach rates (sends/reach, saves/reach, likes/reach, follows/reach)
   and 3-second View Rate / Average Watch Time ratio against your own account median.
2. Evaluates Trial Reels (24h-72h non-follower sampling) and recommends whether to
   promote ("Share to everyone"), iterate the hook, or archive.
3. Generates a structured 1-variable experiment plan (hypothesis + control + metric).

Zero external dependencies (Python 3 standard library only).
Accepts TSV or CSV exports (or --demo to run a built-in example).
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional


def _to_float(val: object, default: float = 0.0) -> float:
    if val is None:
        return default
    text = str(val).strip().replace(",", "").replace("%", "")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _median(values: List[float]) -> float:
    clean = [v for v in values if v > 0]
    return statistics.median(clean) if clean else 0.0


def load_rows(path: Path) -> List[Dict[str, str]]:
    raw = path.read_text(encoding="utf-8-sig")
    first_line = raw.splitlines()[0] if raw.splitlines() else ""
    delimiter = "\t" if "\t" in first_line else ","
    reader = csv.DictReader(raw.splitlines(), delimiter=delimiter)
    rows: List[Dict[str, str]] = []
    for row in reader:
        norm = {str(k).strip().lower(): (v.strip() if isinstance(v, str) else "") for k, v in row.items() if k}
        if any(norm.values()):
            rows.append(norm)
    return rows


DEMO_ROWS: List[Dict[str, str]] = [
    {
        "id": "reel_01",
        "format": "reel",
        "trial": "no",
        "hook": "I lost $18,000 because of one missing contract clause.",
        "reach": "14200",
        "views": "18900",
        "likes": "610",
        "sends": "420",
        "saves": "390",
        "comments": "44",
        "follows": "95",
        "avg_watch_s": "14.2",
        "duration_s": "26",
        "view_rate_3s": "68.5",
    },
    {
        "id": "reel_02",
        "format": "reel",
        "trial": "no",
        "hook": "3 pricing mistakes junior designers make every week",
        "reach": "4800",
        "views": "5600",
        "likes": "190",
        "sends": "62",
        "saves": "140",
        "comments": "12",
        "follows": "19",
        "avg_watch_s": "8.4",
        "duration_s": "28",
        "view_rate_3s": "51.0",
    },
    {
        "id": "reel_03",
        "format": "reel",
        "trial": "no",
        "hook": "My morning routine as a freelance designer",
        "reach": "2300",
        "views": "2600",
        "likes": "110",
        "sends": "9",
        "saves": "14",
        "comments": "6",
        "follows": "2",
        "avg_watch_s": "5.1",
        "duration_s": "24",
        "view_rate_3s": "39.0",
    },
    {
        "id": "trial_04",
        "format": "reel",
        "trial": "yes",
        "hook": "Steal this 4-line follow-up email before your next client ghosting",
        "reach": "6900",
        "views": "8400",
        "likes": "260",
        "sends": "245",
        "saves": "310",
        "comments": "19",
        "follows": "48",
        "avg_watch_s": "13.0",
        "duration_s": "22",
        "view_rate_3s": "64.0",
    },
]


def analyze(rows: List[Dict[str, str]]) -> Dict[str, object]:
    enriched: List[Dict[str, object]] = []
    for idx, r in enumerate(rows, 1):
        reach = max(_to_float(r.get("reach") or r.get("views")), 1.0)
        views = _to_float(r.get("views"), reach)
        likes = _to_float(r.get("likes"))
        sends = _to_float(r.get("sends") or r.get("shares"))
        saves = _to_float(r.get("saves"))
        comments = _to_float(r.get("comments"))
        follows = _to_float(r.get("follows"))
        avg_watch = _to_float(r.get("avg_watch_s"))
        duration = _to_float(r.get("duration_s"))
        view_rate_3s = _to_float(r.get("view_rate_3s"))
        watch_pct = (avg_watch / duration * 100.0) if duration > 0 and avg_watch > 0 else 0.0

        enriched.append(
            {
                "id": r.get("id") or f"post_{idx:02d}",
                "format": (r.get("format") or "reel").lower(),
                "trial": (r.get("trial") or "no").lower() in {"yes", "true", "1", "trial"},
                "hook": r.get("hook") or r.get("title") or "(no hook text)",
                "reach": reach,
                "views": views,
                "sends_per_1k": sends / reach * 1000.0,
                "saves_per_1k": saves / reach * 1000.0,
                "likes_per_1k": likes / reach * 1000.0,
                "follows_per_1k": follows / reach * 1000.0,
                "comments_per_1k": comments / reach * 1000.0,
                "avg_watch_s": avg_watch,
                "watch_pct": watch_pct,
                "view_rate_3s": view_rate_3s,
            }
        )

    med_reach = _median([float(x["reach"]) for x in enriched])
    med_sends = _median([float(x["sends_per_1k"]) for x in enriched])
    med_saves = _median([float(x["saves_per_1k"]) for x in enriched])
    med_likes = _median([float(x["likes_per_1k"]) for x in enriched])
    med_watch = _median([float(x["watch_pct"]) for x in enriched])
    med_3s = _median([float(x["view_rate_3s"]) for x in enriched])

    for item in enriched:
        reach_mult = float(item["reach"]) / med_reach if med_reach > 0 else 1.0
        sends_mult = float(item["sends_per_1k"]) / med_sends if med_sends > 0 else 1.0
        saves_mult = float(item["saves_per_1k"]) / med_saves if med_saves > 0 else 1.0
        watch_mult = float(item["watch_pct"]) / med_watch if med_watch > 0 and float(item["watch_pct"]) > 0 else 1.0

        composite = 0.35 * sends_mult + 0.35 * watch_mult + 0.20 * saves_mult + 0.10 * reach_mult
        item["reach_multiple"] = round(reach_mult, 2)
        item["sends_multiple"] = round(sends_mult, 2)
        item["saves_multiple"] = round(saves_mult, 2)
        item["composite_index"] = round(composite, 2)

        diagnoses: List[str] = []
        if med_3s > 0 and float(item["view_rate_3s"]) > 0:
            if float(item["view_rate_3s"]) < med_3s * 0.85:
                diagnoses.append("3s view rate below account median -> test a sharper visual/spoken first 3s hook")
            elif float(item["view_rate_3s"]) >= med_3s * 1.1:
                diagnoses.append("strong 3s hold past opening")
        if med_watch > 0 and float(item["watch_pct"]) > 0 and float(item["watch_pct"]) < med_watch * 0.85:
            diagnoses.append("mid-video drop-off -> tighten beat changes every 2-4s or shorten total runtime")
        if med_sends > 0 and float(item["sends_per_1k"]) >= med_sends * 1.3:
            diagnoses.append("high sends/reach -> strong non-follower discovery driver (shareable angle)")
        if med_saves > 0 and float(item["saves_per_1k"]) >= med_saves * 1.3:
            diagnoses.append("high saves/reach -> strong reference utility; consider a follow-up carousel")
        if not diagnoses:
            diagnoses.append("near account baseline")
        item["diagnosis"] = "; ".join(diagnoses)

        if item["trial"]:
            if sends_mult >= 1.15 and watch_mult >= 1.0:
                item["trial_verdict"] = "PROMOTE TO EVERYONE (beats baseline on non-follower sends + watch time)"
            elif float(item["view_rate_3s"]) >= med_3s and watch_mult < 0.9:
                item["trial_verdict"] = "RE-EDIT BODY (hook holds 3s, but watch % lags baseline)"
            else:
                item["trial_verdict"] = "KEEP AS TRIAL / ARCHIVE (re-test hook variable before main-grid post)"
        else:
            item["trial_verdict"] = None

    ranked = sorted(enriched, key=lambda x: float(x["composite_index"]), reverse=True)
    return {
        "count": len(enriched),
        "baselines": {
            "median_reach": round(med_reach, 1),
            "median_sends_per_1k": round(med_sends, 2),
            "median_saves_per_1k": round(med_saves, 2),
            "median_likes_per_1k": round(med_likes, 2),
            "median_watch_pct": round(med_watch, 1),
            "median_view_rate_3s": round(med_3s, 1),
        },
        "posts": ranked,
    }


def format_report(summary: Dict[str, object], hypothesis_topic: Optional[str] = None) -> str:
    b = summary["baselines"]
    posts = summary["posts"]
    lines = [
        f"INSIGHTS LAB  ·  {summary['count']} posts  ·  account-median baselines",
        "=" * 78,
        (
            f"Baselines -> Reach: {b['median_reach']:,.0f} | "
            f"Sends/1k: {b['median_sends_per_1k']} | "
            f"Saves/1k: {b['median_saves_per_1k']} | "
            f"Watch%: {b['median_watch_pct']}% | "
            f"3s View Rate: {b['median_view_rate_3s']}%"
        ),
        "-" * 78,
    ]
    for p in posts:
        tag = "[TRIAL]" if p["trial"] else f"[{str(p['format']).upper()}]"
        lines.append(
            f"{p['composite_index']:>4.2f}x  {tag:<8} {p['id']:<10} "
            f"reach {p['reach']:>7,.0f} ({p['reach_multiple']}x)  "
            f"sends/1k {p['sends_per_1k']:>5.1f}  saves/1k {p['saves_per_1k']:>5.1f}  "
            f"watch {p['watch_pct']:>4.1f}%  3s {p['view_rate_3s']:>4.1f}%"
        )
        lines.append(f"       hook: \"{p['hook']}\"")
        lines.append(f"       note: {p['diagnosis']}")
        if p["trial_verdict"]:
            lines.append(f"       trial decision: {p['trial_verdict']}")

    topic = hypothesis_topic or (posts[0]["hook"] if posts else "your top topic")
    lines.extend(
        [
            "-" * 78,
            "NEXT EXPERIMENT (1 variable only):",
            f"  Topic/Payoff Held Constant : {topic}",
            "  Variable Under Test        : First 3s hook framing (Variant A = concrete number/loss vs Variant B = contrarian/steal)",
            "  Delivery Method            : Post Variant A/B as Trial Reels (or matched time slots 48h apart)",
            "  Primary Readout (24h-72h)  : 3s View Rate + Average Watch % + Sends per 1,000 reach",
            "  Promotion Rule             : Share to everyone only if Sends/1k and Watch % >= account median",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Instagram Insights exports and Trial Reels decisions.")
    parser.add_argument("input", nargs="?", help="Path to CSV or TSV file with post metrics.")
    parser.add_argument("--demo", action="store_true", help="Run with built-in sample Insights data.")
    parser.add_argument("--topic", help="Optional topic for the generated 1-variable experiment block.")
    parser.add_argument("--json", action="store_true", help="Print JSON output instead of a formatted table.")
    args = parser.parse_args()

    if args.demo or not args.input:
        if not args.demo and not args.input:
            parser.print_help()
            return 0
        rows = DEMO_ROWS
    else:
        path = Path(args.input)
        if not path.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            return 1
        rows = load_rows(path)

    summary = analyze(rows)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(format_report(summary, args.topic))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
