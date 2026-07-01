# Agent-Research Design

This file documents the full design of the `agent-research` command.
Last updated: 2026-06-18

---

## Role

Research agent. Works in three modes.

| Mode | Triggered by | Purpose |
|------|-------------|---------|
| Explore | `/agent-research <topic>` | Find papers, show summaries — human picks which to keep |
| Save | `/agent-research <topic> --save` | Save human-approved papers to all index files |
| Idea | `/agent-research --idea <slug>` | Explore all pipelines for a designer idea |

**Key rule:** Explore first, save after. Human always chooses which papers to keep.

---

## Two-Phase Flow (Explore → Save)

### Why two phases?
The agent searches and finds multiple papers. Some may be irrelevant for the current goal.
Human reviews the 5-6 line summaries and deletes papers they don't want.
Only approved papers are written to permanent files.

### Phase 1 — Explore
```
/agent-research voice-assistant
```
- Searches web (arxiv, paperswithcode, IEEE, GitHub, blogs)
- Writes ALL papers found to `research/preview_voice-assistant.md`
- Each paper: 5-6 line summary covering tools, robot assumed, ROS2, offline, compute
- STOPS — does not write to papers/, log.md, candidates.md

Human action:
- Opens `research/preview_voice-assistant.md`
- Deletes "## Paper N" blocks they do NOT want
- Keeps only the papers they want saved

### Phase 2 — Save
```
/agent-research voice-assistant --save
```
- Reads `research/preview_voice-assistant.md`
- Whatever "## Paper N" blocks remain = approved by human
- Writes full paper files, updates all indices
- STOPS

---

## Triggers

### Explore Mode
```
/agent-research <topic>
```
Topic can be anything. Not limited to active pipelines.

### Save Mode
```
/agent-research <topic> --save
```
Always run after editing the preview file.

### Idea Mode
```
/agent-research --idea <idea-slug>
```
Runs Explore mode for each pipeline in the idea. Writes one preview file per pipeline.
Human then runs `--save` for each pipeline individually.

---

## Rules (Always Follow)

- Do your job, write your output files, then STOP.
- NEVER invoke or trigger the next agent. Human runs the next step.
- NEVER write to permanent files (papers/, log.md, candidates.md) during Explore mode.
- NEVER repeat a resource already in log.md for the same topic.
- NEVER make recommendations — write facts only. Planner decides what to use.

---

## File Structure

```
research/
├── preview_<topic>.md      ← Explore writes here. Human edits. Save reads from here.
├── context.md              ← Robot/software facts. All agents read from here.
├── log.md                  ← Save writes here (grep by tags)
├── bibliography.md         ← Human-readable link list. Save writes here.
├── candidates.md           ← Picking history. Save writes paper facts here.
├── papers/                 ← Full summary per resource. Save writes here.
│   └── <slug>.md
└── topics/                 ← Comparison table per topic. Save writes here.
    └── <topic>.md
```

---

## preview_<topic>.md Format

Written by Explore. Read by human (for selection). Read by Save (for saving).

```markdown
# Research Preview — <topic>
Date: <today>

Instructions:
Delete the "## Paper N" blocks you do NOT want to save.
Keep only the papers you want.
Then run: /agent-research <topic> --save

---

## Paper 1: <Full Title>
**Type:** paper / repo / webpage / tutorial
**Link:** <url>
**Tags:** #<topic> #<keyword1>
**Also useful for:** <other topic or "—">

What it proposes: <1-2 lines>
Tools/libs used: <libraries, frameworks>
Robot assumed: <what robot the paper uses>
ROS2 compatible: Yes / No / Partial
Offline capable: Yes / No — <note cloud dependency if any>
Compute needed: <GPU? RAM? Jetson-compatible?>

---

## Paper 2: ...
```

---

## candidates.md Format (Save mode writes this)

No recommendations. Only objective facts per paper.
Planner reads these facts and runs its own scorecard.

