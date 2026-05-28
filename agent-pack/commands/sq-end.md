---
description: Cierra la sesión actual, genera shutdown note estructurada y la guarda en el intent activo. Aplica el truco de Hemingway (sugerir parar en punto "going good").
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# /sq-end

Cierra la sesión actual.

Invoca el skill `squirrel:session-end` para:
1. Leer state.json e identificar el intent activo
2. Reconstruir lo que pasó en la sesión (de la conversación + git)
3. Generar shutdown note con: estado, next physical action, hipótesis activa, bloqueos, decisiones tomadas
4. Pedir confirmación antes de aplicar
5. Actualizar checkboxes de Definition of Done si corresponde
6. Sugerir commit con tag semántico
7. Aplicar Hemingway (sugerir parar en punto "going good" o dejar TODO en próxima línea)

Argumentos opcionales:
- `--quick`: shutdown rápido (2 líneas, sin estructura completa)
- `--commit`: además de la shutdown note, hacer commit automáticamente
- `--vault NAME` — operar sobre un vault específico (default si se omite)
