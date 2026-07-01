# git-cliff — Auto Changelog Generator

## What it does

Reads your git commit history → groups by type → writes `CHANGELOG.md` automatically.

No manual writing needed.

---

## Commit message format (required)

```
feat: add DMP fitting node
fix: correct launch file reference
chore: clean up CMakeLists
refactor: rename so101_teleop to joy_teleop
docs: update README for vlm_perception
```

| Prefix | Means | Shows in changelog as |
|--------|-------|-----------------------|
| `feat:` | New feature | Added |
| `fix:` | Bug fix | Fixed |
| `chore:` | Cleanup, rename, dependency update | Chores |
| `refactor:` | Code restructure, no new feature | Changed |
| `docs:` | README, comments only | Docs |
| anything else | Uncategorized | Other |

---

## Commands

```bash
# Preview what the new CHANGELOG would look like (does not write file)
git-cliff --unreleased

# Write full CHANGELOG.md (overwrites the file)
git-cliff -o CHANGELOG.md

# Append only new commits since last tag
git-cliff --unreleased --prepend CHANGELOG.md
```

**Use `--unreleased`** to see only commits not yet in CHANGELOG.
**Use `-o CHANGELOG.md`** at the end of a milestone to update the file.

---

## Config file

`cliff.toml` — at workspace root `/home/mira/workspaces/lerobot_ws/cliff.toml`

Do not delete it. git-cliff reads it automatically.

---

## Workflow

1. Write commits with prefix: `feat:`, `fix:`, `chore:` etc.
2. At end of milestone (working feature, major fix): run `git-cliff -o CHANGELOG.md`
3. Commit the updated CHANGELOG: `git commit -m "chore: update CHANGELOG"`
