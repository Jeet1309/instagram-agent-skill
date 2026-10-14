# Instagram Content Studio (`instagram-agent-skill`)

**Turn any AI agent into a full-stack Instagram creative team, pre-shoot retention editor, multi-agent test jury, and post-publish analytics lab.**

Most Instagram AI prompts generate generic, robotic captions that die behind the `... more` fold or scripts that lose viewers in the first three seconds. **Instagram Content Studio** gives your agent a complete, production-grade operating system for Instagram—from finding outlier ideas and scripting Reels with timed beat sheets, to stress-testing drafts with a panel of independent reviewer subagents, auditing your profile, and analyzing Trial Reels data.

Works out of the box in **Claude Code, Codex, OpenCode, Cursor, Cline, Windsurf, Hermes, or any agent that reads `SKILL.md`**—with zero required API keys.

---

## What This Skill Does (And Why Use It)

### 1. Writes Reels You Can Actually Say Out Loud (Before You Waste a Take)
Instead of handing you a wall of text, the skill builds Reels around **36 proven hook formulas**, scores your opening line on 5 attention properties (`hookscore.py`), and maps your script into a **spoken word-per-minute beat sheet (`beats.py`)**. It flags hooks that run past 3 seconds, static beats longer than 4 seconds where viewers swipe away, abstract runs with no concrete numbers, and endings that fail to loop back to the first line.

### 2. Convenes an $N$-Subagent Test Jury (`reel_jury.py`) So Scores Are Never Random
When a Reel draft is ready, your agent can optionally spawn **$N$ independent reviewer subagents in parallel** (`cold_scroller`, `retention_editor`, `niche_skeptic`, `icp_buyer`, `voice_humanizer`, `algorithm_packager`, `brand_guardian`, `conversion_strategist`).
- **40% Deterministic Tool Floor:** Runs local calculators (`hookscore.py`, `beats.py`, `caption.py`, `detect.py`) first so 40% of the score is anchored to repeatable code.
- **60% Blinded Persona Panel (0–5 BARS + Quote Verification):** Each subagent is blinded to other reviewers' scores, grades 5 criteria on a **0–5 Behaviorally Anchored Rating Scale**, and **must quote an exact substring** from your Reel packet for every score. Ungrounded scores are penalized automatically, disagreements are preserved, and the top 3 rewrites are surfaced before you record.

### 3. Previews the 125-Character Feed Fold & Strips AI Slop
Instagram hides everything past ~125 characters behind a tap. `caption.py` renders the exact feed preview box, checks keyword placement, enforces Instagram's **5-hashtag cap**, and verifies a single clear CTA. Then `humanize.py` + `detect.py` strip invisible zero-width watermarks, curly-quote/em-dash fingerprints, and 154 stock AI phrases (`slop.json`) while auditing sentence burstiness and concrete noun density.

### 4. Runs Your Entire Account Workflow End-to-End
- **Carousels & Stories:** 6–10 slide retention arcs (cover hook -> front-loaded value -> save/follow payoff) and daily Story sequences with DM keyword triggers.
- **Profile 100-Point Audit:** Scores your profile against a 12-part rubric (`rubric.json`) and rewrites your searchable Name field, 150-char bio, highlights, and pinned posts in fix-first order.
- **Weekly Content Planner & Repurposer:** Turns podcasts, YouTube scripts, newsletters, or LinkedIn posts into native Reels and carousels without cross-platform artifacts.
- **Comments, Replies & DM Funnels:** Sorts comment threads by intent (keyword / lead / substance / question / support) and drafts non-pushy DM deliveries and collab pitches.
- **Optional Publishing & Visuals:** Draft-first by default (nothing posts without your explicit OK), with optional adapters for **Publora** (draft -> S3 upload -> schedule), **Apify** (niche/profile reading), and **Pixfaro** (carousel slide illustration).

### 5. Evaluates Post-Publish Insights & Trial Reels (`insights_lab.py`)
Pre-publish text scores can catch bad hooks, but your retention graph decides winners. `insights_lab.py` reads your Instagram Insights CSV/TSV exports, computes your account's own median baselines (**Sends per 1k reach**, **Saves per 1k reach**, **Average Watch %**, **3s View Rate**), gives a clear **Trial Reel verdict** (`PROMOTE TO EVERYONE`, `RE-EDIT BODY`, or `KEEP AS TRIAL / ARCHIVE`), and generates your next **1-variable experiment**.

