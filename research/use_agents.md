# How to Use the Research Pipeline

This pipeline helps you research, plan, build, and improve robotics features
in a structured way. You control every step — no agent ever auto-runs another.

---

## The 5 Agents

| Agent | Command | Job |
|-------|---------|-----|
| Designer | `/agent-designer` | Find innovative ideas from HRI papers + creative sources |
| Research | `/agent-research <topic>` | Explore papers — shows summaries, you pick which to keep |
| Research | `/agent-research <topic> --save` | Save your selected papers to all index files |
| Planner | `/agent-planner <number>` | Check feasibility + write step-by-step plan |
| Implement | `/agent-implement <pipeline>` | Write code for ONE step at a time |
| Feedback | `/agent-feedback <pipeline> "<outcome>"` | Log what happened after testing |

**Golden rule:** Each agent writes its file and STOPS. You run the next one.

**Research is always two steps:** Explore first → you pick papers → then Save.

---

## Two Ways to Start

### Path A — You want ideas first

```
1. /agent-designer
   → reads HRI papers + GitHub for inspiration
   → writes new ideas to research/ideas.md
   → STOP

2. Read research/ideas.md → pick an idea

3. /agent-research --idea <idea-slug>
   → searches papers for each pipeline in order
   → writes research/preview_<pipeline>.md (one file per pipeline)
   → STOP

4. For each pipeline:
   - Open research/preview_<pipeline>.md
   - Delete papers you do NOT want
   - Run: /agent-research <pipeline> --save

5. Continue with the main flow below (start from Step 3)
```

### Path B — You have a specific topic

```
1. /agent-research <topic>
   → finds papers, repos, tutorials
   → writes research/preview_<topic>.md with summaries
   → STOP

2. Open research/preview_<topic>.md
   → delete papers you do NOT want
   → keep only what you want saved

3. /agent-research <topic> --save
   → saves your selected papers to all index files
   → writes research/candidates.md with paper facts
   → STOP

4. Continue with the main flow below (start from Step 2)
```

---

## Main Flow (step by step)

### Step 1a — Research (Explore)
```
/agent-research voice-assistant
```
- Reads past research from log.md (no repeats)
- Reads past failures from candidates.md (uses as extra search context)
- Searches: arxiv, paperswithcode, IEEE, GitHub, blogs
- Writes: `research/preview_voice-assistant.md` — numbered list with 5-6 line summary per paper

**You do:**
- Open `research/preview_voice-assistant.md`
- Delete "## Paper N" blocks you do NOT want
- Keep only the papers relevant to your goal

### Step 1b — Research (Save)
```
/agent-research voice-assistant --save
```
- Reads preview file — saves whatever you kept
- Writes:
  - `research/papers/<slug>.md` — one file per saved paper
  - `research/topics/voice-assistant.md` — comparison table (tools, ROS2, offline, compute)
  - `research/candidates.md` — objective paper facts (no recommendations)
  - `research/log.md` — index row per resource
  - `research/bibliography.md` — human-readable row per resource

**You do:** Read `research/candidates.md` → read paper facts → pick a number.

---

### Step 2 — Plan
```
/agent-planner 2
/agent-planner 2,4        ← amalgamation of two papers
```
- Reads chosen paper(s) from candidates.md + papers/<slug>.md
- Reads CLAUDE.md for your hardware and stack constraints
- Checks cross-pipeline dependencies
- Scores: GO / MODIFY / SKIP

  - **GO** → writes plan immediately
  - **MODIFY** → explains workaround → waits for your confirmation → then plan
  - **SKIP** → explains why → suggests what to research instead

- Writes:
  - `research/feasibility_plan.md` — scorecard + plan with checkboxes
  - `research/candidates.md` — fills Chosen + Why chosen fields

**You do:** Read `research/feasibility_plan.md` → review the plan → confirm it makes sense.

---

### Step 3 — Implement (run once per step)
```
/agent-implement voice-assistant
```
- Reads feasibility_plan.md → finds first unchecked `[ ]` step
- Creates git branch on first run: `research-voice-assistant-v1`
- Writes code for that ONE step only
- Runs `colcon build` → reports result
- Handles problems:
  - Minor → fixes itself
  - Medium → tries 3 approaches
  - Major → writes issue report → tells you to replan → STOPS
- Marks step `[x]` when done
- Updates candidates.md: Implemented field

**You do:** Test the step works. Then run `/agent-implement voice-assistant` again for next step.
Repeat until all steps are done.

