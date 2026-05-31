---
description: Descompone un intent grande en chunks ADHD-friendly (≤60 min cada uno) con nombres específicos del dominio y condiciones de done.
allowed-tools: [Bash, Read, Write]
---

# /sq-chunk-intent

Toma un intent del vault (o descripción libre) y lo descompone en fases + chunks manejables.

Argumentos opcionales: `[INTENT-TAG]`, `--vault NAME` (default si se omite)

Invoca el skill `squirrel-chunk-intent` (ver `skills/chunk-intent/SKILL.md`).

El skill:
1. Lee el intent del vault (si se pasa TAG)
2. Pide o confirma la estimación de tiempo total
3. Corre `estimate_buffer.py` para aplicar multiplicador ADHD
4. Corre `chunk_helper.py` para calcular la estructura de fases
5. Rellena nombres específicos del dominio (trabajo del LLM)
6. Presenta el plan con "Done when" por cada chunk
7. Ofrece escribir los chunks como checkboxes en el intent
8. Ofrece hacer handoff al skill `task-initiation` para el primer chunk
