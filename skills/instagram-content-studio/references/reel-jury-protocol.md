# Optional Multi-Subagent Reel Review Jury (`reel_jury.py`)

When an AI agent creates or revises a Reel (hook + spoken beat sheet + on-screen text + visual cues + caption), it can optionally convene **$N$ independent test subagents** (default `N=5`, configurable `3` to `8`) to stress-test and score the Reel before the creator shoots it.

---

## Why This Design Prevents Random or Sycophantic Scores

This workflow is modeled on findings from multi-agent evaluation research (**ChatEval**, **MAJ-Eval** ACL 2026, **LLM-Rubric**, **0–5 Grading Scale Alignment** 2026, and **Anchoring Bias in LLM-as-a-Judge** 2026) and multi-persona skill panels:

1. **40% Deterministic Tool Floor (`hookscore.py` + `beats.py` + `caption.py` + `detect.py`)**
   Subagents do not make up the whole score. `40%` of the final score comes directly from deterministic local code checking hook length/specificity, spoken word-per-minute beat durations, the 125-character caption fold, hashtag caps, and slop density.
2. **Blinded Parallel Execution (Zero Score Anchoring)**
   Each of the $N$ subagents is spawned in parallel with its own context window. `reel_jury.py prepare` gives each subagent the Reel packet and objective structural measurements (word count, duration, 125-char visible window), **never** a prior numerical score or another subagent's opinion.
3. **0–5 Behaviorally Anchored Rating Scale (BARS) + Mandatory Quote Verification**
   Instead of arbitrary `1–100` guesses, every subagent scores 5 orthogonal criteria on a `0–5` scale where each integer (`0, 1, 2, 3, 4, 5`) has a concrete behavioral definition. Every score **must** include an exact verbatim substring quote from the Reel packet (`quote`) or `MISSING:<what is absent>`. `reel_jury.py aggregate` verifies that each quote actually exists in the packet and penalizes ungrounded scores.
4. **Orthogonal Persona Lenses & Domain Weight Vectors**
   Each reviewer persona weights the 5 criteria according to its specialty rather than acting as a generic critic:
   - `cold_scroller` — **Maya (Ruthless Cold Feed Scroller)**: 45% weight on 3s thumb-stop hook, 25% on pacing.
   - `retention_editor` — **Devon (Short-Form Retention & Pacing Editor)**: 45% weight on 2–4s beat pacing & loop payoff.
   - `niche_skeptic` — **Dr. Aris (Adversarial Domain Skeptic)**: 50% weight on practitioner proof, mechanism accuracy, and anti-BS.
   - `icp_buyer` — **Elena (Target Audience / Buyer)**: 45% weight on Save utility, DM Send trigger, and CTA friction.
   - `voice_humanizer` — **Nora (Spoken-Word & Anti-Slop Director)**: 50% weight on ear-tested spoken cadence and zero AI tells.
   - `algorithm_packager` — **Kai (Instagram SEO & Trial-Reel Strategist)**: focuses on 125-char caption fold, keywords, and non-follower discovery.
   - `brand_guardian` — **Sloane (Brand Trust & Positioning Reviewer)**: focuses on claim safety, originality compliance, and authority.
   - `conversion_strategist` — **Marcus (DM Funnel & Comment Architect)**: focuses on comment keyword triggers and DM handoffs.
5. **Preserved Disagreements & Hard Gate Caps**
   If two personas disagree by $\ge 2.0$ points on the 0–5 scale (for example, `cold_scroller` loves a dramatic hook that `niche_skeptic` flags as overclaimed), the aggregator surfaces the exact disagreement instead of hiding it in an average. Majority failures on binary gates (`no_unverified_fabrication`, `no_greeting_or_begging`, `single_clear_cta`, `caption_fold_complete`) apply hard score ceilings.

---

## Step-by-Step Agent Workflow

### Step 1: Write `reel_packet.json`
After drafting the Reel, save the candidate packet as JSON:

```json
{
  "topic": "Why freelance designers lose money on 'payment on approval' contracts",
  "target_audience": "Freelance designers and studio owners",
  "hook": "I lost $18,000 because of one missing word in my freelance contract.",
  "on_screen_text": [
    "$18,000 contract mistake (Section 4)",
    "Never write: 'Payment on approval'",
    "Write: 'Payment on delivery + 5-day review window'"
  ],
  "script_beats": [
    "I lost $18,000 because of one missing word in my freelance contract.",
    "In Section 4, my old agreement said the final 50% was due upon client approval.",
    "The client loved the designs, launched the rebrand, and then paused 'final approval' for four months.",
    "Now I replace 'upon approval' with 'upon delivery of final files, with a 5-business-day deem-approved window.'",
    "Approval is a feeling. Delivery is a calendar date.",
    "That one clause change is the difference between chasing an $18,000 invoice and getting paid on Friday."
  ],
  "visual_cues": [
    "0-3s: Hold up red-marked contract page on camera",
    "3-10s: Split-screen showing old clause crossed out",
    "10-18s: Green replacement clause overlay",
    "18-24s: Direct-to-camera close + loop back to paper"
  ],
  "caption": "I lost $18,000 because my freelance contract said 'payment on approval'...",
  "keywords": ["freelance contract", "client payment", "design business"],
  "target_duration_s": 24,
  "wpm": 165
}
```

### Step 2: Prepare the Deterministic Floor & $N$ Blinded Subagent Prompts
Run `reel_jury.py prepare`:

```sh
python scripts/reel_jury.py prepare --packet reel_packet.json --n 5 --out-dir jury_run
```

This writes `jury_run/deterministic_floor.json` and `jury_run/prompt_<persona_id>.md` for each of the $N$ personas.

### Step 3: Spawn $N$ Subagents in Parallel
- **In agents with a Subagent / Task tool (Claude Code, OpenCode, Codex, Cursor, etc.):** Spawn all $N$ subagents **in a single parallel tool-call batch**, passing each subagent only its own `prompt_<persona_id>.md` content. Each subagent returns its strict JSON ballot.
- **Fallback for single-thread chat agents:** Evaluate each persona sequentially using the generated prompts and collect the JSON ballots.

### Step 4: Aggregate Ballots & Apply Top Rewrites
Save the returned JSON ballots to `jury_run/ballots.json` (or individual `.json` files in `jury_run/ballots/`) and run:

```sh
python scripts/reel_jury.py aggregate --packet reel_packet.json --ballots jury_run/ballots.json
```

If the verdict is below `80 / 100` (or if a hard gate failed), apply the `TOP PRIORITY REWRITES BEFORE SHOOTING` to the Reel draft before presenting the final version to the user.
