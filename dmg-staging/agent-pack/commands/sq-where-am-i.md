---
description: "¿En qué estaba?" — Muestra el estado actual de todos los proyectos WIP y sugiere por dónde retomar.
allowed-tools: [Read, Glob, Grep]
---

# /sq-where-am-i

Diagnóstico rápido: ¿en qué estabas?

Argumentos opcionales:
- `--vault NAME` — operar sobre un vault específico (default si se omite)

Invoca el skill `squirrel:brief` con `--all` para:
1. Listar todos los proyectos WIP
2. Para cada uno: avance estimado, último intent, next action
3. Detectar señales de problema:
   - Proyectos sin actividad >3 días
   - Foyer Family (o cualquier proyecto con `prioridad: finishing-tax`) sin avance
   - Intents bloqueados
4. Sugerir 1 acción concreta para HOY basada en deadlines y bloqueos

Ideal para empezar el día o después de varios días sin tocar el vault.
