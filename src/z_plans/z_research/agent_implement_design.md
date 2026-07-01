# Agent-Implement Design

This file documents the full design of the `agent-implement` command.
Agreed through conversation on 2026-06-17.

---

## Role

Implementation agent. Reads the feasibility plan for a specific pipeline,
does ONE step at a time, handles minor problems itself, raises major problems
to feasibility, and reviews code quality after all steps are done.

---

## Trigger

```
/agent-implement <pipeline>
```

Examples:
```
/agent-implement voice-assistant
/agent-implement vision-pipeline
/agent-implement arm-emotions
```

Each pipeline is independent. You control which one runs.

---

## Rules (Always Follow)

- Do your job, then STOP. ONE step per run.
- NEVER invoke or trigger the next agent. Human runs the next step.
- NEVER modify feasibility_plan.md plan steps — only update checkboxes.
- NEVER implement more than one step per run, even if the step is small.
- If OVERALL verdict in plan is SKIP → refuse, explain why, STOP.
- End every run by printing: files changed + branch name + what step is next.

---

## File Structure

```
research/
├── feasibility_plan.md          ← agent reads plan + updates checkboxes
├── candidates.md                ← agent writes Implemented + branch
└── improvements/
    └── <pipeline>.md            ← agent writes post-completion review
```

---

## Agent Steps (Full Flow)

### Step 1 — Read the plan

```
Read research/feasibility_plan.md
→ find ## <pipeline> section
→ find latest plan version (highest vN)
→ check OVERALL verdict:
    if SKIP → print reason → STOP
    if GO or MODIFY → continue
```

### Step 2 — Find next unchecked step

```
Scan plan steps top to bottom:
- [x] Step 1 ← already done, skip
- [x] Step 2 ← already done, skip
- [ ] Step 3 ← THIS is the step to do now

If ALL steps are [x] → go to Post-completion review flow
```

### Step 3 — Check git branch

```
If this is Step 1 (first step, no branch yet):
  → create branch: git checkout -b research-<pipeline>-v<N>
  → example: research-voice-assistant-v1
  → example after replan: research-voice-assistant-v2

If Step 2 or later:
  → check current branch matches expected branch name
  → if wrong branch → warn human, STOP
  → if correct → continue
```

### Step 4 — Implement the step

```
Write clean Python code:
  - Type hints throughout
  - Clear comments explaining WHY (not what)
  - Reuse existing enums and helpers from utilities.py
  - Follow ROS2 conventions (lifecycle nodes, QoS, namespacing)
  - No hardcoded paths — use PathConfig from utilities.py
  - No OpenAI/Google calls — Qwen via aliyuncs.com only

After writing code:
  → run colcon build --packages-select <pkg>
  → report build result
```

### Step 5 — Handle problems

Three levels of problems:

#### Level 1 — Minor (fix itself)
Examples: wrong import, version mismatch, small config error, typo in topic name.

```
→ fix the issue
→ rebuild
→ document in step note: "Fixed: <what was wrong> → <what was changed>"
→ continue to Step 6
```

#### Level 2 — Medium (try up to 3 approaches)
Examples: unexpected behavior, library works differently than expected.

```
→ Attempt 1: try first approach → document result
→ Attempt 2: try second approach → document result
→ Attempt 3: try third approach → document result

If solved:
  → document which approach worked
  → continue to Step 6

If not solved after 3 attempts:
  → treat as Level 3 (Major)
```

#### Level 3 — Major (raise to feasibility)
Examples: core technique does not work, approach affects multiple steps,
fundamental assumption in plan is wrong.

```
→ STOP implementing
→ write issue report inline in feasibility_plan.md under the failed step:

  **Issue raised:** <date>
  **Problem:** <what failed>
  **Attempts tried:** <list what was tried>
  **Impact:** <which other steps are affected>
  **Recommended action:** Run /agent-planner <pipeline> --replan "<reason>"

→ print: "Major issue found. Read feasibility_plan.md then run
          /agent-planner <pipeline> --replan"
→ STOP
```

**How agent decides Minor vs Major:**
| Minor / Medium | Major |
|----------------|-------|
| Can fix without changing plan steps | Requires changing plan steps or approach |
| Isolated to current step only | Affects other steps |
| Fix takes < 30 min | Fix would take longer than the step itself |

### Step 6 — Update feasibility_plan.md checkbox

```
Mark current step done:
  - [ ] Step 3: Add Qwen tool-calling (est. 2h)
becomes:
  - [x] Step 3: Add Qwen tool-calling (est. 2h)

If fix was needed, add note below the checkbox:
  - [x] Step 3: Add Qwen tool-calling (est. 2h)
    Note: Fixed import path for dashscope → used dashscope.Generation not dashscope.TextGeneration
```

