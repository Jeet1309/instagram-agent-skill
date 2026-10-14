---
name: instagram-content-studio
description: Instagram strategy and content production across Reels, captions, carousels, Stories, profile, planning, research, repurposing, analytics, and optional publishing. Use when the user asks to create, improve, research, plan, or review Instagram content or an Instagram account.
---

# Instagram Content Studio

Use the included upstream prompts, scripts, references, rubrics, and templates as the specialist toolkit. This file is the agent-neutral router and operating contract. Do not assume slash-command support, a particular agent vendor, network access, file access, Python, a browser, or connected services.

## Operating rules

1. Draft first. Never publish, schedule, upload, comment, follow, or send a DM unless the user explicitly requests that exact external action and confirms the final content and destination. When no safe/approved publishing integration is configured, return copy-ready material for the user to post.
2. Do not ask for Instagram passwords, session cookies, or recovery codes. Do not automate browsing, scraping, likes, follows, comments, or unsolicited/bulk DMs. Use user-provided exports, account Insights, official APIs, or user-directed manual research. Third-party adapters are opt-in, not defaults.
3. Never invent personal stories, metrics, credentials, client outcomes, quotations, or sources. Ask for proof or retain a clear placeholder such as `[add your real result]`.
4. Keep the user's voice and constraints. Humanizing means making the writing specific and natural, not evading AI detectors. Do not promise detector results or virality. Local scores and hook formulas are editing prompts, not performance predictions.
5. Platform details expire. For policy, account eligibility, format limits, hashtags, APIs, or ranking claims, verify current official Meta/Instagram documentation when research access exists. Otherwise qualify the uncertainty and avoid turning old upstream numbers into hard constraints.
6. Use audience/account data before generic advice. Distinguish observed data, the user's interpretation, and the recommendation. Small samples and outliers do not prove causation.
7. Ask only for missing information that materially changes the result. If enough context exists, proceed and list any assumptions briefly.

## Toolkit location

All included upstream source files are under this skill's `upstream/` directory:

- `upstream/sergebulaev/` contains the nine marketing skills, references, Python library, API clients, scripts, templates, manifests, and security documentation from `sergebulaev/instagram-skills`.
- `upstream/jakeschincariol/` contains the thirteen creator skills, Python scripts, JSON data/rubrics, voice template, and plugin files from `Jakeschincariol/instagram-agent-skill`.
- `../../ATTRIBUTION.md` in the repository maps capabilities, licenses, and current research links. In an installation that omits repository-level files, the MIT license texts remain in `upstream/*/LICENSE` and `licenses/`.

Use the original specialist prompt as the detailed workflow for the task. Read its adjacent references/data files when it points to them. Treat relative paths as relative to that upstream project root. Do not load the entire toolkit into context when only one workflow is needed.

## Route by user intent

Slash names shown below are optional labels, not required syntax. Any agent can route from ordinary language.

| Intent | Specialist source to load |
| --- | --- |
| Reel idea, hook options, spoken script, on-screen text, beat sheet | `upstream/jakeschincariol/skills/ig-reel/SKILL.md`; use its `hooks.json`, `hookscore.py`, and `beats.py`. For hook analysis/template extraction, also load `upstream/sergebulaev/skills/ig-hook-extractor/SKILL.md`, `references/hook-formulas.md`, and its local references. |
| Research successful posts or patterns in a niche | `upstream/jakeschincariol/skills/ig-viral/SKILL.md` and `swipe.py`. For account/profile or hashtag data with explicitly configured access, load `upstream/sergebulaev/skills/ig-audience-insights/SKILL.md` and inspect `lib/apify_client.py`. |
| Caption, caption lint, or hashtag set | Load both `upstream/jakeschincariol/skills/ig-caption/SKILL.md` and `upstream/sergebulaev/skills/ig-caption-writer/SKILL.md`; use the caption script and relevant caption/voice references. For a dedicated hashtag plan, also load `upstream/sergebulaev/skills/ig-hashtag-strategist/SKILL.md` and its sourcing reference. |
| Carousel | Load both carousel specialist prompts and their architecture references. Use the humanizer only after the user approves the core meaning/copy. Image generation is optional and must be reviewed before use. |
| Stories | `upstream/jakeschincariol/skills/ig-story/SKILL.md`. |
| Weekly/monthly plan | Load `upstream/jakeschincariol/skills/ig-plan/SKILL.md` and `upstream/sergebulaev/skills/ig-content-planner/SKILL.md`; include cadence/timing only when based on the user's constraints or data. |
| Profile audit | Load both profile specialist prompts and `upstream/jakeschincariol/skills/ig-profile/rubric.json`. Treat rubric points as an editing aid, not an objective ranking. |
| Humanize or audit writing | Load both humanizer prompts plus relevant voice, audit, and scrub references. Run local scripts only when Python is available and the user wants a tool-based check. Review suggested edits; never silently alter substantive claims or meaningful Unicode. |
| Repurpose source content | Load both repurposing prompts. Preserve the source's factual claims, transform for native Instagram context, and do not imply the author has experiences they did not provide. |
| Analyze existing post performance or Trial Reels | Load `upstream/jakeschincariol/skills/ig-audit/SKILL.md`, `upstream/sergebulaev/skills/ig-humanizer/sub-skills/post-audit.md`, and run `scripts/insights_lab.py` when CSV/TSV metrics or Trial Reel results are provided. |
| Design a Trial Reel or A/B content experiment | Use the Data-informed planning and research rules below plus `scripts/insights_lab.py --demo` (or user metrics) to specify one variable under test, a 24h-72h readout, and a promotion threshold. |
| Comment, reply, DM/collaboration copy | Load the relevant `ig-comment`, `ig-reply`, or `ig-dm` prompt in `upstream/jakeschincariol/skills/`. Draft only; do not send or bulk automate. Respect consent, context, and platform rules. |
| Publish or schedule media | Load `upstream/sergebulaev/references/media-workflow.md`, `skills/ig-humanizer/sub-skills/illustration.md` only if generating an asset, and inspect the selected backend/client. Require explicit confirmation for the final content, assets, account, and schedule before using a write-capable integration. |

