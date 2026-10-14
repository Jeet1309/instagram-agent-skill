#!/usr/bin/env python3
"""
reel_jury.py - Multi-Subagent Persona Review Panel & Calibrated Aggregator for Instagram Reels.

Why this exists (and why scores are NOT random):
  Research on LLM-as-a-Judge and multi-agent panels (ChatEval, MAJ-Eval ACL 2026,
  LLM-Rubric, 0-5 Grading Scale Alignment 2026, Anchoring Bias in LLM Judges 2026)
  shows that naive "rate this 1-100" prompts produce sycophantic, drifting numbers.

  This tool enforces a 3-layer calibrated evaluation:
  1. DETERMINISTIC TOOL FLOOR (40% of final score):
     Runs the objective local calculators (hookscore.py, beats.py, caption.py, detect.py)
     directly on the Reel packet so 40% of the score is anchored to repeatable code.
  2. BLINDED N-SUBAGENT PERSONA PANEL (60% of final score):
     Generates self-contained prompts for N orthogonal reviewer subagents (3 to 8).
     Each subagent scores 5 criteria on a 0-5 Behaviorally Anchored Rating Scale (BARS),
     completes 4 binary gate checks, and MUST provide a verbatim quote from the Reel
     for every score. No subagent sees another subagent's score (preventing anchoring).
  3. CALIBRATED AGGREGATION & DISAGREEMENT ENGINE:
     Validates each subagent's JSON ballot, penalizes unquoted claims, applies persona-
     specific domain weights, computes inter-rater dispersion (std dev + spread),
     enforces hard dealbreaker caps, and outputs a final 0-100 score + verdict.

Subcommands:
  python scripts/reel_jury.pypersonas
  python scripts/reel_jury.py prepare --packet reel_packet.json --n 5 --out-dir jury_run
  python scripts/reel_jury.py aggregate --packet reel_packet.json --ballots jury_run/ballots.json
  python scripts/reel_jury.py demo --n 5
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
JAKE_ROOT = SKILL_ROOT / "upstream" / "jakeschincariol" / "skills"


# ---------------------------------------------------------------------------
# 1. Behaviorally Anchored 0-5 Rubric (BARS)
# ---------------------------------------------------------------------------

RUBRIC_CRITERIA: Dict[str, Dict[str, Any]] = {
    "thumb_stop_hook": {
        "label": "3-Second Thumb-Stop & Curiosity Gap",
        "anchors": {
            0: "Opens with greeting ('hey guys'), channel intro, or zero concrete nouns/numbers.",
            1: "Generic topic announcement ('Today we talk about pricing') or 'stop scrolling' begging.",
            2: "Clear topic with some tension, but no concrete number, named entity, or visual contrast.",
            3: "Specific claim or problem in first 3 seconds (<12 words), addresses viewer or names a real stake.",
            4: "Sharp pattern interrupt + concrete number/mistake/loss in first 3 seconds; on-screen text complements spoken line without repeating it verbatim.",
            5: "Immediate high-stakes proof, contrarian flip, or visceral tension in <=10 words with a specific visual cue that forces a 3-second hold.",
        },
    },
    "retention_pacing": {
        "label": "Beat Pacing, Visual Change & Loop Payoff",
        "anchors": {
            0: "Monotone wall of text; beats run >8s with no visual/shot change; ends with 'thanks for watching'.",
            1: "Multiple beats exceed 5s without visual reset; slow preamble before delivering value.",
            2: "Acceptable length, but middle section sags or repeats the same point twice.",
            3: "Every beat is ~2-4s (or has a visual cut/B-roll cue); front-loads value immediately after hook.",
            4: "Tight 2-4s beat cadence, concrete examples in the middle, and final line cleanly resolves the hook.",
            5: "Zero dead air, escalating proof every 3s, and final sentence syntactically/thematically loops back to the first 3s for seamless replay.",
        },
    },
    "proof_credibility": {
        "label": "Domain Accuracy, Specificity & Proof",
        "anchors": {
            0: "Contains fabricated-sounding stats, impossible promises, or factually wrong domain advice.",
            1: "Pure platitudes ('just be consistent', 'add value') that anyone could say without experience.",
            2: "Plausible advice but lacks a concrete mechanism, example, before/after, or number.",
            3: "Includes at least one specific mechanism, clause, workflow step, or real number/placeholder.",
            4: "Actionable, non-obvious domain mechanism backed by concrete specifics and honest scope.",
            5: "Practitioner-grade insight with exact wording/numbers/steps that a viewer can verify or apply immediately.",
        },
    },
    "save_send_value": {
        "label": "Save Reference Utility & DM Send Trigger",
        "anchors": {
            0: "No reason to save or send to a friend; purely self-serving or vague.",
            1: "Mildly interesting thought, but nothing worth bookmarking or forwarding in a DM.",
            2: "Has a takeaway, yet too abstract to use as a checklist/template or share with a peer.",
            3: "Clear takeaway or template that a viewer might save for later reference.",
            4: "Contains Either a stealable script/checklist (Save trigger) OR a 'this is literally us' / coworker truth (Send trigger).",
            5: "Engineered for both: stealable high-utility artifact (Save) AND strong identity/peer resonance (DM Send) with a single low-friction CTA.",
        },
    },
    "voice_naturalness": {
        "label": "Spoken Naturalness, Caption Fold & Anti-Slop",
        "anchors": {
            0: "Reads like raw ChatGPT output ('delve', 'unlock', 'game-changer', 'it's not just X it's Y', >5 hashtags).",
            1: "Stiff written prose that sounds unnatural out loud; caption truncates mid-thought at 125 chars.",
            2: "Mostly clean but has 1-2 stock AI transitions or a cluttered multi-ask CTA.",
            3: "Natural spoken sentences, clean 125-char caption preview, <=5 relevant hashtags, one CTA.",
            4: "Sounds like a real human talking to one person; concrete nouns, varied sentence lengths, crisp caption fold.",
            5: "Distinctive creator voice with zero slop tells, ear-tested contractions, and a caption hook that adds a second angle to the video.",
        },
    },
}

BINARY_GATES: Dict[str, str] = {
    "no_greeting_or_begging": "True if the Reel does NOT open with 'hey guys/welcome back' or 'stop scrolling/watch till the end'.",
    "single_clear_cta": "True if there is at most ONE primary call-to-action across script and caption (not 'like, save, share, and comment').",
    "no_unverified_fabrication": "True if claims either use user-supplied proof, practitioner mechanics, or explicit [placeholder] markers rather than invented fake client stats.",
    "caption_fold_complete": "True if the first 125 characters of the caption form a complete, compelling thought before '... more' and hashtags are <= 5.",
}


# ---------------------------------------------------------------------------
# 2. Orthogonal Persona Pool (N subagents with distinct domain lenses & weights)
# ---------------------------------------------------------------------------

PERSONA_POOL: List[Dict[str, Any]] = [
    {
        "id": "cold_scroller",
        "name": "Maya (Ruthless Cold Feed Scroller)",
        "domain": "Unconnected Non-Follower Discovery & 3-Second Attention",
        "personality": "Impatient, allergic to intros, clichés, and creators talking about themselves before earning attention. Swipes away in 1.8 seconds if bored.",
        "skillset": " Evaluates thumb-stop power, visual/spoken contrast in the first 3 seconds, and whether a stranger who doesn't follow the account cares.",
        "weights": {
            "thumb_stop_hook": 0.45,
            "retention_pacing": 0.25,
            "proof_credibility": 0.05,
            "save_send_value": 0.15,
            "voice_naturalness": 0.10,
        },
    },
    {
        "id": "retention_editor",
        "name": "Devon (Short-Form Retention & Pacing Editor)",
        "domain": "Video Editing, Beat Timing, Visual Resets & Loop Mechanics",
        "personality": "Obsessive timeline editor who watches retention graphs for a living. Hates static talking-head beats longer than 4 seconds and weak endings.",
        "skillset": "Audits spoken word-per-minute pacing, beat durations, on-screen text vs spoken audio alignment, and loop back to the opening line.",
        "weights": {
            "thumb_stop_hook": 0.20,
            "retention_pacing": 0.45,
            "proof_credibility": 0.05,
            "save_send_value": 0.10,
            "voice_naturalness": 0.20,
        },
    },
    {
        "id": "niche_skeptic",
        "name": "Dr. Aris (Adversarial Domain Skeptic & Fact Checker)",
        "domain": "Subject-Matter Depth, Claim Verification & Anti-BS",
        "personality": "Skeptical practitioner who has seen every recycled Twitter/LinkedIn thread turned into a Reel. Penalizes vague platitudes and unbacked numbers.",
        "skillset": "Stress-tests whether the mechanism actually works, flags generic advice, checks if proof is concrete or fabricated, and challenges weak logic.",
        "weights": {
            "thumb_stop_hook": 0.10,
            "retention_pacing": 0.10,
            "proof_credibility": 0.50,
            "save_send_value": 0.20,
            "voice_naturalness": 0.10,
        },
    },
    {
        "id": "icp_buyer",
        "name": "Elena (Target Audience / Ideal Customer Buyer)",
        "domain": "Practical Utility, Save-Worthiness, DM Shareability & CTA Friction",
        "personality": "Busy operator in the target audience. Saves posts she can use Monday morning and DMs posts that make her look smart to a teammate or client.",
        "skillset": "Judges whether the payoff is worth a Save, whether the angle triggers a DM Send, and whether the CTA feels natural or pushy.",
        "weights": {
            "thumb_stop_hook": 0.15,
            "retention_pacing": 0.10,
            "proof_credibility": 0.20,
            "save_send_value": 0.45,
            "voice_naturalness": 0.10,
        },
    },
    {
        "id": "voice_humanizer",
        "name": "Nora (Spoken-Word & Anti-Slop Editorial Director)",
        "domain": "Ear-Tested Copywriting, Human Cadence & AI-Tell Scrubbing",
        "personality": "Former radio producer and copy chief. Spots LLM sentence symmetry, 'it's not X it's Y' contrasts, and robotic vocabulary instantly.",
        "skillset": "Reads every line out loud for breathability, rhythm, specificity, and authentic creator voice.",
        "weights": {
            "thumb_stop_hook": 0.15,
            "retention_pacing": 0.15,
            "proof_credibility": 0.10,
            "save_send_value": 0.10,
            "voice_naturalness": 0.50,
        },
    },
    {
        "id": "algorithm_packager",
        "name": "Kai (Instagram Distribution, SEO & Trial-Reel Strategist)",
        "domain": "2026 Instagram Signals (Watch Time, Sends/Reach, 125-Char Fold, Search Keywords)",
        "personality": "Analytical growth lead who treats every Reel as a measurable hypothesis for Trial Reels and non-follower recommendations.",
        "skillset": "Checks 125-char caption truncation, search keyword placement, <=5 sized hashtags, originality compliance, and Trial Reel testability.",
        "weights": {
            "thumb_stop_hook": 0.25,
            "retention_pacing": 0.25,
            "proof_credibility": 0.10,
            "save_send_value": 0.25,
            "voice_naturalness": 0.15,
        },
    },
    {
        "id": "brand_guardian",
        "name": "Sloane (Brand Trust, Positioning & Risk Reviewer)",
        "domain": "Reputation, Audience Trust, Claim Safety & Platform Guidelines",
        "personality": "Protective strategist who ensures a viral hook doesn't cheapen authority or violate platform recommendation rules.",
        "skillset": "Audits tone alignment, overclaiming risk, originality eligibility, and long-term positioning.",
        "weights": {
            "thumb_stop_hook": 0.10,
            "retention_pacing": 0.10,
            "proof_credibility": 0.40,
            "save_send_value": 0.15,
            "voice_naturalness": 0.25,
        },
    },
    {
        "id": "conversion_strategist",
        "name": "Marcus (DM Funnel & Comment-to-Lead Architect)",
        "domain": "Comment Keyword Triggers, Story/DM Handoffs & Lead Capture",
        "personality": "Direct-response minimalist who cares about qualified replies and DM starts per 1,000 views, not vanity likes.",
        "skillset": "Evaluates whether the final beat and caption CTA naturally earn a comment/DM or profile tap without sounding like engagement bait.",
        "weights": {
            "thumb_stop_hook": 0.15,
            "retention_pacing": 0.15,
            "proof_credibility": 0.20,
            "save_send_value": 0.35,
            "voice_naturalness": 0.15,
        },
    },
]


# ---------------------------------------------------------------------------
# 3. Deterministic Tool Floor Loader (40% of composite score)
# ---------------------------------------------------------------------------

def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_deterministic_floor(packet: Dict[str, Any]) -> Dict[str, Any]:
    """Run Jake's hookscore.py, beats.py, caption.py, and detect.py on the packet."""
    hook = str(packet.get("hook") or "").strip()
    script_lines = packet.get("script_beats") or []
    if isinstance(script_lines, list):
        script_text = "\n".join(str(x).strip() for x in script_lines if str(x).strip())
    else:
        script_text = str(script_lines).strip()
    if hook and hook not in script_text:
        script_text = f"{hook}\n{script_text}".strip()

    caption_text = str(packet.get("caption") or "").strip()
    keywords_raw = packet.get("keywords") or []
    if isinstance(keywords_raw, str):
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    else:
        keywords = [str(k).strip() for k in keywords_raw if str(k).strip()]
    target_s = float(packet.get("target_duration_s") or 28.0)
    wpm = int(packet.get("wpm") or 165)

    hookscore_mod = _load_module("hookscore", JAKE_ROOT / "ig-reel" / "hookscore.py")
    beats_mod = _load_module("beats", JAKE_ROOT / "ig-reel" / "beats.py")
    caption_mod = _load_module("caption", JAKE_ROOT / "ig-caption" / "caption.py")
    detect_mod = _load_module("detect", JAKE_ROOT / "ig-human" / "detect.py")
    lexicon = json.loads((JAKE_ROOT / "ig-human" / "slop.json").read_text(encoding="utf-8"))

    hook_line = hook or (script_text.splitlines()[0] if script_text else "")
    h_results, h_overall, h_verdict, h_flags = hookscore_mod.run(hook_line)
    hook_res = {
        "hook": hook_line,
        "checks": {k: {"score": round(v[0], 1), "detail": v[1]} for k, v in h_results.items()},
        "weakest": min(hookscore_mod.CHECKS, key=lambda c: h_results[c][0]),
        "flags": h_flags,
        "total": round(h_overall, 1),
        "verdict": h_verdict,
    }
    beat_res = beats_mod.analyse(script_text or hook_line, wpm=wpm, target=target_s) or {
        "total_words": 0,
        "total_seconds": 0.0,
        "target": target_s,
        "beats": [],
        "notes": [],
    }
    cap_res = caption_mod.analyse(caption_text or hook_line, cut=125, keywords=keywords)
    ds_res, ds_overall, ds_verdict = detect_mod.run(script_text or hook_line, lexicon)
    dc_res, dc_overall, dc_verdict = detect_mod.run(caption_text or hook_line, lexicon)
    det_script = {
        "human_score": round(ds_overall, 1),
        "verdict": ds_verdict,
        "scores": {k: {"score": round(v[0], 1), "detail": v[1]} for k, v in ds_res.items()},
    }
    det_caption = {
        "human_score": round(dc_overall, 1),
        "verdict": dc_verdict,
        "scores": {k: {"score": round(v[0], 1), "detail": v[1]} for k, v in dc_res.items()},
    }

    # Beat pacing score (0-100) from deterministic notes/flags
    beat_score = 100.0
    for note in beat_res.get("notes", []):
        low = note.lower()
        if "beat 1 takes" in low or "no number and no name" in low:
            beat_score -= 20.0
        elif "static frame" in low or "run past" in low:
            beat_score -= 14.0
        elif "nothing concrete" in low:
            beat_score -= 14.0
        elif "no loop" in low:
            beat_score -= 12.0
    beat_score = max(0.0, min(100.0, beat_score))

    # Caption lint score (0-100)
    checks = cap_res.get("checks", [])
    if checks:
        pts = 0.0
        for c in checks:
            st = c.get("status")
            pts += 1.0 if st == "PASS" else (0.5 if st == "WARN" else 0.0)
        caption_score = round(pts / len(checks) * 100.0, 1)
    else:
        caption_score = 50.0

    human_score = round(0.6 * float(det_script["human_score"]) + 0.4 * float(det_caption["human_score"]), 1)
    hook_total = float(hook_res.get("total", 0.0))

    deterministic_total = round(
        0.35 * hook_total + 0.25 * beat_score + 0.20 * caption_score + 0.20 * human_score,
        1,
    )

    return {
        "deterministic_score_100": deterministic_total,
        "components": {
            "hook_score_100": hook_total,
            "beat_pacing_score_100": round(beat_score, 1),
            "caption_lint_score_100": caption_score,
            "human_voice_score_100": human_score,
        },
        "hook_detail": hook_res,
        "beat_detail": beat_res,
        "caption_detail": cap_res,
        "human_script_detail": {
            "human_score": det_script["human_score"],
            "verdict": det_script["verdict"],
            "scores": det_script["scores"],
        },
        "human_caption_detail": {
            "human_score": det_caption["human_score"],
            "verdict": det_caption["verdict"],
            "scores": det_caption["scores"],
        },
    }


