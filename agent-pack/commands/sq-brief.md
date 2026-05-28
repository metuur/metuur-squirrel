---
description: Genera un brief estructurado de 6 secciones (now/done/next/decisions/steps/context) listo para copiar a email, Slack o stand-up.
allowed-tools: [Read, Glob, Grep]
---

# /sq-brief

Genera un brief del proyecto `$ARGUMENTS` (o el proyecto activo).

Invoca el skill `squirrel:brief` que produce las 6 secciones:
1. 🎯 Lo que estoy haciendo (NOW)
2. ✅ Lo que ya hice (DONE)
3. 🎬 Lo que falta (NEXT)
4. 🧠 Decisiones tomadas (DECISIONS)
5. 🚦 Próximos pasos (STEPS)
6. 🌐 Contexto importante (CONTEXT)

Argumentos opcionales:
- `--short`: versión Slack/stand-up (3 líneas)
- `--email <stakeholder>`: formato email + abre draft mailto:
- `--all`: brief de todos los proyectos WIP (para weekly review)
- `--vault NAME`: operar sobre un vault específico (default si se omite)