```markdown
### Session: <today>
**Context:** <"First run on this topic" OR "Previous failed — <reason>">
**Papers saved:** N

#### #1 — <Title>
**Type:** paper / repo / webpage
**Link:** <url>
**Tools/libs:** <list>
**Robot assumed:** <what robot the paper used>
**ROS2 compatible:** Yes / No / Partial — <note>
**Offline capable:** Yes / No — <flag OpenAI/Google dependency>
**Compute needed:** <GPU? RAM? Jetson-compatible?>
**Transfers to SO-101:** <what directly applies>
**Gaps:** <what paper doesn't cover for this hardware>

#### #2 — ...
```

### Field ownership table

| Field | Written by |
|-------|-----------|
| Context | agent-research (Save) |
| Papers saved + per-paper facts | agent-research (Save) |
| Chosen + Why chosen | agent-planner |
| Implemented + branch | agent-implement |
| Outcome | agent-feedback |

---

## papers/<slug>.md Format

Full details. Written once, reused by planner + future research runs.

```markdown
---
title: <title>
type: paper / repo / webpage / tutorial
tags: [<topic>, <keyword>]
date: <today>
link: <url>
also_useful_for: [<other-topic>]
---

# <Title>

## Key idea
3-5 lines.

## Tools and libraries
Key libs, frameworks, APIs.

## Hardware and compute assumed
GPU needed? RAM? Edge-compatible on Jetson Orin NX?

## Robot assumed
What robot the paper used. How different from SO-101?

## ROS2 integration
Native? Bridge available? Needs custom wrapper?

## Offline capability
Cloud-free? Any OpenAI/Google dependency?

## What transfers to SO-101 arm + Jetson
Which parts are directly usable.

## Limitations
What it doesn't cover for this setup.
```

---

## topics/<topic>.md Format

Comparison across all saved papers on same topic.
Updated every time Save mode runs.

```markdown
# <Topic> Research

Last updated: <today>

## Papers compared

| Paper | Key idea | Tools used | ROS2 | Offline | Compute | Weakness |
|-------|----------|-----------|------|---------|---------|----------|

## Open questions
What is still not solved for this setup.
```

---

## log.md Format

Flat table. Agent greps by `#tag` — does NOT read full file.

```markdown
# Research Log

## Papers seen

| Date | Title | Type | Tags | Link | Paper file | Also useful for |
|------|-------|------|------|------|------------|----------------|

## Decisions
| Date | Topic | Resource | Verdict | Reason |
|------|-------|----------|---------|--------|
```

---

## bibliography.md Format

All resources in one table. Human reference only. Agent appends, never edits.

```markdown
# Bibliography

| # | Date | Title | Type | Tags | Summary | Link |
|---|------|-------|------|------|---------|------|
```

---

## Feedback Loop

When implementation fails:
```
1. /agent-feedback voice-assistant "Qwen tool-calling drops tools"
   → candidates.md Outcome field updated

2. /agent-research voice-assistant
   → reads Outcome: Failed — reason
   → adds failure reason to search query
   → finds resources that solve that specific problem
   → writes preview_voice-assistant.md

3. You review + /agent-research voice-assistant --save
4. /agent-planner <number> --replan
```

---

## What Is NOT Agent-Research's Job

- Making recommendations → that is the human + agent-planner
- Scoring feasibility → that is agent-planner
- Writing code → that is agent-implement
- Updating Outcome after testing → that is agent-feedback
- Filling Chosen / Why chosen in candidates.md → that is agent-planner
- Filling Implemented / branch → that is agent-implement
- Auto-triggering next agent → NEVER. Human does that.

---

## Sync With Other Agents

| File written by this agent | Read by |
|---------------------------|---------|
| `research/preview_<topic>.md` | Human (selection), then agent-research --save |
| `research/log.md` | agent-research (next run), agent-planner |
| `research/bibliography.md` | Human only |
| `research/candidates.md` (partial) | agent-planner, agent-feedback |
| `research/papers/<slug>.md` | agent-planner, agent-research (next run) |
| `research/topics/<topic>.md` | agent-planner, agent-research (next run) |
