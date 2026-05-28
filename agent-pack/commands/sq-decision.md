---
description: Captura una decisión arquitectónica/de diseño como ADR ligero en el vault.
allowed-tools: [Read, Write, Glob]
---

# /sq-decision

Captura una decisión sobre $ARGUMENTS (o sobre la conversación reciente).

Argumentos opcionales:
- `--vault NAME` — operar sobre un vault específico (default si se omite)

Invoca el skill `squirrel:decision` que:
1. Asigna tag `<PROYECTO>-DECISION-<NNN>`
2. Extrae de la conversación: contexto, decisión, alternativas consideradas, consecuencias
3. Pide confirmación de los campos
4. Crea archivo `<PROYECTO>-DECISION-<NNN>.md` con formato ADR
5. Linkea desde la Project Page
6. Ofrece notificar a stakeholders relevantes
