# Instagram Content Studio (`instagram-agent-skill`)

A unified, agent-neutral Instagram skill repository that combines the full source toolkits of:

- **[sergebulaev/instagram-skills](https://github.com/sergebulaev/instagram-skills)** (9 marketing/content-engineering skills + Publora publishing, Apify niche reading, Pixfaro carousel illustration clients)
- **[Jakeschincariol/instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill)** (13 creator/Reels skills + 6 zero-dependency local Python linters/scorers, 26 hook formulas, 100-point profile rubric, 154-term slop lexicon)

plus two new research-backed tools:
1. **`scripts/reel_jury.py` (Optional $N$-Subagent Reel Review Panel & Calibrated Aggregator)** — spawns $N$ orthogonal reviewer subagents (`cold_scroller`, `retention_editor`, `niche_skeptic`, `icp_buyer`, `voice_humanizer`, etc.) using a blinded **0–5 Behaviorally Anchored Rating Scale (BARS)** + mandatory verbatim quote verification combined with a **40% deterministic tool floor** (`hookscore.py` + `beats.py` + `caption.py` + `detect.py`) so scores are never random.
2. **`scripts/insights_lab.py` (Insights & Trial Reels Experiment Lab)** — analyzes your own post CSV/TSV exports against account-median per-reach baselines and outputs Trial Reels promote/re-edit/archive verdicts,

all wrapped in a single cross-agent `SKILL.md` router that works in any AI agent (Claude Code, Codex, OpenCode, Cursor, Cline, Windsurf, Hermes, or plain chat).

---

## Install (Any Agent)

### 1. Skills CLI (Claude Code, Codex, Cursor, OpenCode, etc.)

```sh
npx skills add Jeet1309/instagram-agent-skill
```

Select `instagram-content-studio` when prompted.

### 2. Git Clone into Any Agent's Skills Folder

```sh
# Universal / OpenCode / Agent Skills standard
git clone https://github.com/Jeet1309/instagram-agent-skill.git
cp -r instagram-agent-skill/skills/instagram-content-studio ~/.agents/skills/

# Claude Code
cp -r instagram-agent-skill/skills/instagram-content-studio ~/.claude/skills/
```

Other agents (Aider, Windsurf, custom LLM wrappers, or web chat) can load [`skills/instagram-content-studio/SKILL.md`](skills/instagram-content-studio/SKILL.md) as system/project instructions and read the adjacent `upstream/` and `scripts/` folders on demand.

---

## How This Differs from the Two Original Skills

| Capability / Design | `sergebulaev/instagram-skills` | `Jakeschincariol/instagram-agent-skill` | **This Combined Repo (`Jeet1309/instagram-agent-skill`)** |
| --- | --- | --- | --- |
| **Agent compatibility** | Built around Claude Code & Codex plugin manifests | Built around Claude Code `/ig-*` slash commands & `~/.claude/instagram/` paths | **Agent-neutral (`SKILL.md` standard)**: works via natural language in any agent without requiring slash commands or vendor-specific paths |
| **Preserved original prompts & scripts** | 9 marketing skills + `lib/` (`publora_client.py`, `apify_client.py`, `pixfaro_client.py`, `url_parser.py`, `approval.py`) | 13 creator skills + 6 local scripts (`hookscore.py`, `beats.py`, `caption.py`, `humanize.py`, `detect.py`, `swipe.py`) | **Includes 100% of both upstream trees** under `skills/instagram-content-studio/upstream/` plus all data files, rubrics, and templates |
| **Reels production & timing** | Hook extraction & 10 hook formulas, no spoken beat timer | 26 scored hook formulas + `hookscore.py` + `beats.py` spoken timing sheet | **Combines both** (36 total formula references + local hook scorer + spoken beat timer) |
| **Humanizer & AI-tell scrubbing** | Prompt-based 2026 density rules, em-dash cap (~1/100 words), pre-publish audit checklist | `humanize.py` + `detect.py` + `slop.json` (strips zero-width chars, normalizes typography, flags structural tells) | **Runs both**: local deterministic cleanup/scoring (`humanize.py` / `detect.py`) + nuanced editorial scrub and voice rules |
| **Hashtag & policy accuracy** | Some files still reference the legacy 30-hashtag ceiling | Enforces the 5-hashtag cap in `caption.py` | **Reconciles conflicts** in the top-level router and prioritizes current official Instagram guidance (including April 2026 originality rules for carousels/photos) |
| **Publishing & external tools** | Optional Publora auto-scheduling, Apify niche reading, Pixfaro image generation | Strictly copy-paste only; no API clients | **Draft-first by default, opt-in adapters preserved** when the user explicitly configures `.env` and approves publishing |
| **Post-publish Insights & Trial Reels testing** | Descriptive audit prompts only | `ig-audit` prompt + `swipe.py` for competitor outlier ranking | **Adds `scripts/insights_lab.py`** to score your own post CSV/TSV exports on Sends/Reach, Saves/Reach, 3s View Rate, Watch %, and Trial Reels promote/archive decisions |
| **Multi-subagent pre-shoot Reel evaluation** | Single-agent draft review | Single-agent hook & beat scoring | **Adds `scripts/reel_jury.py` + `references/reel-jury-protocol.md`**: spawns $N$ orthogonal persona subagents in parallel and combines their quote-verified 0–5 BARS ballots (60%) with the deterministic local tool floor (40%) |

---

## Added Value from Research: `insights_lab.py` & Trial Reels Workflow

Both upstream repos focus heavily on pre-publish text heuristics. However, Jake's own benchmark on 74 short-form hooks found that static text scoring separates hits from misses at **AUC 0.56** (near coin-flip) once obviously bad hooks are removed, and Instagram's 2025-2026 creator guidance emphasizes **Watch Time**, **3-second View Rate**, **Sends per Reach** (especially for non-follower discovery), **Saves per Reach**, **Originality across photos/carousels/Reels**, and **Trial Reels** (24h-72h non-follower testing).

To turn those findings into an executable tool, this repo adds [`skills/instagram-content-studio/scripts/insights_lab.py`](skills/instagram-content-studio/scripts/insights_lab.py) (Python 3 stdlib, zero dependencies):

```sh
# Run the built-in demonstration
python skills/instagram-content-studio/scripts/insights_lab.py --demo

# Analyze your own Instagram Insights CSV or TSV export
python skills/instagram-content-studio/scripts/insights_lab.py my_posts.csv --topic "freelance pricing clauses"
```

What `insights_lab.py` does:
1. Calculates account-median baselines for **Reach**, **Sends per 1k reach**, **Saves per 1k reach**, **Average Watch %**, and **3-second View Rate**.
2. Diagnoses whether a post underperformed in the **first 3 seconds** (hook issue) vs **mid-video retention** (pacing/beat issue) vs **shareability/save utility**.
3. Gives a concrete **Trial Reel verdict** (`PROMOTE TO EVERYONE`, `RE-EDIT BODY`, or `KEEP AS TRIAL / ARCHIVE`).
4. Prints a structured **1-variable next experiment** (holding topic/payoff constant while testing hook framing).

---

## Added Value from Multi-Agent Evaluation Research: $N$-Subagent Reel Jury (`reel_jury.py`)

When an agent finishes drafting a Reel, asking a single LLM *"rate my Reel 1-100"* produces sycophantic, drifting numbers. Based on multi-agent judge research (*ChatEval*, *MAJ-Eval* ACL 2026, *LLM-Rubric*, *0–5 Grading Scale Alignment* 2026, and *Anchoring Bias in LLM Judges* 2026), [`skills/instagram-content-studio/scripts/reel_jury.py`](skills/instagram-content-studio/scripts/reel_jury.py) and [`references/reel-jury-protocol.md`](skills/instagram-content-studio/references/reel-jury-protocol.md) implement a non-random **3-layer evaluation panel**:

1. **40% Deterministic Tool Floor**: Runs `hookscore.py`, `beats.py`, `caption.py`, and `detect.py` directly on the Reel packet so 40% of the score is anchored to repeatable code.
2. **60% Blinded $N$-Subagent Persona Jury ($N=3..8$)**: Generates self-contained prompts for $N$ orthogonal personas (`cold_scroller`, `retention_editor`, `niche_skeptic`, `icp_buyer`, `voice_humanizer`, `algorithm_packager`, `brand_guardian`, `conversion_strategist`). Each subagent runs in parallel, is blinded to other subagents' scores, grades 5 criteria on a **0–5 Behaviorally Anchored Rating Scale (BARS)**, and **must cite a verbatim quote** from the Reel packet for every score.
3. **Calibrated Aggregation & Disagreement Preservation**: Verifies every quote against the Reel text (penalizing ungrounded claims), applies each persona's domain weight vector, computes the 95% confidence interval and inter-rater spread, preserves disagreements ($\ge 2.0$ spread), enforces binary dealbreaker caps, and outputs the top 3 rewrites before you shoot.

```sh
# List the 8 reviewer personas and their domain weights
python skills/instagram-content-studio/scripts/reel_jury.py personas

# Run a full 5-subagent demonstration
python skills/instagram-content-studio/scripts/reel_jury.py demo --n 5

# Prepare N blinded subagent prompts for your own Reel packet
python skills/instagram-content-studio/scripts/reel_jury.py prepare --packet reel_packet.json --n 5 --out-dir jury_run

# Aggregate the N subagent JSON ballots into a calibrated score & rewrite list
python skills/instagram-content-studio/scripts/reel_jury.py aggregate --packet reel_packet.json --ballots jury_run/ballots.json
```

---

## Included Local CLI Tools

All local scripts run with standard Python 3 (no `pip install` needed):

```sh
cd skills/instagram-content-studio

# New: Insights & Trial Reels experiment analyzer
python scripts/insights_lab.py --demo

# From Jake Schincariol's toolkit:
python upstream/jakeschincariol/skills/ig-reel/hookscore.py --help
python upstream/jakeschincariol/skills/ig-reel/beats.py --help
python upstream/jakeschincariol/skills/ig-caption/caption.py --help
python upstream/jakeschincariol/skills/ig-human/humanize.py --help
python upstream/jakeschincariol/skills/ig-human/detect.py --help
python upstream/jakeschincariol/skills/ig-viral/swipe.py --help

# From Sergey Bulaev's toolkit (stdlib URL parser + approval card):
python upstream/sergebulaev/lib/url_parser.py "https://www.instagram.com/reel/C9_aBcDeF/"
```

Optional third-party integrations (`Publora`, `Apify`, `Pixfaro`) live in `skills/instagram-content-studio/upstream/sergebulaev/lib/` and require `pip install -r skills/instagram-content-studio/upstream/sergebulaev/requirements.txt` plus user-supplied keys in `.env`.

---

## Attribution & License

MIT Licensed ([`LICENSE`](LICENSE)). Full upstream MIT license notices and commit references are preserved in [`ATTRIBUTION.md`](ATTRIBUTION.md), [`licenses/sergebulaev-MIT.txt`](licenses/sergebulaev-MIT.txt), and [`licenses/jakeschincariol-MIT.txt`](licenses/jakeschincariol-MIT.txt).
