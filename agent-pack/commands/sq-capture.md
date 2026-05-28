---
description: Captura una nota, idea, research finding, o contexto al vault con tag semántico.
allowed-tools: [Read, Write, Glob]
---

# /sq-capture

Captura: $ARGUMENTS

Argumentos opcionales:
- `--vault NAME` — operar sobre un vault específico (default si se omite)

Invoca el skill `squirrel:capture` que:
1. Determina tag semántico apropiado (`PROYECTO-SUBÁREA-NNN`)
2. Detecta tipo de nota (intent / research / constraint / reference)
3. Compone la nota con frontmatter
4. La escribe en el folder correspondiente del vault
5. Linkea desde Project Page si aplica