---

## How It Works

1. **Ask naturally in any agent** (no vendor-specific slash commands required):
   - *"Write a 25-second Reel about why freelance designers lose money on 'payment on approval' contracts, time the beats, and run a 5-subagent jury review."*
   - *"Turn these notes into an 8-slide save-worthy carousel and lint the caption for the 125-char fold."*
   - *"Score my Instagram bio and pinned posts against the 100-point rubric and rewrite what lost points."*
   - *"Run `insights_lab.py` on my last 10 Reels CSV and tell me whether to promote my latest Trial Reel."*
2. **Router loads only what is needed:** [`skills/instagram-content-studio/SKILL.md`](skills/instagram-content-studio/SKILL.md) routes your prompt to the matching specialist guide, rubric, or Python tool without bloating your context window.
3. **Deterministic tools + optional subagent jury run locally:** Standard-library Python 3 scripts verify timing, truncation, slop density, and jury ballots on your machine.
4. **You stay in control:** Every workflow finishes with a copy-ready draft (or waits for your explicit confirmation if you configured optional publishing).

---

## Install (Works in Any Agent)

### Option 1: Skills CLI (Claude Code, Codex, Cursor, OpenCode, etc.)

```sh
npx skills add Jeet1309/instagram-agent-skill
```

Select `instagram-content-studio` when prompted.

### Option 2: Git Clone into Your Agent's Skills Directory

```sh
# Universal / OpenCode / Agent Skills standard
git clone https://github.com/Jeet1309/instagram-agent-skill.git
cp -r instagram-agent-skill/skills/instagram-content-studio ~/.agents/skills/

# Claude Code
cp -r instagram-agent-skill/skills/instagram-content-studio ~/.claude/skills/
```

For chat-only or custom agents (Aider, Windsurf, custom LLM wrappers), load [`skills/instagram-content-studio/SKILL.md`](skills/instagram-content-studio/SKILL.md) as system/project instructions and keep the adjacent `scripts/`, `references/`, and `upstream/` folders accessible.

---

## Local CLI Tools Quickstart

All 8 local analysis scripts run on **Python 3 standard library only** (no `pip install` or API key required):

```sh
cd skills/instagram-content-studio

# 1. N-Subagent Reel Review Jury (40% deterministic + 60% blinded BARS persona panel)
python scripts/reel_jury.py personas
python scripts/reel_jury.py demo --n 5
python scripts/reel_jury.py prepare --packet reel_packet.json --n 5 --out-dir jury_run
python scripts/reel_jury.py aggregate --packet reel_packet.json --ballots jury_run/ballots.json

# 2. Insights & Trial Reels Experiment Analyzer
python scripts/insights_lab.py --demo
python scripts/insights_lab.py my_posts.csv --topic "freelance pricing clauses"

# 3. Reel Hook Scorer & Spoken Beat Sheet Timer
python upstream/jakeschincariol/skills/ig-reel/hookscore.py --hook "I lost $18,000 because of one wrong word in my contract."
python upstream/jakeschincariol/skills/ig-reel/beats.py script.txt --target 25

# 4. Caption 125-Char Fold Linter & Hashtag Cap Checker
python upstream/jakeschincariol/skills/ig-caption/caption.py caption.txt --keywords "freelance contract,design business"

# 5. Humanizer & 5-Signal AI Tell Detector
python upstream/jakeschincariol/skills/ig-human/humanize.py draft.txt --report
python upstream/jakeschincariol/skills/ig-human/detect.py draft.txt

# 6. Competitor Outlier Swipe File Ranker & Instagram URL Parser
python upstream/jakeschincariol/skills/ig-viral/swipe.py captured.tsv
python upstream/sergebulaev/lib/url_parser.py "https://www.instagram.com/reel/C9_aBcDeF/"
```

Optional external adapters (`Publora`, `Apify`, `Pixfaro`) in `skills/instagram-content-studio/upstream/sergebulaev/lib/` can be enabled by installing `skills/instagram-content-studio/upstream/sergebulaev/requirements.txt` and configuring `.env`.

