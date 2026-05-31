---
description: Protocolo de inicio de tarea contra la parálisis ejecutiva. Detecta el tipo de bloqueo y aplica el protocolo correcto (Smallest Action, 2-Minute Start, Decompose, Emotional Defusion).
allowed-tools: [Bash, Read]
---

# /sq-task-initiation

Rompe la parálisis de inicio. Usa cuando el usuario no puede arrancar una tarea.

Argumentos opcionales: `[INTENT-TAG]`, `--vault NAME` (default si se omite)

Invoca el skill `squirrel-task-initiation` (ver `skills/task-initiation/SKILL.md`).

El skill:
1. Identifica el intent bloqueado (del TAG, del state, o pregunta)
2. Lee la última shutdown note para extraer el "next physical action"
3. Diagnostica el tipo de bloqueo (A=no sé qué hacer / B=no puedo hacer click / C=abrumado / D=miedo)
4. Aplica el protocolo apropiado:
   - **Protocol 1 (Smallest Action)**: abre un archivo específico, nada más
   - **Protocol 2 (2-Minute Start)**: solo 2 minutos, después podés parar
   - **Protocol 3 (Decompose)**: la tarea es muy grande → ofrece `/sq-chunk-intent`
   - **Protocol 4 (Emotional Defusion)**: "¿qué harías si supieras que va a salir bien?"
5. Se queda presente hasta confirmar el primer micro-acción
6. Hace handoff suave al working mode

Triggers automáticos (desde `session-start`): intent en "in-progress" por >3 sesiones sin nuevo shutdown note.
