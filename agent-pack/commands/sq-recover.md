---
description: Recupera el contexto de una sesión olvidada (sin /sq-end). Usa session-manifest.jsonl o historial de Claude. Uso: /sq-recover [--scope TAG]
allowed-tools: [Bash, Read, Write]
---

# /sq-recover

Argumentos: `$ARGUMENTS`

Argumentos opcionales:
- `--vault NAME` — operar sobre un vault específico (default si se omite)

Recupera una sesión perdida (cuando se olvidó `/sq-end`).

Invoca el skill `squirrel:recover` con los argumentos recibidos.