---

## Comparison: How This Differs from the Two Original Skills

This repository combines the full source trees of **[sergebulaev/instagram-skills](https://github.com/sergebulaev/instagram-skills)** and **[Jakeschincariol/instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill)**, reconciles their overlapping rules, and adds `reel_jury.py` and `insights_lab.py`.

| Capability / Design | `sergebulaev/instagram-skills` | `Jakeschincariol/instagram-agent-skill` | **This Combined Repo (`Jeet1309/instagram-agent-skill`)** |
| --- | --- | --- | --- |
| **Agent compatibility** | Built around Claude Code & Codex plugin manifests | Built around Claude Code `/ig-*` slash commands & `~/.claude/instagram/` paths | **Agent-neutral (`SKILL.md` standard)**: works via natural language in any agent without requiring slash commands or vendor-specific paths |
| **Preserved original prompts & scripts** | 9 marketing skills + `lib/` (`publora_client.py`, `apify_client.py`, `pixfaro_client.py`, `url_parser.py`, `approval.py`) | 13 creator skills + 6 local scripts (`hookscore.py`, `beats.py`, `caption.py`, `humanize.py`, `detect.py`, `swipe.py`) | **Includes 100% of both upstream trees** under `skills/instagram-content-studio/upstream/` plus all data files, rubrics, and templates |
| **Reels production & timing** | Hook extraction & 10 hook formulas, no spoken beat timer | 26 scored hook formulas + `hookscore.py` + `beats.py` spoken timing sheet | **Combines both** (36 total formula references + local hook scorer + spoken beat timer) |
| **Multi-subagent pre-shoot Reel evaluation** | Single-agent draft review | Single-agent hook & beat scoring | **Adds `scripts/reel_jury.py` + `references/reel-jury-protocol.md`**: spawns $N$ orthogonal persona subagents in parallel and combines their quote-verified 0–5 BARS ballots (60%) with the deterministic local tool floor (40%) |
| **Post-publish Insights & Trial Reels testing** | Descriptive audit prompts only | `ig-audit` prompt + `swipe.py` for competitor outlier ranking | **Adds `scripts/insights_lab.py`** to score your own post CSV/TSV exports on Sends/Reach, Saves/Reach, 3s View Rate, Watch %, and Trial Reels promote/archive decisions |
| **Humanizer & AI-tell scrubbing** | Prompt-based 2026 density rules, em-dash cap (~1/100 words), pre-publish audit checklist | `humanize.py` + `detect.py` + `slop.json` (strips zero-width chars, normalizes typography, flags structural tells) | **Runs both**: local deterministic cleanup/scoring (`humanize.py` / `detect.py`) + nuanced editorial scrub and voice rules |
| **Hashtag & policy accuracy** | Some files still reference the legacy 30-hashtag ceiling | Enforces the 5-hashtag cap in `caption.py` | **Reconciles conflicts** in the top-level router and prioritizes current official Instagram guidance (including April 2026 originality rules for carousels/photos) |
| **Publishing & external tools** | Optional Publora auto-scheduling, Apify niche reading, Pixfaro image generation | Strictly copy-paste only; no API clients | **Draft-first by default, opt-in adapters preserved** when the user explicitly configures `.env` and approves publishing |

---

## Original Sources, Attribution & License

This project is MIT Licensed ([`LICENSE`](LICENSE)) and builds directly upon:

1. **[sergebulaev/instagram-skills](https://github.com/sergebulaev/instagram-skills)** by Sergey Bulaev ([Creative Content Crafts](https://cccrafts.ai)) — MIT License preserved in [`licenses/sergebulaev-MIT.txt`](licenses/sergebulaev-MIT.txt).
2. **[Jakeschincariol/instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill)** by Jake Schincariol ([opusjake.ai](https://opusjake.ai)) — MIT License preserved in [`licenses/jakeschincariol-MIT.txt`](licenses/jakeschincariol-MIT.txt).

See [`ATTRIBUTION.md`](ATTRIBUTION.md) for the complete capability-to-source map, upstream commit snapshots, and official Instagram/Meta creator research references.
