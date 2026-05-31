---
description: Inicia una sesión de trabajo sobre un proyecto, cargando todo el contexto desde el vault. Uso: /sq-start [PROJECT-TAG]
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# /sq-start

Inicia una sesión sobre el proyecto `$ARGUMENTS` (o pregunta si no se especifica).

Argumentos opcionales:
- `--vault NAME` — operar sobre un vault específico (default si se omite)

Invoca el skill `squirrel:session-start` para:
1. Identificar el proyecto activo
2. Leer la Project Page y los intents
3. Generar un loading note de máximo 200 palabras con: lo que estoy haciendo, lo último que hice, next physical action, bloqueos, contexto crítico, sugerencia de apertura concreta

El skill actualiza `~/.squirrel/state.json` con el proyecto y intent activos.

Después del loading note, ofrece UNA acción concreta para empezar (abrir archivo X línea Y, correr test Z, etc.).
