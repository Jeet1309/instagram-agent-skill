# Instagram Content Studio (`instagram-agent-skill`)

A unified, agent-neutral Instagram skill repository that combines the full source toolkits of:

- **[sergebulaev/instagram-skills](https://github.com/sergebulaev/instagram-skills)** (9 marketing/content-engineering skills + Publora publishing, Apify niche reading, Pixfaro carousel illustration clients)
- **[Jakeschincariol/instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill)** (13 creator/Reels skills + 6 zero-dependency local Python linters/scorers, 26 hook formulas, 100-point profile rubric, 154-term slop lexicon)

plus a new **research-backed Insights & Trial Reels Experiment Lab (`scripts/insights_lab.py`)** and a single cross-agent `SKILL.md` router that works in any AI agent (Claude Code, Codex, OpenCode, Cursor, Cline, Windsurf, Hermes, or plain chat).

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