---

### Step 4 — After all steps done

When all steps are `[x]`, agent-implement automatically:
- Reviews the code for performance, memory, ROS2 best practices
- Writes `research/improvements/voice-assistant.md`
  - Quick fixes (agent can apply)
  - Redesign items (you decide)

**You do:** Test the complete pipeline end-to-end.

---

### Step 5 — Log outcome
```
/agent-feedback voice-assistant "success — working on Jetson"
/agent-feedback voice-assistant "failed — Qwen drops tools randomly"
/agent-feedback voice-assistant "partial — steps 1-3 ok, step 4 crashes"
/agent-feedback voice-assistant "blocked — Jetson not available"
```
- Updates candidates.md (Outcome field)
- Updates feasibility_plan.md (Stopped at + Reason + Pipeline status)
- Appends to log.md
- Reads improvements file → prints what to run next

---

## When Things Go Wrong

### Implementation fails at a step

```
1. /agent-feedback voice-assistant "failed — reason"
   → logs failure

2. /agent-planner voice-assistant --replan
   → reads failure reason
   → replans using EXISTING research only
   → writes Plan v2

   If no solution in existing research, it tells you:
   → /agent-research voice-assistant   (finds new targeted papers)
   → /agent-planner voice-assistant --replan   (now has new papers)

3. /agent-implement voice-assistant
   → picks up from Plan v2, Step 1
```

### Apply quick fixes after success

```
/agent-implement voice-assistant --fix-improvements
→ reads research/improvements/voice-assistant.md
→ applies Quick fixes only
→ leaves Redesign items for you to decide
```

### Redesign needed

```
Read research/improvements/voice-assistant.md
→ find the redesign item
→ /agent-planner voice-assistant --replan "<item description>"
→ /agent-implement voice-assistant   (new plan, new branch)
```

---

## All Commands Reference

| Command | What it does |
|---------|-------------|
| `/agent-designer` | Generate ideas from HRI + creative sources |
| `/agent-research <topic>` | Explore papers — writes preview file, no files saved yet |
| `/agent-research <topic> --save` | Save approved papers from preview file |
| `/agent-research --idea <slug>` | Explore papers for all pipelines in a designer idea |
| `/agent-planner <number>` | Plan for single paper |
| `/agent-planner <n>,<m>` | Plan for amalgamation of papers |
| `/agent-planner <pipeline> --replan` | Replan after failure (existing research only) |
| `/agent-implement <pipeline>` | Implement next unchecked step |
| `/agent-implement <pipeline> --fix-improvements` | Apply quick fixes only |
| `/agent-feedback <pipeline> "failed — reason"` | Log failure |
| `/agent-feedback <pipeline> "partial — reason"` | Log partial success |
| `/agent-feedback <pipeline> "success — reason"` | Log success |
| `/agent-feedback <pipeline> "blocked — reason"` | Log blocked |

---

## Files Reference

| File | Who writes it | What it contains |
|------|--------------|-----------------|
| `research/log.md` | agent-research, agent-planner, agent-feedback | Index of all resources. Grepped by agents. |
| `research/bibliography.md` | agent-research | All links + 2-line summary. For you to browse. |
| `research/ideas.md` | agent-designer | All project ideas with ratings and pipeline breakdown. |
| `research/candidates.md` | All agents | Picking history per pipeline. Session-based. |
| `research/feasibility_plan.md` | agent-planner, agent-implement, agent-feedback | All plans, versioned, with checkboxes. |
| `research/papers/<slug>.md` | agent-research | Deep summary of one resource. Written once. |
| `research/topics/<topic>.md` | agent-research | Comparison of all papers on same topic. |
| `research/improvements/<pipeline>.md` | agent-implement | Post-completion code review. Quick fixes + redesign items. |

---

## Parallel Pipelines

You can have multiple pipelines active at the same time.
Always specify the pipeline name in the command:

```
/agent-implement voice-assistant    ← works on voice pipeline
/agent-implement vision-pipeline    ← works on vision pipeline (independent)
```

Each pipeline has its own section in candidates.md and feasibility_plan.md.
agent-planner checks dependencies between pipelines automatically.

---

## Design files (reference only)

The full design decisions behind each agent are documented in:
```
src/z_research/
├── agent_designer_design.md
├── agent_research_design.md
├── agent_planner_design.md
├── agent_implement_design.md
└── agent_feedback_design.md
```

Read these if you want to understand WHY an agent behaves a certain way.
