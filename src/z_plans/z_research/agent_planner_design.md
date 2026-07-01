# Agent-Planner Design

This file documents the full design of the `agent-planner` command.
Agreed through conversation on 2026-06-17.

---

## Role

Planner agent. Takes chosen paper(s) from candidates.md, checks if they
can be implemented with current hardware and software, writes a detailed plan,
and tracks replans over time.

---

## Triggers

```
/agent-planner 2                        ← single paper
/agent-planner 2,4                      ← amalgamation of papers
/agent-planner voice-assistant --replan ← replan using existing research
```

---

## Rules (Always Follow)

- Do your job, write your output files, then STOP.
- NEVER invoke or trigger the next agent. Human runs the next step.
- NEVER overwrite old plan versions. Always append new version below old one.
- If OVERALL verdict is SKIP — explain exactly why, suggest what to research instead.
- If OVERALL is MODIFY — explain workaround clearly, wait for human to confirm before writing plan.
- Replan uses EXISTING research only. If no solution found → tell human to run /agent-research first.
- End every run by printing: files written + one line "what to do next".

---

## File Structure

```
research/
└── feasibility_plan.md     ← all plans, all topics, full history
```

---

## feasibility_plan.md Format

```markdown
# Feasibility Plans

## Active Pipelines Overview

| Pipeline | Status | Depends on | Blocker? |
|----------|--------|-----------|---------|
| Voice Assistant | In Progress | Vision Pipeline | YES — detect_objects not ready |
| Vision Pipeline | In Progress | — | No |
| Arm Emotions | Planned | — | No |

---

## Voice Assistant

### Plan v1 — 2026-06-17 | Papers: LangGraph + Pipecat
**Verdict:** GO

#### Feasibility Scorecard
| Check | Result | Note |
|-------|--------|------|
| Hardware fit (SO-101 / Jetson) | OK | Runs on CPU, no GPU needed |
| Offline fit (no OpenAI/Google) | OK | Uses Qwen via aliyuncs.com |
| Existing libs available offline | OK | pipecat, langgraph pip installable |
| Compute fit (Jetson memory) | WARN | Qwen-Max needs ~6GB RAM |
| ROS2 integration | OK | rclpy bridge pattern works |
| Dependency risk | Low | Stable libs, pinned versions |
| OVERALL | GO | |

#### Plan Steps
- [x] Step 1: Setup LangGraph env + Qwen client (est. 1h)
- [x] Step 2: Connect Pipecat audio loop (est. 2h)
- [ ] Step 3: Add tool-calling with Qwen (est. 2h) ← FAILED here
- [ ] Step 4: ROS2 bridge + service clients (est. 3h)
- [ ] Step 5: End-to-end voice test (est. 1h)

**Stopped at:** Step 3
**Reason:** Jetson runs out of memory with Qwen-Max

---

### Plan v2 — 2026-06-25 | Replan
**Replan reason:** Jetson OOM at step 3 — Qwen-Max too heavy
**Research used:** Existing — papers/qwen-agent-official.md
**Change from v1:** Switch Qwen-Max to Qwen-Turbo, reduce context window size

#### Plan Steps
- [ ] Step 1: Swap model to Qwen-Turbo in llm_setup.py (est. 30min)
- [ ] Step 2: Reduce context window to 4096 tokens (est. 30min)
- [ ] Step 3: Test memory usage on Jetson (est. 1h)
- [ ] Step 4: Run end-to-end voice test (est. 1h)

**Stopped at:** —
**Reason:** —

---

## Vision Pipeline

### Plan v1 — 2026-06-25 | Papers: SAM2 + Depth-Anything
...
```

---

## Agent Steps (Full Flow)

### Normal run: `/agent-planner 2` or `/agent-planner 2,4`

**Step 1 — Read candidates**
```
Read research/candidates.md
→ find paper(s) matching the given number(s)
→ get paper slug(s)
→ read research/papers/<slug>.md for each
→ read research/topics/<topic>.md for full context
```

**Step 2 — Read current situation**
```
Read CLAUDE.md:
→ Hardware: SO-101 arm, Jetson Orin NX
→ Stack: ROS2 Humble, Python, rclpy
→ Constraint: no OpenAI/Google — Qwen via aliyuncs.com only
→ Available libs: check what is already installed

Read research/feasibility_plan.md:
→ check Active Pipelines Overview
→ understand what is already being built
→ check for dependencies between pipelines
```

**Step 3 — Score against setup**

Run scorecard:

