# Attribution and source map

This package combines and redistributes the canonical source files from these MIT-licensed projects:

1. Sergey Bulaev, [`sergebulaev/instagram-skills`](https://github.com/sergebulaev/instagram-skills), copyright (c) 2026 Sergey Bulaev.
2. Jake Schincariol, [`Jakeschincariol/instagram-agent-skill`](https://github.com/Jakeschincariol/instagram-agent-skill), copyright notice as stated in the upstream `LICENSE`.

The source snapshots used here are `1e6fb1691e4f88aa455dd8ba5f74d1239d8091cc` and `d03c56bb598be770c60b201f94237e5d1a4268a6`, respectively. The upstream directories preserve their original files; this repository adds the cross-agent router and attribution/documentation.

Their complete upstream MIT license texts are preserved in `licenses/sergebulaev-MIT.txt` and `licenses/jakeschincariol-MIT.txt`. The original source files are kept under `skills/instagram-content-studio/upstream/sergebulaev/` and `skills/instagram-content-studio/upstream/jakeschincariol/`. The generated nested Codex marketplace mirror in the first repository is omitted because it duplicates its canonical files and is tool-specific packaging, not a distinct capability. Vendor manifests and instructions remain only as upstream source material; the combined entry point does not require them.

## Capabilities mapped to upstream material

| Combined workflow | Source prompts, data, scripts, or references |
| --- | --- |
| Captions, voice, humanizing, caption audit | Both projects' caption and humanizer skills; Jake's `caption.py`, `humanize.py`, `detect.py`, `slop.json`; Sergey Bulaev's voice rules, caption checklist, audit checklist, and scrub references |
| Reels, hook options, timing | Jake's Reel skill, `hookscore.py`, `beats.py`, `hooks.json`; Sergey Bulaev's hook extractor, hook formulas, and examples |
| Carousels and illustrations | Both carousel skills and architecture references; optional illustration sub-skill and Pixfaro client |
| Stories | Jake's story skill |
| Content calendar and pillars | Both planning skills; pillar framework and example week |
| Profile audit | Both profile skills; Jake's 100-point rubric |
| Niche/audience research | Sergey Bulaev's audience-insights skill and Apify client; Jake's manual viral research skill and `swipe.py` |
| Repurposing | Both projects' repurposing skills |
| Performance review | Jake's audit skill; Sergey Bulaev's post-audit sub-skill |
| Comments, replies, DMs | Jake's comment, reply, and DM skills |
| Publishing and media flow | Sergey Bulaev's media workflow, approval helper, backend selector, Publora client, URL parser, and security notes |
| Hashtag selection | Sergey Bulaev's hashtag strategist and sourcing guide; Jake's caption linter |

## Research references

Checked on 2026-10-15. Prefer these primary sources for platform policy and product behavior; their current content takes precedence over dated numbers in upstream prompt files:

- [Instagram for Creators: Best Practices](https://creators.instagram.com/best-practices)
- [Instagram for Creators: Understand Instagram Insights](https://creators.instagram.com/grow/insights)
- [Instagram for Creators: Algorithms and Ranking](https://creators.instagram.com/grow/algorithms-and-ranking)
- [Instagram for Creators: Recommendations and eligibility](https://creators.instagram.com/blog/instagram-recommendations-eligibility-tips-creators)
- [Instagram for Creators: Rewarding original creators (April 30, 2026)](https://creators.instagram.com/blog/rewarding-original-creators-on-instagram)
- [Meta for Developers: Instagram content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing)

Notable update: Instagram's April 30, 2026 announcement extended originality protections to photos and carousels as well as Reels. Do not treat generic timing, ranking, hashtag, or hook-score advice as a guarantee. The Jake hook score is a local heuristic; its README reports testing on a small corpus of YouTube Shorts, not a predictive validation on Instagram Reels.

## Adaptation and scope

The files under `upstream/` are included as source material and are not silently rewritten. The combined `SKILL.md` supplies agent-neutral routing and resolves conflicts: drafts first, no invented evidence, use account-specific Insights where available, and obtain explicit approval before any external write action. Some optional clients contact third-party services; review their code and upstream security documentation before use.