# ---------------------------------------------------------------------------
# 4. Subagent Prompt Builder (Blinded, Quote-Anchored, 0-5 BARS)
# ---------------------------------------------------------------------------

def select_personas(n: int, persona_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    if persona_ids:
        by_id = {p["id"]: p for p in PERSONA_POOL}
        chosen = [by_id[pid] for pid in persona_ids if pid in by_id]
        if chosen:
            return chosen
    n_clamped = max(1, min(n, len(PERSONA_POOL)))
    return PERSONA_POOL[:n_clamped]


def build_subagent_prompt(persona: Dict[str, Any], packet: Dict[str, Any], det_floor: Dict[str, Any]) -> str:
    rubric_lines: List[str] = []
    for cid, cinfo in RUBRIC_CRITERIA.items():
        w = int(round(persona["weights"].get(cid, 0.2) * 100))
        rubric_lines.append(f"### Criterion `{cid}` ({cinfo['label']}) — Your Domain Weight: {w}%")
        for score_val, desc in cinfo["anchors"].items():
            rubric_lines.append(f"  - **{score_val}/5**: {desc}")
    rubric_block = "\n".join(rubric_lines)

    gates_block = "\n".join(f"- `{gid}`: {gdesc}" for gid, gdesc in BINARY_GATES.items())

    # Notice: We pass objective facts (duration, word count, caption window) NOT prior numerical scores
    # to avoid LLM-as-a-Judge numerical anchoring bias (arXiv:2608.25869).
    beat_detail = det_floor["beat_detail"]
    cap_detail = det_floor["caption_detail"]
    facts_block = json.dumps(
        {
            "spoken_word_count": beat_detail.get("total_words"),
            "estimated_duration_s": beat_detail.get("total_seconds"),
            "target_duration_s": beat_detail.get("target"),
            "caption_first_125_chars": cap_detail.get("visible"),
            "caption_total_chars": cap_detail.get("characters"),
            "hashtag_count": len(cap_detail.get("hashtags", [])),
            "structural_notes_detected": beat_detail.get("notes", []),
        },
        indent=2,
    )

    packet_block = json.dumps(packet, indent=2, ensure_ascii=False)

    return f"""You are an independent test reviewer on an Instagram Reel Evaluation Jury.
Do NOT act like a polite assistant. Score strictly from your persona's perspective and domain expertise.
You are BLINDED to other reviewers' scores. Do not guess a middle score to be safe.

## Your Persona
- **ID**: `{persona['id']}`
- **Name**: {persona['name']}
- **Domain Expertise**: {persona['domain']}
- **Personality & Bias**: {persona['personality']}
- **Skillset**: {persona['skillset']}

## Reel Packet Under Review
```json
{packet_block}
```

## Objective Measurements (Measured by Local Tools — No Numeric Score Shown to Prevent Anchoring)
```json
{facts_block}
```

## Behaviorally Anchored 0-5 Rubric (BARS)
Score EVERY criterion with an integer or half-step from `0` to `5` using ONLY these behavioral anchors.
For EVERY criterion, you MUST include a `quote` field containing an exact verbatim substring from the Reel Packet (or `"MISSING:<what is absent>"` if penalizing an omission). Unquoted scores are penalized by the aggregator.

{rubric_block}

## Binary Gate Checks (true / false)
{gates_block}

## Required Output Format (Return ONLY valid JSON, no markdown wrapper)
{{
  "persona_id": "{persona['id']}",
  "persona_name": "{persona['name']}",
  "criteria": {{
    "thumb_stop_hook": {{"score": 0, "quote": "...", "rationale": "...", "fix": "..."}},
    "retention_pacing": {{"score": 0, "quote": "...", "rationale": "...", "fix": "..."}},
    "proof_credibility": {{"score": 0, "quote": "...", "rationale": "...", "fix": "..."}},
    "save_send_value": {{"score": 0, "quote": "...", "rationale": "...", "fix": "..."}},
    "voice_naturalness": {{"score": 0, "quote": "...", "rationale": "...", "fix": "..."}}
  }},
  "binary_gates": {{
    "no_greeting_or_begging": true,
    "single_clear_cta": true,
    "no_unverified_fabrication": true,
    "caption_fold_complete": true
  }},
  "would_watch_past_3s": true,
  "would_save_or_send": false,
  "top_dealbreaker": "One sentence naming the single biggest weakness from your lens.",
  "highest_leverage_rewrite": "Exact replacement line or edit instruction."
}}
"""


# ---------------------------------------------------------------------------
# 5. Ballot Validation & Non-Random Aggregation Engine
# ---------------------------------------------------------------------------

def _packet_corpus(packet: Dict[str, Any]) -> str:
    parts: List[str] = []
    for k in ("hook", "caption", "cta", "topic", "target_audience"):
        if packet.get(k):
            parts.append(str(packet[k]))
    for k in ("script_beats", "on_screen_text", "visual_cues"):
        val = packet.get(k)
        if isinstance(val, list):
            parts.extend(str(x) for x in val)
        elif val:
            parts.append(str(val))
    return "\n".join(parts).lower()


def validate_and_score_ballot(
    ballot: Dict[str, Any],
    persona_map: Dict[str, Dict[str, Any]],
    corpus_lower: str,
) -> Dict[str, Any]:
    pid = str(ballot.get("persona_id") or "custom")
    persona = persona_map.get(pid, PERSONA_POOL[0])
    weights = persona["weights"]
    criteria_in = ballot.get("criteria") or {}

    weighted_sum = 0.0
    weight_total = 0.0
    unquoted_penalties = 0
    cleaned_criteria: Dict[str, Dict[str, Any]] = {}

    for cid in RUBRIC_CRITERIA:
        entry = criteria_in.get(cid) or {}
        raw_score = float(entry.get("score", 0.0))
        clamped = max(0.0, min(5.0, raw_score))
        quote = str(entry.get("quote") or "").strip()
        rationale = str(entry.get("rationale") or "").strip()
        fix = str(entry.get("fix") or "").strip()

        # Verify quote grounding: must either be a >=6 char substring of packet or start with MISSING:
        quote_grounded = False
        if quote.upper().startswith("MISSING:") and len(quote) > 10:
            quote_grounded = True
        elif len(quote) >= 6 and quote.lower() in corpus_lower:
            quote_grounded = True
        elif len(quote) >= 6:
            # Check token overlap if punctuation differs slightly
            tokens = [t for t in quote.lower().split() if len(t) > 3]
            if tokens and sum(1 for t in tokens if t in corpus_lower) / len(tokens) >= 0.7:
                quote_grounded = True

        if not quote_grounded:
            unquoted_penalties += 1
            # Pull score toward conservative 2.5 if reviewer failed to cite evidence
            clamped = round(0.7 * clamped + 0.3 * 2.0, 2)

        w = float(weights.get(cid, 0.2))
        weighted_sum += clamped * w
        weight_total += w
        cleaned_criteria[cid] = {
            "score_0_to_5": round(clamped, 2),
            "quote": quote,
            "quote_verified": quote_grounded,
            "rationale": rationale,
            "fix": fix,
        }

    persona_score_0_to_5 = (weighted_sum / weight_total) if weight_total > 0 else 0.0
    persona_score_100 = round((persona_score_0_to_5 / 5.0) * 100.0, 1)

    gates_in = ballot.get("binary_gates") or {}
    cleaned_gates = {gid: bool(gates_in.get(gid, True)) for gid in BINARY_GATES}
    failed_gates = [gid for gid, passed in cleaned_gates.items() if not passed]

    return {
        "persona_id": pid,
        "persona_name": ballot.get("persona_name") or persona["name"],
        "domain": persona["domain"],
        "weighted_score_100": persona_score_100,
        "unquoted_penalties": unquoted_penalties,
        "criteria": cleaned_criteria,
        "binary_gates": cleaned_gates,
        "failed_gates": failed_gates,
        "would_watch_past_3s": bool(ballot.get("would_watch_past_3s", persona_score_100 >= 65)),
        "would_save_or_send": bool(ballot.get("would_save_or_send", persona_score_100 >= 72)),
        "top_dealbreaker": str(ballot.get("top_dealbreaker") or "").strip(),
        "highest_leverage_rewrite": str(ballot.get("highest_leverage_rewrite") or "").strip(),
    }


def aggregate_jury(
    packet: Dict[str, Any],
    ballots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    det_floor = run_deterministic_floor(packet)
    persona_map = {p["id"]: p for p in PERSONA_POOL}
    corpus_lower = _packet_corpus(packet)

    scored_ballots = [validate_and_score_ballot(b, persona_map, corpus_lower) for b in ballots]
    if not scored_ballots:
        raise ValueError("At least one subagent ballot is required for aggregation.")

    # Criterion-level stats across N subagents
    criterion_summary: Dict[str, Dict[str, Any]] = {}
    disagreements: List[Dict[str, Any]] = []
    for cid, cinfo in RUBRIC_CRITERIA.items():
        vals = [float(b["criteria"][cid]["score_0_to_5"]) for b in scored_ballots]
        mean_v = statistics.mean(vals)
        std_v = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        spread = max(vals) - min(vals) if vals else 0.0
        criterion_summary[cid] = {
            "label": cinfo["label"],
            "mean_0_to_5": round(mean_v, 2),
            "score_100": round(mean_v / 5.0 * 100.0, 1),
            "std_dev": round(std_v, 2),
            "spread": round(spread, 2),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
        }
        if spread >= 2.0 or std_v >= 0.85:
            low_b = min(scored_ballots, key=lambda b: b["criteria"][cid]["score_0_to_5"])
            high_b = max(scored_ballots, key=lambda b: b["criteria"][cid]["score_0_to_5"])
            disagreements.append(
                {
                    "criterion": cid,
                    "label": cinfo["label"],
                    "spread_0_to_5": round(spread, 2),
                    "lowest_reviewer": f"{low_b['persona_name']} ({low_b['criteria'][cid]['score_0_to_5']}/5): {low_b['criteria'][cid]['rationale']}",
                    "highest_reviewer": f"{high_b['persona_name']} ({high_b['criteria'][cid]['score_0_to_5']}/5): {high_b['criteria'][cid]['rationale']}",
                }
            )

    jury_scores = [float(b["weighted_score_100"]) for b in scored_ballots]
    jury_mean_100 = round(statistics.mean(jury_scores), 1)
    jury_std_100 = round(statistics.pstdev(jury_scores), 1) if len(jury_scores) > 1 else 0.0
    margin_95 = round(1.96 * (jury_std_100 / math.sqrt(len(jury_scores))), 1) if len(jury_scores) > 1 else 0.0

    det_100 = float(det_floor["deterministic_score_100"])
    raw_combined = round(0.40 * det_100 + 0.60 * jury_mean_100, 1)

    # Hard dealbreaker caps (majority gate failure or severe hook dealbreaker)
    caps_applied: List[str] = []
    final_score = raw_combined
    for gid in BINARY_GATES:
        fail_count = sum(1 for b in scored_ballots if gid in b["failed_gates"])
        if fail_count > len(scored_ballots) / 2.0:
            if gid == "no_unverified_fabrication":
                final_score = min(final_score, 45.0)
                caps_applied.append("Capped at 45.0: Majority of jury flagged unverified fabrication/stats.")
            elif gid == "no_greeting_or_begging":
                final_score = min(final_score, 58.0)
                caps_applied.append("Capped at 58.0: Opens with greeting or 'stop scrolling' begging.")
            else:
                final_score = round(final_score - 6.0, 1)
                caps_applied.append(f"-6.0 penalty: Majority failed binary gate `{gid}`.")

    hold_3s_rate = round(sum(1 for b in scored_ballots if b["would_watch_past_3s"]) / len(scored_ballots) * 100.0, 1)
    save_send_rate = round(sum(1 for b in scored_ballots if b["would_save_or_send"]) / len(scored_ballots) * 100.0, 1)

    if final_score >= 80.0 and hold_3s_rate >= 75.0:
        verdict = "SHIP TO MAIN FEED (High confidence across deterministic tools + multi-persona jury)"
    elif final_score >= 68.0:
        verdict = "SHIP AS TRIAL REEL FIRST (Good core, test 24h-72h non-follower retention before main grid)"
    elif final_score >= 52.0:
        verdict = "REVISE HOOK & PACING BEFORE SHOOTING (Apply top jury rewrites and re-score)"
    else:
        verdict = "DO NOT SHOOT YET (Major hook, pacing, or credibility dealbreakers)"

    # Rank actionable fixes by lowest-scoring criteria
    sorted_crit = sorted(criterion_summary.items(), key=lambda kv: kv[1]["score_100"])
    priority_fixes: List[Dict[str, str]] = []
    for cid, cstats in sorted_crit[:3]:
        worst_ballot = min(scored_ballots, key=lambda b: b["criteria"][cid]["score_0_to_5"])
        fix_text = worst_ballot["criteria"][cid]["fix"] or worst_ballot["highest_leverage_rewrite"]
        priority_fixes.append(
            {
                "criterion": cid,
                "score_100": str(cstats["score_100"]),
                "critic": worst_ballot["persona_name"],
                "issue": worst_ballot["criteria"][cid]["rationale"],
                "fix": fix_text,
            }
        )

    return {
        "final_calibrated_score_100": round(final_score, 1),
        "raw_combined_score_100": raw_combined,
        "verdict": verdict,
        "weights_used": {"deterministic_tool_floor": 0.40, "n_subagent_persona_panel": 0.60},
        "deterministic_floor": det_floor,
        "jury_panel": {
            "n_subagents": len(scored_ballots),
            "jury_mean_100": jury_mean_100,
            "jury_std_dev_100": jury_std_100,
            "confidence_interval_95": f"{jury_mean_100} +/- {margin_95}",
            "predicted_3s_hold_pct": hold_3s_rate,
            "predicted_save_or_send_pct": save_send_rate,
            "caps_or_penalties_applied": caps_applied,
            "criterion_breakdown": criterion_summary,
            "preserved_disagreements": disagreements,
            "priority_fixes": priority_fixes,
            "ballots": scored_ballots,
        },
    }


def format_jury_report(result: Dict[str, Any]) -> str:
    det = result["deterministic_floor"]
    dc = det["components"]
    jp = result["jury_panel"]
    lines = [
        f"REEL JURY REPORT  ·  N={jp['n_subagents']} subagents  ·  40% Deterministic + 60% Calibrated BARS Panel",
        "=" * 86,
        f"FINAL CALIBRATED SCORE : {result['final_calibrated_score_100']} / 100   ({result['verdict']})",
        f"  - Deterministic Floor (40%) : {det['deterministic_score_100']} / 100  "
        f"[Hook {dc['hook_score_100']} | Beats {dc['beat_pacing_score_100']} | Caption {dc['caption_lint_score_100']} | Human {dc['human_voice_score_100']}]",
        f"  - N-Subagent Panel    (60%) : {jp['confidence_interval_95']} / 100  "
        f"[3s Hold: {jp['predicted_3s_hold_pct']}% | Save/Send: {jp['predicted_save_or_send_pct']}%]",
        "-" * 86,
        "CRITERION SCORES ACROSS SUBAGENTS (0-5 BARS -> 0-100):",
    ]
    for cid, cstats in jp["criterion_breakdown"].items():
        lines.append(
            f"  {cstats['label']:<42} {cstats['mean_0_to_5']:>4.2f}/5  ({cstats['score_100']:>5.1f}/100)  "
            f"spread {cstats['spread']:>3.1f} (min {cstats['min']}, max {cstats['max']})"
        )

    lines.append("-" * 86)
    lines.append("INDIVIDUAL SUBAGENT BALLOTS (domain-weighted):")
    for b in jp["ballots"]:
        watch = "HOLD-3s" if b["would_watch_past_3s"] else "SWIPE-3s"
        share = "SAVE/SEND" if b["would_save_or_send"] else "NO-SHARE"
        lines.append(
            f"  * {b['persona_name']:<44} {b['weighted_score_100']:>5.1f}/100  [{watch} | {share}]"
        )
        lines.append(f"      dealbreaker: {b['top_dealbreaker']}")
        lines.append(f"      rewrite    : {b['highest_leverage_rewrite']}")

    if jp["preserved_disagreements"]:
        lines.append("-" * 86)
        lines.append("PRESERVED PANEL DISAGREEMENTS (spread >= 2.0 on 0-5 scale):")
        for d in jp["preserved_disagreements"]:
            lines.append(f"  ! {d['label']} (spread {d['spread_0_to_5']}):")
            lines.append(f"      Low : {d['lowest_reviewer']}")
            lines.append(f"      High: {d['highest_reviewer']}")

    if jp["caps_or_penalties_applied"]:
        lines.append("-" * 86)
        lines.append("HARD GATES / PENALTIES APPLIED:")
        for cap in jp["caps_or_penalties_applied"]:
            lines.append(f"  - {cap}")

    lines.append("-" * 86)
    lines.append("TOP PRIORITY REWRITES BEFORE SHOOTING:")
    for idx, f in enumerate(jp["priority_fixes"], 1):
        lines.append(f"  {idx}. [{f['criterion']} @ {f['score_100']}/100 — {f['critic']}] {f['fix']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6. Built-In Demo Packet & Realistic Subagent Ballots
# ---------------------------------------------------------------------------

DEMO_PACKET: Dict[str, Any] = {
    "topic": "Why freelance designers lose money on 'payment on approval' contracts",
    "target_audience": "Freelance designers and creative studio owners ($5k-$25k projects)",
    "hook": "I lost $18,000 because of one missing word in my freelance contract.",
    "on_screen_text": [
        "$18,000 contract mistake (Section 4)",
        "Never write: 'Payment on approval'",
        "Write: 'Payment on delivery + 5-day review window'",
    ],
    "script_beats": [
        "I lost $18,000 because of one missing word in my freelance contract.",
        "In Section 4, my old agreement said the final 50% was due upon client approval.",
        "The client loved the designs, launched the rebrand, and then paused 'final approval' for four months.",
        "Now I replace 'upon approval' with 'upon delivery of final files, with a 5-business-day deem-approved window.'",
        "Approval is a feeling. Delivery is a calendar date.",
        "That one clause change is the difference between chasing an $18,000 invoice and getting paid on Friday.",
    ],
    "visual_cues": [
        "0-3s: Hold up red-marked contract page on camera; zoom into Section 4 highlight.",
        "3-10s: Split-screen showing old 'upon approval' clause crossed out.",
        "10-18s: Green replacement clause overlay you can screenshot.",
        "18-24s: Direct-to-camera close + loop back to the $18,000 paper.",
    ],
    "caption": (
        "I lost $18,000 because my contract said 'payment on approval' instead of 'payment on delivery.'\n\n"
        "Here is the exact Section 4 wording I use now on every design project:\n"
        "\"Final payment is due within 7 days of file delivery. If no written revision request is received "
        "within 5 business days of delivery, deliverables are deemed approved.\"\n\n"
        "Comment CLAUSE and I'll DM you my full 1-page freelance payment schedule.\n\n"
        "#freelancedesigner #clientcontracts #designbusiness #creativeagency"
    ),
    "keywords": ["freelance contract", "client payment", "design business"],
    "target_duration_s": 24,
    "wpm": 165,
}


def build_demo_ballots(personas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    preset: Dict[str, Dict[str, Any]] = {
        "cold_scroller": {
            "criteria": {
                "thumb_stop_hook": {
                    "score": 4.5,
                    "quote": "I lost $18,000 because of one missing word in my freelance contract.",
                    "rationale": "Immediate $18,000 loss + 'one missing word' creates an instant curiosity gap in 12 words.",
                    "fix": "Show the actual red-lined clause in frame 1 before speaking.",
                },
                "retention_pacing": {
                    "score": 4.0,
                    "quote": "Approval is a feeling. Delivery is a calendar date.",
                    "rationale": "Crisp punchline and loops back to $18,000 at the end, though Beat 3 is slightly wordy.",
                    "fix": "Trim Beat 3 from 17 words to 11 words so the middle doesn't slow down.",
                },
                "proof_credibility": {
                    "score": 4.0,
                    "quote": "upon delivery of final files, with a 5-business-day deem-approved window.",
                    "rationale": "Gives the exact replacement phrasing right away.",
                    "fix": "None needed for a cold viewer.",
                },
                "save_send_value": {
                    "score": 4.5,
                    "quote": "Write: 'Payment on delivery + 5-day review window'",
                    "rationale": "Screenshot-worthy clause that any freelancer will save.",
                    "fix": "Keep the green replacement clause on screen for at least 3 full seconds.",
                },
                "voice_naturalness": {
                    "score": 4.5,
                    "quote": "Approval is a feeling. Delivery is a calendar date.",
                    "rationale": "Sounds like a real person who got burned, zero AI clichés.",
                    "fix": "Keep spoken delivery deadpan.",
                },
            },
            "would_watch_past_3s": True,
            "would_save_or_send": True,
            "top_dealbreaker": "Beat 3 explaining the client delay takes slightly too long before the clause reveal.",
            "highest_leverage_rewrite": "Cut Beat 3 to: 'They launched the rebrand, then stalled final approval for four months.'",
        },
        "retention_editor": {
            "criteria": {
                "thumb_stop_hook": {
                    "score": 4.5,
                    "quote": "$18,000 contract mistake (Section 4)",
                    "rationale": "On-screen text complements spoken hook instead of duplicating every word.",
                    "fix": "Add a subtle paper-snap SFX at 0:00.4.",
                },
                "retention_pacing": {
                    "score": 3.5,
                    "quote": "Now I replace 'upon approval' with 'upon delivery of final files, with a 5-business-day deem-approved window.'",
                    "rationale": "This beat is 17 words (~6.2s at 165 wpm), which risks a mid-reel drop if shot on a single static frame.",
                    "fix": "Split Beat 4 into two visual cuts: Cut A ('Now I ban the word approval.') + Cut B ('I use a 5-day deem-approved delivery window.').",
                },
                "proof_credibility": {
                    "score": 4.5,
                    "quote": "Section 4, my old agreement said the final 50% was due upon client approval.",
                    "rationale": "Specific section number and 50% structure feel authentic.",
                    "fix": "Highlight '5 business days' in yellow on the overlay.",
                },
                "save_send_value": {
                    "score": 4.0,
                    "quote": "Green replacement clause overlay you can screenshot.",
                    "rationale": "Visual screenshot cue drives saves and rewatches.",
                    "fix": "Make sure overlay sits inside the middle 9:16 safe zone away from Reels UI buttons.",
                },
                "voice_naturalness": {
                    "score": 4.5,
                    "quote": "That one clause change is the difference between chasing an $18,000 invoice",
                    "rationale": "Clean loop back to '$18,000' from Beat 1.",
                    "fix": "Cut the audio 0.2s after 'Friday' so it loops seamlessly into 'I lost $18,000'.",
                },
            },
            "would_watch_past_3s": True,
            "would_save_or_send": True,
            "top_dealbreaker": "Beat 4 runs over 6 seconds on a legal sentence.",
            "highest_leverage_rewrite": "Break Beat 4 into two 3-second sentences with a punch-in zoom between them.",
        },
        "niche_skeptic": {
            "criteria": {
                "thumb_stop_hook": {
                    "score": 4.0,
                    "quote": "I lost $18,000 because of one missing word in my freelance contract.",
                    "rationale": "Technically it's a phrase replacement ('approval' -> 'delivery + 5-day window'), not literally one missing word.",
                    "fix": "Change 'one missing word' to 'one bad word' so the hook is 100% literal.",
                },
                "retention_pacing": {
                    "score": 4.0,
                    "quote": "Approval is a feeling. Delivery is a calendar date.",
                    "rationale": "Earned aphorism backed by the mechanism right before it.",
                    "fix": "No pacing issue from a domain standpoint.",
                },
                "proof_credibility": {
                    "score": 3.0,
                    "quote": "If no written revision request is received within 5 business days of delivery, deliverables are deemed approved.",
                    "rationale": "Solid deem-acceptance clause, but in real studio ops, handing over unwatermarked final source files before final payment still leaves leverage gaps.",
                    "fix": "Specify 'delivery of review proof / staged deliverables' so junior freelancers don't hand over raw source files unpaid.",
                },
                "save_send_value": {
                    "score": 4.5,
                    "quote": "Final payment is due within 7 days of file delivery.",
                    "rationale": "Copy-pasteable contract language in the caption is high utility.",
                    "fix": "Add a brief '(not legal advice)' note in caption.",
                },
                "voice_naturalness": {
                    "score": 4.5,
                    "quote": "I lost $18,000 because my contract said 'payment on approval'",
                    "rationale": "Direct, practitioner tone.",
                    "fix": "Change 'missing word' to 'wrong word' in spoken hook.",
                },
            },
            "would_watch_past_3s": True,
            "would_save_or_send": True,
            "top_dealbreaker": "Saying 'one missing word' when it's actually swapping 'approval' for a deem-approved delivery clause.",
            "highest_leverage_rewrite": "Open with: 'I lost $18,000 because of one wrong word in my freelance contract.'",
        },
        "icp_buyer": {
            "criteria": {
                "thumb_stop_hook": {
                    "score": 5.0,
                    "quote": "I lost $18,000 because of one missing word in my freelance contract.",
                    "rationale": "Every freelancer has been ghosted on a final milestone; hits a visceral nerve immediately.",
                    "fix": "None.",
                },
                "retention_pacing": {
                    "score": 4.5,
                    "quote": "Approval is a feeling. Delivery is a calendar date.",
                    "rationale": "Fast, memorable, and easy to repeat to a studio partner.",
                    "fix": "None.",
                },
                "proof_credibility": {
                    "score": 4.5,
                    "quote": "within 5 business days of delivery, deliverables are deemed approved.",
                    "rationale": "Immediately usable in my own SOW.",
                    "fix": "None.",
                },
                "save_send_value": {
                    "score": 5.0,
                    "quote": "Comment CLAUSE and I'll DM you my full 1-page freelance payment schedule.",
                    "rationale": "I would both Save the caption for the clause and DM this Reel to my co-founder.",
                    "fix": "Make sure the CLAUSE DM resource is a clean 1-pager with no email gate.",
                },
                "voice_naturalness": {
                    "score": 4.5,
                    "quote": "Approval is a feeling. Delivery is a calendar date.",
                    "rationale": "Clear, peer-to-peer tone.",
                    "fix": "None.",
                },
            },
            "would_watch_past_3s": True,
            "would_save_or_send": True,
            "top_dealbreaker": "No major dealbreaker; just ensure the DM template is instant.",
            "highest_leverage_rewrite": "Keep caption clause verbatim; it's the main reason I'm saving.",
        },
        "voice_humanizer": {
            "criteria": {
                "thumb_stop_hook": {
                    "score": 4.5,
                    "quote": "I lost $18,000 because of one missing word in my freelance contract.",
                    "rationale": "First-person, active verb, concrete dollar figure.",
                    "fix": "Swap 'missing word' to 'wrong word' for cleaner logic.",
                },
                "retention_pacing": {
                    "score": 4.0,
                    "quote": "Approval is a feeling. Delivery is a calendar date.",
                    "rationale": "Strong rhythmic contrast (6 words + 6 words) after longer narrative sentences.",
                    "fix": "Shorten Beat 4 for easier one-breath spoken delivery.",
                },
                "proof_credibility": {
                    "score": 4.0,
                    "quote": "Section 4, my old agreement said the final 50% was due upon client approval.",
                    "rationale": "Concrete details ('Section 4', 'final 50%', 'four months') beat vague adjectives.",
                    "fix": "None.",
                },
                "save_send_value": {
                    "score": 4.5,
                    "quote": "Comment CLAUSE and I'll DM you my full 1-page freelance payment schedule.",
                    "rationale": "Single clear ask matched to the topic.",
                    "fix": "None.",
                },
                "voice_naturalness": {
                    "score": 4.5,
                    "quote": "I lost $18,000 because my contract said 'payment on approval' instead of 'payment on delivery.'",
                    "rationale": "First 96 chars of caption finish a complete thought before the 125-char fold and contain zero AI slop terms.",
                    "fix": "Include the exact phrase 'freelance contract' in the caption so all 3 target search keywords appear verbatim.",
                },
            },
            "would_watch_past_3s": True,
            "would_save_or_send": True,
            "top_dealbreaker": "Caption says 'my contract' instead of 'my freelance contract', missing one of the three target SEO keywords.",
            "highest_leverage_rewrite": "Change caption line 1 to: 'I lost $18,000 because my freelance contract said \"payment on approval\"...'",
        },
    }

    ballots: List[Dict[str, Any]] = []
    for p in personas:
        template = preset.get(p["id"]) or preset["cold_scroller"]
        ballots.append(
            {
                "persona_id": p["id"],
                "persona_name": p["name"],
                "criteria": template["criteria"],
                "binary_gates": {
                    "no_greeting_or_begging": True,
                    "single_clear_cta": True,
                    "no_unverified_fabrication": True,
                    "caption_fold_complete": True,
                },
                "would_watch_past_3s": template["would_watch_past_3s"],
                "would_save_or_send": template["would_save_or_send"],
                "top_dealbreaker": template["top_dealbreaker"],
                "highest_leverage_rewrite": template["highest_leverage_rewrite"],
            }
        )
    return ballots


# ---------------------------------------------------------------------------
# 7. CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Multi-Subagent Persona Review Panel & Calibrated Aggregator for Instagram Reels."
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("personas", help="List the 8 orthogonal reviewer personas and their domain weights.")

    prep = sub.add_parser("prepare", help="Run deterministic pre-checks and generate N blinded subagent prompts.")
    prep.add_argument("--packet", required=True, help="Path to Reel packet JSON file.")
    prep.add_argument("--n", type=int, default=5, help="Number of subagent personas to spawn (default 5, max 8).")
    prep.add_argument("--personas", help="Optional comma-separated persona IDs.")
    prep.add_argument("--out-dir", help="Optional directory to write individual prompt files and deterministic floor JSON.")
    prep.add_argument("--json", action="store_true", help="Emit JSON bundle of prompts + deterministic floor to stdout.")

    agg = sub.add_parser("aggregate", help="Validate N subagent JSON ballots and compute calibrated final score.")
    agg.add_argument("--packet", required=True, help="Path to Reel packet JSON file.")
    agg.add_argument("--ballots", required=True, help="Path to JSON file (array of ballots) or directory of ballot .json files.")
    agg.add_argument("--json", action="store_true", help="Print full JSON report instead of formatted table.")

    demo = sub.add_parser("demo", help="Run a complete end-to-end demonstration with N subagents.")
    demo.add_argument("--n", type=int, default=5, help="Number of subagents in demo (default 5).")
    demo.add_argument("--json", action="store_true", help="Print JSON output.")

    args = parser.parse_args()

    if args.cmd == "personas":
        for idx, p in enumerate(PERSONA_POOL, 1):
            w_str = ", ".join(f"{k}={int(v*100)}%" for k, v in p["weights"].items())
            print(f"{idx}. {p['id']:<22} {p['name']}")
            print(f"   Domain     : {p['domain']}")
            print(f"   Personality: {p['personality']}")
            print(f"   Weights    : {w_str}\n")
        return 0

    if args.cmd == "prepare":
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8-sig"))
        det_floor = run_deterministic_floor(packet)
        pids = [x.strip() for x in args.personas.split(",") if x.strip()] if args.personas else None
        personas = select_personas(args.n, pids)
        prompts = [
            {
                "persona_id": p["id"],
                "persona_name": p["name"],
                "domain": p["domain"],
                "prompt": build_subagent_prompt(p, packet, det_floor),
            }
            for p in personas
        ]
        if args.out_dir:
            out_dir = Path(args.out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "deterministic_floor.json").write_text(json.dumps(det_floor, indent=2), encoding="utf-8")
            for item in prompts:
                (out_dir / f"prompt_{item['persona_id']}.md").write_text(item["prompt"], encoding="utf-8")
        if args.json or not args.out_dir:
            print(json.dumps({"deterministic_floor": det_floor, "subagent_prompts": prompts}, indent=2))
        else:
            print(f"Prepared {len(prompts)} blinded subagent prompts in {args.out_dir}")
        return 0

    if args.cmd == "aggregate":
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8-sig"))
        bpath = Path(args.ballots)
        if bpath.is_dir():
            ballots = [
                json.loads(p.read_text(encoding="utf-8-sig"))
                for p in sorted(bpath.glob("*.json"))
                if p.name != "deterministic_floor.json"
            ]
        else:
            raw = json.loads(bpath.read_text(encoding="utf-8-sig"))
            ballots = raw["ballots"] if isinstance(raw, dict) and "ballots" in raw else raw
        result = aggregate_jury(packet, ballots)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_jury_report(result))
        return 0

    if args.cmd == "demo":
        personas = select_personas(args.n)
        ballots = build_demo_ballots(personas)
        result = aggregate_jury(DEMO_PACKET, ballots)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_jury_report(result))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