| Check | How agent decides |
|-------|-----------------|
| Hardware fit | Does paper assume different arm/robot? Different DOF? |
| Offline fit | Does it call OpenAI/Google API? If yes → FAIL |
| Libs available | Can all dependencies be pip installed offline? |
| Compute fit | Does it need GPU? How much RAM? Jetson has limited memory |
| ROS2 integration | Does a ROS2 bridge exist or need to be written? |
| Dependency risk | Are libs stable? Last updated? Known issues? |
| OVERALL | GO / MODIFY / SKIP |

**Step 4 — Three outcomes**

| Verdict | Agent does |
|---------|-----------|
| GO | Write detailed step-by-step plan immediately |
| MODIFY | Explain workaround clearly → STOP → wait for human confirm → then write plan |
| SKIP | Explain why not feasible → suggest what to research instead → STOP |

**Step 5 — Write plan (if GO or MODIFY confirmed)**
```
Max 5 steps per plan version
Each step:
  - Small and concrete (one thing only)
  - Estimated time (realistic for one session)
  - Written as checkbox: - [ ] Step N: description (est. Xh)
```

**Step 6 — Update feasibility_plan.md**
```
Update Active Pipelines Overview table
Append new plan version under correct ## Topic section
Never overwrite old versions
```

**Step 7 — Append to log.md**
```
Append to ## Decisions:
| date | topic | papers | verdict | reason |
```

**Step 8 — STOP**
```
Print:
- Files written
- Verdict + one-line reason
- What to do next: "Review feasibility_plan.md then run /agent-implement"
```

---

### Replan run: `/agent-planner voice-assistant --replan`

**Step 1 — Read failure context**
```
Read research/candidates.md → find latest session for voice-assistant
→ read Outcome field (logged by /agent-feedback)
→ extract failure reason
```

**Step 2 — Read existing research only**
```
Read research/topics/voice-assistant.md
Read all research/papers/<slug>.md tagged #voice-assistant
Do NOT search the web
```

**Step 3 — Find solution in existing research**
```
Can the failure reason be solved with what we already have?

If YES:
  → Write Plan v(N+1) addressing the failure
  → Reference which existing paper solves it

If NO:
  → Tell human: "No solution in current research. Run /agent-research voice-assistant first."
  → STOP (do not write a new plan)
```

**Step 4 — Write new plan version**
```
Append Plan v(N+1) under ## Voice Assistant
Include:
  - Replan reason
  - Which existing paper used
  - What changed from previous plan
  - New steps with checkboxes and time estimates
```

**Step 5 — STOP**
```
Print:
- Plan v(N+1) written
- Key change from previous plan
- What to do next
```

---

## Checkbox Ownership

| Who | Does what |
|-----|----------|
| agent-planner | Writes all steps as unchecked: `- [ ]` |
| agent-implement | Marks step done: `- [x]` after completing it |
| Human | Never needs to touch checkboxes |

---

## Pipeline Dependencies

Agent-planner must check cross-pipeline dependencies every run.

Example situations to catch:
- Voice assistant calls `/vlm/detect_objects` → vision pipeline must be ready first
- Arm emotions need `/follower/arm_controller` → hardware bringup must be running

If dependency not ready → write in Active Pipelines Overview as Blocker: YES.
Tell human which pipeline to finish first.

---

## Picking Help (from agent-research)

Agent-research writes a "Recommended picks" section at bottom of candidates.md
to help human pick numbers without reading all papers:

```markdown
## Recommended picks
- Best single paper: #2 — most complete, fewest dependencies
- Best combination: #2 + #4 — if you want audio + tool routing
- Skip: #1 — requires OpenAI, not offline compatible
```

Human reads this → picks number(s) → runs /agent-planner.

---

## Feedback + Replan Full Flow

```
Implementation fails at runtime
        ↓
/agent-feedback voice-assistant "step 3 failed, Jetson OOM"
→ logs Outcome to candidates.md (latest session)
→ logs to log.md Decisions section
→ STOP
        ↓
/agent-planner voice-assistant --replan
→ reads failure from candidates.md
→ searches EXISTING papers only
→ if solution found: writes Plan v2
→ if no solution: tells human to run /agent-research first
→ STOP
        ↓
(only if needed)
/agent-research voice-assistant
→ uses failure reason as extra search context
→ finds new targeted papers
→ STOP
        ↓
/agent-planner voice-assistant --replan
→ now has new papers to work with
→ writes Plan v2
→ STOP
```

---

## What Is NOT Agent-Planner's Job

- Finding new papers → that is agent-research
- Writing code → that is agent-implement
- Marking steps complete → that is agent-implement
- Logging failure outcomes → that is /agent-feedback
- Auto-triggering next agent → NEVER. Human does that.