## Combined workflow

For multi-part requests, work in this order and skip irrelevant steps:

1. Identify goal, audience, format, voice, offer/topic, proof/assets, constraints, and desired action. Use `upstream/jakeschincariol/templates/voice.md` or `upstream/sergebulaev/references/voice-profile.md` as optional intake templates; do not require the user to fill them out for a one-off task.
2. Research only as needed. Prefer official platform sources for current rules and the user's own Insights for account strategy. Competitor/viral research must be manual or based on a user-provided/authorized source. Record source and date for claims that can change.
3. Create the requested deliverable using the relevant specialist prompt. For Reels, provide multiple hook options, a spoken draft, on-screen text, visual/shot cues, approximate beat timing, and one clear CTA when appropriate. For carousels, make each slide work in sequence and specify the cover, slide copy, visual direction, and closing action. For captions, preview the opening and include one natural action. Do not force every format into the same template.
4. Run applicable checks: clarity, voice, factual support, accessibility, policy risk, unnecessary repetition, and format-specific lint/timing. Scripts are optional helpers; the agent should still complete the task if they cannot run.
5. Return the draft and concise rationale. Identify placeholders, assumptions, uncertain platform guidance, and any approval needed for an external action. Do not imply that checks guarantee reach or compliance.

## Data-informed planning and research

- Define the goal before choosing a metric: awareness, meaningful engagement, saves/shares, qualified profile visits, follows, leads, or sales.
- When given Insights, use the metric definitions and time window from the export. Compare like with like (same format and reasonably similar audience/goal) and use medians or ranges when outliers distort averages.
- Explain sample size and uncertainty. Recommend one or two experiments with a hypothesis and a success measure instead of declaring a universal winning hook, posting time, hashtag count, or format.
- For public niche research, record the account/post URL, date checked, visible metrics, format, and the account's available baseline. Raw views across accounts of different size are not directly comparable. Never bypass login, rate limits, or access controls.
- If external research is unavailable, use the supplied source material and mark what remains unverified rather than fabricating a trend report.

## Optional scripts and integrations

Jake's tools and the added Insights/Trial Reels lab are standard-library Python scripts and can be run from the installed skill directory, for example:

```sh
python scripts/insights_lab.py --demo
python upstream/jakeschincariol/skills/ig-reel/hookscore.py --help
python upstream/jakeschincariol/skills/ig-reel/beats.py --help
python upstream/jakeschincariol/skills/ig-caption/caption.py --help
python upstream/jakeschincariol/skills/ig-human/humanize.py --help
python upstream/jakeschincariol/skills/ig-human/detect.py --help
python upstream/jakeschincariol/skills/ig-viral/swipe.py --help
```

The first project also has `lib/url_parser.py`, `lib/approval.py`, `lib/backend_selector.py`, and optional Apify, Publora, and Pixfaro clients. Their dependencies and environment variables are documented in `upstream/sergebulaev/requirements.txt` and `.env.example`. Do not request or expose secrets in chat or commit them. The approval helper formats a review card; it is not a technical enforcement boundary.

## Conflicts and precedence

This combined operating contract takes precedence over vendor-specific install notes and inconsistent or time-sensitive claims in the preserved upstream prompts. The user's explicit request and safety constraints take precedence over all generic workflows. Among platform facts, current official Meta/Instagram documentation takes precedence over either project's dated references. Where sources disagree or cannot be checked, state the uncertainty and ask before an irreversible action.
