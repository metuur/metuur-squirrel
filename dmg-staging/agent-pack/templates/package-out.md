<!-- SQUIRREL-PACKAGE v1 -->
<!--
  from: {{from_env}}
  to: {{to_env}}
  generated_at: {{iso_timestamp}}
  generated_by: {{agent_name}}@{{hostname}}
  scope: {{scope}}
  files_count: {{count}}
  hash_sha256: {{hash}}
  intent: {{intent_description}}
  receiver_instructions: apply-with-sync-in
-->

# 📦 Context Bridge Package

**From**: {{from_env}}  →  **To**: {{to_env}}
**Generated**: {{human_date}}
**Scope**: {{scope}}
**Files**: {{count}}

> 📋 To apply: in the other environment, open Claude Code / Codex and paste THIS entire block
> into the chat. The `squirrel:sync-in` skill will process it automatically.

---

## 📑 Package Summary

{{#each files}}
- `{{target_path}}` — {{operation}} — {{description}}
{{/each}}

---

## 📂 Files to Apply

{{#each files}}

### File {{index}}: {{target_path}}

**Operation**: {{operation}}
**Tag**: `{{tag}}`
**Conflict if exists**: {{conflict_policy}}

```markdown
{{content}}
```

---
{{/each}}

<!-- END-SQUIRREL-PACKAGE -->
