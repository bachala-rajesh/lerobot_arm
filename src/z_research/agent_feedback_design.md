# Agent-Feedback Design

This file documents the full design of the `agent-feedback` command.
Agreed through conversation on 2026-06-17.

---

## Role

Feedback agent. Records what happened after testing — success, failure,
partial, or blocked. Updates both tracking files automatically. Acts as
bridge between testing results and next pipeline action.

---

## Trigger

```
/agent-feedback <pipeline> "<outcome>"
```

Examples:
```
/agent-feedback voice-assistant "failed — Qwen drops tools randomly"
/agent-feedback voice-assistant "partial — steps 1-3 ok, step 4 crashes on Jetson"
/agent-feedback voice-assistant "success — working on Jetson"
/agent-feedback voice-assistant "blocked — Jetson not available this week"
```

---

## Rules (Always Follow)

- Do your job, update files, then STOP.
- NEVER invoke or trigger the next agent. Human runs the next step.
- NEVER overwrite old outcome entries. Always append or update only the latest session.
- Update BOTH candidates.md AND feasibility_plan.md in one run.
- On success — always read improvements file and print reminder before stopping.
- End every run by printing: files updated + what to do next.

---

## Outcome Types

| Outcome | Meaning | Example |
|---------|---------|---------|
| failed | Nothing works | "failed — Qwen drops tools randomly" |
| partial | Some steps work, some do not | "partial — steps 1-3 ok, step 4 crashes on Jetson" |
| success | Everything works as planned | "success — working on Jetson" |
| blocked | Cannot test right now | "blocked — Jetson not available this week" |

---

## Files Updated

| File | What gets written |
|------|-----------------|
| `research/candidates.md` | Outcome field in latest session |
| `research/feasibility_plan.md` | Stopped at + Reason in latest plan version |
| `research/log.md` | One-line decision entry appended to ## Decisions |

---

## Agent Steps (Full Flow)

### Step 1 — Parse input

```
Extract from $ARGUMENTS:
→ pipeline name: voice-assistant
→ outcome type: failed / partial / success / blocked
→ reason: the text after the dash
```

### Step 2 — Update candidates.md

```
Read research/candidates.md
→ find ## <Pipeline> section
→ find latest ### Session block
→ write Outcome field:

  **Outcome:** Failed — Qwen drops tools randomly

If Outcome field already exists → append new line below:
  **Outcome:** Failed — Qwen drops tools randomly
  **Outcome update (2026-07-01):** Partial — fixed tools but step 4 still crashes
```

### Step 3 — Update feasibility_plan.md

```
Read research/feasibility_plan.md
→ find ## <Pipeline> section
→ find latest Plan vN block
→ find "Stopped at" and "Reason" fields:

For failed / partial / blocked:
  **Stopped at:** Step 4
  **Reason:** <outcome reason from input>

For success:
  **Stopped at:** All steps complete
  **Reason:** Working on Jetson

Also update Active Pipelines Overview table:
  failed   → Status: Blocked
  partial  → Status: Partially Working
  success  → Status: Complete
  blocked  → Status: On Hold
```

### Step 4 — Append to log.md

```
Append to ## Decisions section:

| 2026-06-30 | voice-assistant | LangGraph + Pipecat | Failed | Qwen drops tools randomly |
```

### Step 5 — Check improvements file (ALL outcomes)

```
Check if research/improvements/<pipeline>.md exists

If NOT exists:
→ skip this step

If EXISTS:
→ read the file
→ count Quick fix items
→ count Redesign items
→ prepare reminder for Step 6
```

### Step 6 — Print and STOP

**If outcome = failed / partial / blocked:**
```
Print:
- "Outcome logged: <outcome>"
- "Files updated: candidates.md, feasibility_plan.md, log.md"
- Next steps:
  → "Run /agent-planner <pipeline> --replan '<reason>' to create new plan"
  → if improvements exist: also print improvements reminder (see below)
```

**If outcome = success:**
```
Print:
- "Success logged for <pipeline>."
- "Files updated: candidates.md, feasibility_plan.md, log.md"
- Improvements reminder (always shown on success):

  If quick fixes exist:
  "Quick fixes pending (N items) — agent can apply these:
   Run /agent-implement <pipeline> --fix-improvements"

  If redesign items exist:
  "Redesign items pending (N items) — needs new feasibility plan:
   Run /agent-planner <pipeline> --replan '<item description>'"

  If no improvements file:
  "No improvements file found. Pipeline complete."
```

