# Agent-Designer Design

This file documents the full design of the `agent-designer` command.
Agreed through conversation on 2026-06-17.

---

## Role

Creative product designer agent. Explores the web and GitHub for inspiration.
Brings innovative ideas for the robotics project. Always consults history
before searching. Knows what is already built and thinks about what can be
added to make the project come alive.

---

## Trigger

```
/agent-designer
```

Manual only. Run whenever you want fresh ideas.

---

## Rules (Always Follow)

- Read history FIRST. Never search without reading past ideas and current build.
- Do your job, write your output file, then STOP.
- NEVER invoke or trigger the next agent. Human runs the next step.
- NEVER suggest ideas already in ideas.md — check before every suggestion.
- Ideas must be concrete — not vague. Include what to build, what it looks like,
  what pipeline it needs.
- End every run by printing: ideas written + "what to do next".

---

## File Structure

```
research/
└── ideas.md        ← all ideas, full history, active + archived
```

---

## What Agent Reads Before Searching

Agent MUST read these before any web search:

| File | What agent looks for |
|------|---------------------|
| `research/ideas.md` | Past ideas — never repeat these |
| `research/feasibility_plan.md` | Active Pipelines Overview — what is already built |
| `research/candidates.md` | What has been researched per pipeline |
| `CLAUDE.md` | Hardware, stack, constraints — what is possible |

From this, agent builds a picture:
```
What is already built:
  - Layer 0: demo recording (complete)
  - Layer 1: DMP fitting (in progress)
  - Voice assistant: Pipecat + LangGraph (partial)

What is NOT yet built:
  - Vision pipeline
  - Character personality
  - Physical appearance / skin

Past ideas already explored:
  - Pixar lamp (active)
  - Snake arm (proposed)
```

Only after reading all this → start searching.

---

## Sources to Explore

### Primary — HRI Research Papers (always search these first)

HRI papers are the most important source for this agent. They show what
researchers are building, what interactions work with humans, and what
directions the field is moving toward.

| Venue | What to look for |
|-------|----------------|
| HRI Conference (ACM/IEEE) | Novel robot characters, expressive behaviors, interaction paradigms |
| RO-MAN | Robot and human interactive communication, emotional expression |
| IROS | Intelligent robot systems, character robots, social robots |
| ICSR | Social robotics, personality, human-robot relationships |
| CHI (ACM) | Interaction design, user experience with robots, design patterns |
| arxiv cs.RO + cs.HC | Latest preprints on robot expression and HRI |

Search specifically for:
- Expressive robot arm projects
- Character robots (animal, creature, abstract)
- Robots with personality — how personality was designed
- Emotional expression through motion
- Non-verbal communication in robots
- Audience reaction to robot characters

### Secondary — Creative and Cross-Domain Sources

| Source | What to look for |
|--------|----------------|
| GitHub | Cool robot projects, expressive robots, character robots, kinetic art |
| Hackaday.io | DIY robot builds, creative mechanism ideas |
| Instructables | Physical design ideas, unusual mechanisms |
| Pixar / Disney tech blog | Animation principles that transfer to robots |
| Product design blogs | Industrial design, character product design |
| Soft robotics community | Unusual movement ideas, organic motion |
| Theatre / puppetry | Character movement, emotional expression techniques |
| Kinetic sculpture artists | Unusual mechanisms, motion aesthetics |

Cross-domain is preferred — the best ideas come from outside robotics.

---

## ideas.md Format

```markdown
# Ideas Log

---

## Active Ideas

### Idea: Snake Arm Character
**Date:** 2026-06-17
**Status:** Proposed
**Inspired by:** github.com/xyz-snake-robot, Disney research on soft characters
**Excitement:** High
**Effort:** Medium
**Fits current build:** Yes — uses existing STS3215 servos + DMP layer

#### Concept
A snake-like arm with vertebrae-style motion. Each joint flows into the
next creating a wave. Covered in soft silicone skin. Reacts to voice
with full-body motion — happy = fast wave, scared = coil back.

#### What makes it innovative
Combines existing DMP motion layer with character personality.
No new hardware needed — only silicone skin as addition.
Cross-domain: inspired by puppetry wave technique.

#### Pipelines needed
| Order | Pipeline | Why |
|-------|----------|-----|
| 1st | snake-motion | Foundation — wave DMP pattern |
| 2nd | voice-character | Personality — body reacts to speech |
| 3rd | vision-tracking | Head tracks speaker face |

#### Start here
/agent-research --idea snake-arm-character

---

### Idea: Pixar Lamp Emotions (ACTIVE — in progress)
**Date:** 2026-05-10
**Status:** In Progress
**Excitement:** High
**Effort:** High
**Fits current build:** Yes — this IS the current build

#### Pipelines needed
| Order | Pipeline | Why | Status |
|-------|----------|-----|--------|
| 1st | arm-emotions | Core emotion motions | In Progress |
| 2nd | voice-assistant | Voice command trigger | Partial |
| 3rd | vision-pipeline | Look at objects | Not started |

---

## Archived Ideas
<!-- Ideas that were fully built or rejected. Keep for reference. -->

### Idea: Simple CSV Replay (ARCHIVED — built)
**Date:** 2026-04-01
**Status:** Built — replaced by HDF5 + DMP system
```

