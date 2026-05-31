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

**De**: {{from_env}}  →  **Para**: {{to_env}}
**Generado**: {{human_date}}
**Scope**: {{scope}}
**Archivos**: {{count}}

> 📋 Para aplicar: en el otro entorno, abrí Claude Code / Codex y pegá ESTE bloque completo
> en el chat. El skill `squirrel:sync-in` lo procesará automáticamente.

---

## 📑 Resumen del paquete

{{#each files}}
- `{{target_path}}` — {{operation}} — {{description}}
{{/each}}

---

## 📂 Archivos a aplicar

{{#each files}}

### Archivo {{index}}: {{target_path}}

**Operación**: {{operation}}
**Tag**: `{{tag}}`
**Conflicto si existe**: {{conflict_policy}}

```markdown
{{content}}
```

---
{{/each}}

<!-- END-SQUIRREL-PACKAGE -->