---

## candidates.md After This Agent Runs

```markdown
### Session: 2026-06-17
**Context:** First run on voice-assistant
**Papers considered:** LangGraph (#1), Pipecat (#2), Whisper (#3), Qwen-Audio (#4)

## Recommended picks
- Best single: #3
- Best combination: #1 + #2
- Skip: #4

**Chosen:** LangGraph + Pipecat (amalgamation)        ← written by agent-planner
**Why chosen:** LangGraph for routing. Pipecat for audio.

**Implemented:** In Progress — branch research-voice-assistant-v1  ← agent-implement
**Outcome:** Failed — Qwen drops tools randomly        ← THIS AGENT writes this
```

---

## feasibility_plan.md After This Agent Runs

```markdown
### Plan v1 — 2026-06-17 | Papers: LangGraph + Pipecat
**Verdict:** GO

#### Plan Steps
- [x] Step 1: Setup LangGraph env (est. 1h)
- [x] Step 2: Connect Pipecat audio loop (est. 2h)
- [ ] Step 3: Add Qwen tool-calling (est. 2h)
- [ ] Step 4: ROS2 bridge (est. 3h)
- [ ] Step 5: End-to-end test (est. 1h)

**Stopped at:** Step 3                    ← THIS AGENT writes this
**Reason:** Qwen drops tools randomly     ← THIS AGENT writes this
```

---

## Active Pipelines Overview Updates

| Outcome logged | Status written |
|---------------|---------------|
| failed | Blocked |
| partial | Partially Working |
| success | Complete |
| blocked | On Hold |

---

## Bridge Role — Improvements File

Agent-feedback is the only agent that reads `research/improvements/<pipeline>.md`
and tells human what to do with it.

```
improvements/voice-assistant.md
        ↓
agent-feedback reads on success
        ↓
Quick fixes → /agent-implement voice-assistant --fix-improvements
Redesign    → /agent-planner voice-assistant --replan "reason"
        ↓
Human decides which to run
```

---

## Full Feedback Loop (All Agents Together)

```
/agent-research voice-assistant
→ finds papers, writes candidates.md (partial), log.md, bibliography.md
→ STOP

Human picks number(s)

/agent-planner 1,2
→ scores feasibility, writes plan in feasibility_plan.md
→ fills Chosen + Why chosen in candidates.md
→ STOP

/agent-implement voice-assistant  (run once per step)
→ does Step 1, marks [x], writes branch to candidates.md
→ STOP

(repeat /agent-implement per step)

All steps done → agent-implement writes improvements/voice-assistant.md

Human tests code

/agent-feedback voice-assistant "failed — reason"
→ writes Outcome to candidates.md
→ writes Stopped at + Reason to feasibility_plan.md
→ reads improvements file, prints reminder
→ STOP

/agent-planner voice-assistant --replan "reason"
→ reads failure, replans using existing research
→ writes Plan v2
→ STOP

/agent-implement voice-assistant  (runs on Plan v2 steps)
→ STOP

Human tests again

/agent-feedback voice-assistant "success — working on Jetson"
→ logs success
→ prints quick fix + redesign reminders
→ STOP
```

---

## Sync With Other Agents

| File read by this agent | Written by |
|------------------------|-----------|
| `research/candidates.md` | agent-research, agent-planner, agent-implement |
| `research/feasibility_plan.md` | agent-planner, agent-implement |
| `research/improvements/<pipeline>.md` | agent-implement |

| File written by this agent | Read by |
|---------------------------|---------|
| `research/candidates.md` (Outcome field) | agent-research (next run) |
| `research/feasibility_plan.md` (Stopped at, Reason, Overview status) | agent-planner (on replan) |
| `research/log.md` (Decisions section) | agent-research (next run) |

See `agent_research_design.md`, `agent_planner_design.md`,
and `agent_implement_design.md` for full context.

---

## What Is NOT Agent-Feedback's Job

- Finding papers → that is agent-research
- Scoring feasibility → that is agent-planner
- Writing or fixing code → that is agent-implement
- Replanning → that is agent-planner
- Auto-applying improvements → that is agent-implement --fix-improvements
- Auto-triggering next agent → NEVER. Human does that.