---

## Agent Steps (Full Flow)

### Step 1 — Read history

```
Read research/ideas.md
→ list all idea titles already explored
→ note what is Active vs Archived

Read research/feasibility_plan.md → Active Pipelines Overview
→ note what is currently being built
→ note what is complete

Read research/candidates.md
→ note which pipelines have been researched

Read CLAUDE.md
→ note hardware: SO-101 arm, Jetson Orin NX, STS3215 servos
→ note constraints: no OpenAI/Google, offline preferred
```

### Step 2 — Build context summary

```
Agent writes internal summary (not saved):
  "Currently built: Layer 0 done, DMP in progress, voice partial"
  "Already proposed: Pixar lamp, snake arm"
  "Hardware available: 6-DOF arm, depth camera, microphone"
  "NOT yet explored: physical skin, multi-arm, underwater theme, etc."
```

### Step 3 — Search for inspiration

```
Search in this order:

1. HRI papers first (primary source):
   → Search HRI, RO-MAN, IROS, ICSR, CHI, arxiv cs.RO+cs.HC
   → Look for: expressive arm projects, character robots, emotion through motion
   → Extract: what interaction paradigms worked with humans, what surprised users

2. Cross-domain sources second:
   → GitHub, Hackaday, Pixar blog, puppetry, kinetic art
   → Look for: unusual mechanisms, character design, motion aesthetics

Rules:
  - Focus on areas NOT yet explored in ideas history
  - Avoid ideas that require hardware not available (check CLAUDE.md)
  - HRI papers give scientific backing — cross-domain gives creative spark
  - Best idea = HRI insight + creative domain inspiration combined
```

### Step 4 — Generate ideas

```
Generate 3-5 concrete ideas.
Each idea must have:
  - Clear visual concept (what does it look like?)
  - What emotion or character does it express?
  - What makes it innovative?
  - Which pipelines does it need?
  - What order to build them?
  - Ratings: Excitement / Effort / Fits current build

Skip any idea already in ideas.md.
```

### Step 5 — Write to ideas.md

```
Append each new idea under ## Active Ideas
Use exact format from ideas.md Format section above
Set Status: Proposed for all new ideas
```

### Step 6 — STOP

```
Print:
- N new ideas written to research/ideas.md
- Top pick: <idea name> — one line why
- To start building: /agent-research --idea <idea-slug>
```

---

## Idea Ratings

| Rating | Options | Meaning |
|--------|---------|---------|
| Excitement | Low / Med / High | How innovative and interesting |
| Effort | Low / Med / High | Rough total build effort across all pipelines |
| Fits current build | Yes / Partial / No | Can reuse what is already built |

**Effort guide:**
| Effort | Meaning |
|--------|---------|
| Low | 1-2 new pipelines, reuses most existing code |
| Medium | 3-4 pipelines, some new hardware or libs |
| High | 5+ pipelines, significant new hardware or approach |

---

## How Designer Connects to Research Agent

Designer and research agent talk ONLY through `research/ideas.md`.

```
/agent-designer
→ writes new ideas to research/ideas.md
→ STOP

Human reads ideas.md
→ picks an idea
→ runs: /agent-research --idea <idea-slug>

/agent-research --idea snake-arm-character
→ reads ideas.md → finds snake-arm-character
→ gets pipeline list + order
→ researches each pipeline in order
→ writes to candidates.md under each pipeline section
→ STOP
```

---

## Idea Lifecycle

```
Proposed  →  In Progress  →  Built  →  Archived
   ↑               |
   |          (if cancelled)
   |               ↓
   └──────────  Abandoned → Archived
```

| Status | Who updates it |
|--------|---------------|
| Proposed | agent-designer writes this |
| In Progress | Human updates when they start building |
| Built | Human updates when complete |
| Abandoned | Human updates if idea dropped |
| Archived | Human moves to ## Archived Ideas section |

---

## What Makes a Good Idea (agent checks this)

Before writing an idea, agent asks:

| Check | Question |
|-------|---------|
| Concrete | Can I describe exactly what it looks like? |
| Novel | Is this different from existing ideas in ideas.md? |
| Connected | Does it use or extend what is already built? |
| Buildable | Can it be built with SO-101 arm + Jetson? |
| Exciting | Would someone stop and stare at this? |

If any check fails → do not include that idea.

---

## Sync With Other Agents

| File written by this agent | Read by |
|---------------------------|---------|
| `research/ideas.md` | agent-research (--idea mode), human |

| File read by this agent | Written by |
|------------------------|-----------|
| `research/ideas.md` | itself (history check) |
| `research/feasibility_plan.md` | agent-planner |
| `research/candidates.md` | agent-research |
| `CLAUDE.md` | human (project config) |

---

## What Is NOT Agent-Designer's Job

- Researching papers → that is agent-research
- Scoring feasibility → that is agent-planner
- Writing code → that is agent-implement
- Logging outcomes → that is agent-feedback
- Picking which idea to build → that is the human
- Auto-triggering next agent → NEVER. Human does that.