### Step 7 — Update candidates.md

```
Find ## <Pipeline> section → latest session

If this is Step 1 (first step):
  → write: Implemented: In Progress — branch research-voice-assistant-v1

If this is last step (all done):
  → write: Implemented: Yes — branch research-voice-assistant-v1
```

### Step 8 — STOP

```
Print:
- Branch: research-voice-assistant-v1
- Step done: Step 3
- Files changed: list
- Build result: OK / FAILED
- Next: "Run /agent-implement voice-assistant to do Step 4"
      OR "All steps done. Run /agent-feedback voice-assistant to log outcome."
```

---

## Post-Completion Review Flow

Triggered when agent finds ALL steps are `[x]` in the latest plan.

### Step 1 — Review the code

```
Read all files changed in this branch:
  git diff master..HEAD --name-only

For each file, check:
  - Performance: any slow loops, repeated API calls, blocking calls?
  - Memory: any large objects kept in memory? Important for Jetson.
  - ROS2 best practices: lifecycle nodes, QoS profiles, proper shutdown?
  - Readability: clear variable names, logical structure?
  - Offline safety: any accidental OpenAI/Google calls?
```

### Step 2 — Write improvements file

Write to `research/improvements/<pipeline>.md`:

```markdown
# Improvements — Voice Assistant
Reviewed: 2026-06-30 | Branch: research-voice-assistant-v1

## Issues found

| # | Issue | Location | Type | Effort | Suggestion |
|---|-------|----------|------|--------|-----------|
| 1 | Qwen called on every message, no cache | llm_setup.py:42 | Performance | Low | Cache last 3 responses |
| 2 | Node not using lifecycle | agent_node.py:10 | ROS2 best practice | Medium | Migrate to LifecycleNode |
| 3 | Audio buffer grows unbounded | ros_bridge.py:88 | Memory | High | Add max buffer size + flush |

## Categories

### Quick fixes (agent can do in next run)
- #1 — add response cache

### Needs redesign (human decides)
- #2 — lifecycle node migration (new feasibility plan needed)
- #3 — buffer management (affects ros_bridge architecture)
```

### Step 3 — STOP

```
Print:
- "All steps complete. Improvements written to research/improvements/<pipeline>.md"
- "Quick fixes: N found. Run /agent-implement <pipeline> --fix-improvements to apply."
- "Redesign items: N found. Review and decide if new feasibility plan needed."
- "Next: Run /agent-feedback <pipeline> to log final outcome."
```

---

## Branch Strategy

| Situation | Branch name |
|-----------|------------|
| Plan v1, first step | `research-<pipeline>-v1` |
| Plan v2 (after replan), first step | `research-<pipeline>-v2` |
| Continuing same plan | Same branch, no new branch |

New branch only when a new plan version starts. Never on same plan.

---

## Checkbox Ownership

| Who | Does what |
|-----|----------|
| agent-planner | Writes all steps as `- [ ]` |
| agent-implement | Marks step done `- [x]`, adds notes if fix needed |
| Human | Never touches checkboxes |

---

## candidates.md Updates by This Agent

| When | What agent writes |
|------|-----------------|
| Step 1 complete | `Implemented: In Progress — branch research-voice-assistant-v1` |
| All steps complete | `Implemented: Yes — branch research-voice-assistant-v1` |
| Major issue raised | `Implemented: Blocked — see feasibility_plan.md issue report` |

---

## Apply Quick Fixes (optional trigger)

```
/agent-implement <pipeline> --fix-improvements
```

Agent reads `research/improvements/<pipeline>.md`:
→ applies only "Quick fixes" items
→ does NOT touch "Needs redesign" items
→ rebuilds
→ updates improvements file: marks fixed items as done
→ STOP

---

## Sync With Other Agents

| File read by this agent | Written by |
|------------------------|-----------|
| `research/feasibility_plan.md` | agent-planner |
| `research/candidates.md` (partial) | agent-research, agent-planner |

| File written by this agent | Read by |
|---------------------------|---------|
| `research/feasibility_plan.md` (checkboxes + issue notes) | agent-planner (on replan) |
| `research/candidates.md` (Implemented field) | /agent-feedback |
| `research/improvements/<pipeline>.md` | Human, agent-implement (--fix-improvements) |

See `agent_research_design.md` and `agent_planner_design.md` for full context.

---

## What Is NOT Agent-Implement's Job

- Finding papers → that is agent-research
- Scoring feasibility → that is agent-planner
- Logging failure outcomes → that is /agent-feedback
- Replanning → that is agent-planner
- Doing more than one step per run → NEVER
- Auto-triggering next agent → NEVER. Human does that.
