---
name: planning-with-files
model: reasoning
version: 3.0.1
description: >
  File-based planning for complex tasks. Use persistent markdown files as working memory
  to survive context resets. Creates task_plan.md, findings.md, and progress.md. Use for
  any task requiring >5 tool calls, research projects, or multi-step implementations.
tags: [planning, context, workflow, manus, memory, complex-tasks]
slug: planning-with-files
displayName: 文件化规划·复杂任务规划
license: MIT
---

# Planning with Files

Use persistent markdown files as your "working memory on disk." Based on context engineering principles from Manus.

## Installation

### OpenClaw / Moltbot / Clawbot

```bash
npx clawhub@latest install planning-with-files
```

## WHAT This Skill Does

Treats the filesystem as persistent memory to overcome context window limitations. Three files track your state:

| File | Purpose | Update Frequency |
|------|---------|-----------------|
| `task_plan.md` | Phases, progress, decisions | After each phase |
| `findings.md` | Research, discoveries, decisions | After ANY discovery |
| `progress.md` | Session log, test results, errors | Throughout session |

## WHEN to Use

**Use for:**
- Multi-step tasks (3+ steps)
- Research tasks requiring web search
- Building/creating projects from scratch
- Tasks spanning >5 tool calls
- Anything requiring organization across multiple files
- Tasks where losing context would cause rework

**Skip for:**
- Simple questions
- Single-file edits
- Quick lookups
- Tasks completable in 1-2 actions

**Keywords:** complex task, multi-step, research, build project, create application, plan, organize

## The Core Pattern

```
Context Window = RAM (volatile, limited)
Filesystem = Disk (persistent, unlimited)

→ Anything important gets written to disk.
```

## Workflow

### Phase 1: Create Planning Files

Before starting ANY complex task, create all three files in your project root:

1. **Create `task_plan.md`** — Copy from [templates/task_plan.md](templates/task_plan.md)
2. **Create `findings.md`** — Copy from [templates/findings.md](templates/findings.md)
3. **Create `progress.md`** — Copy from [templates/progress.md](templates/progress.md)

### Phase 2: Execute with Discipline

Follow these rules during execution:

**The 2-Action Rule:**
> After every 2 view/browser/search operations, IMMEDIATELY save findings to text files.

Visual/multimodal content doesn't persist — write it down before it's lost.

**Read Before Decide:**
Before major decisions, read your plan file. This keeps goals in your attention window after many tool calls.

**Update After Act:**
After completing any phase:
- Mark phase status: `in_progress` → `complete`
- Log any errors encountered
- Note files created/modified

**Log ALL Errors:**
Every error goes in the plan file. This prevents repetition.

### Phase 3: Handle Errors Systematically

**The 3-Strike Protocol:**

```
ATTEMPT 1: Diagnose & Fix
  → Read error carefully
  → Identify root cause
  → Apply targeted fix

ATTEMPT 2: Alternative Approach
  → Same error? Try different method
  → Different tool? Different library?
  → NEVER repeat exact same failing action

ATTEMPT 3: Broader Rethink
  → Question assumptions
  → Search for solutions
  → Consider updating the plan

AFTER 3 FAILURES: Escalate to User
  → Explain what you tried
  → Share the specific error
  → Ask for guidance
```

**Critical:** `if action_failed: next_action != same_action`

### Phase 4: Verify Completion

Use the 5-Question Reboot Test. If you can answer these, your context is solid:

| Question | Answer Source |
|----------|---------------|
| Where am I? | Current phase in task_plan.md |
| Where am I going? | Remaining phases |
| What's the goal? | Goal statement in plan |
| What have I learned? | findings.md |
| What have I done? | progress.md |

## Quick Reference: Read vs Write

| Situation | Action | Reason |
|-----------|--------|--------|
| Just wrote a file | DON'T read | Content still in context |
| Viewed image/PDF | Write findings NOW | Multimodal → text before lost |
| Browser returned data | Write to file | Screenshots don't persist |
| Starting new phase | Read plan/findings | Re-orient if context stale |
| Error occurred | Read relevant file | Need current state to fix |
| Resuming after gap | Read all planning files | Recover state |

## Session Recovery

When starting a new session, check for previous work:

```bash
# Check if planning files exist
ls task_plan.md findings.md progress.md 2>/dev/null

# If they exist, read them all before continuing
cat task_plan.md findings.md progress.md
```

If planning files exist from a previous session:
1. Read all three files to recover context
2. Run `git diff --stat` to see what changed
3. Update planning files with any missing context
4. Continue from where you left off

## Templates

Copy these to start:

- [templates/task_plan.md](templates/task_plan.md) — Phase tracking
- [templates/findings.md](templates/findings.md) — Research storage
- [templates/progress.md](templates/progress.md) — Session logging

## Scripts

Helper scripts for automation:

- `scripts/init-session.sh` — Initialize all planning files
- `scripts/check-complete.sh` — Verify all phases complete

## References

- [references/manus-principles.md](references/manus-principles.md) — Context engineering principles from Manus

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Use TodoWrite for persistence | Create task_plan.md file |
| State goals once and forget | Re-read plan before decisions |
| Hide errors and retry silently | Log errors to plan file |
| Stuff everything in context | Store large content in files |
| Start executing immediately | Create plan file FIRST |
| Repeat failed actions | Track attempts, mutate approach |
| Create files in skill directory | Create files in your project |

## NEVER Do

1. **NEVER start a complex task without task_plan.md** — this is non-negotiable
2. **NEVER repeat a failed action exactly** — track what you tried, mutate the approach
3. **NEVER ignore errors** — log every error with resolution attempts
4. **NEVER rely on memory after >10 tool calls** — re-read your plan
5. **NEVER skip the 2-Action Rule for visual content** — multimodal data gets lost
6. **NEVER proceed past 3 failures without escalating** — ask the user for help
7. **NEVER create planning files in the skill directory** — they go in your project root

---

## 适用场景 / 常见疑问 / 反模式 / 快速示例
- **适用场景**：见上方 SKILL.md 正文（受众 + 触发词 + 能力边界）。
- **常见疑问**：是否联网 / 读取私钥？→ 默认只读、零网络外呼、无密钥访问（详见 SKILL.md 安全约定）。
- **反模式**：不要期望它在所有场景都给答案；超出能力边界时它会诚实说明，而非编造。
- **快速示例**：见 SKILL.md 中的命令 / 脚本用法与模板。
