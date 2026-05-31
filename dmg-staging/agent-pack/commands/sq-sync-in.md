---
description: Procesa un paquete SQUIRREL recibido por email/clipboard. Detección automática también: si pegás un bloque SQUIRREL-PACKAGE, se invoca solo.
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# /sq-sync-in

Aplica el paquete pegado en el chat (o el último guardado en `<vault>/.squirrel/incoming/`).

Invoca el skill `squirrel:sync-in` que:
1. Parsea el bloque SQUIRREL-PACKAGE (start/end markers)
2. Valida hash SHA-256
3. Verifica que el `to` field coincide con este entorno
4. Para cada archivo: chequea conflictos con vault local
5. Muestra plan de aplicación (tabla con operaciones)
6. Muestra diffs para conflictos/updates
7. Pide confirmación (todo / selectivo / cancelar)
8. Aplica operaciones atómicamente
9. Linkea nuevos intents desde Project Pages
10. Loguea aplicación en `<vault>/.squirrel/applied/<timestamp>-<hash>.json`

Flags:
- `--dry-run`: solo muestra qué pasaría, sin escribir
- `--from-file <path>`: lee paquete desde archivo en vez de del clipboard/chat
- `--force-hash`: aplica aunque el hash no matchee (peligroso)
- `--vault NAME`: operar sobre un vault específico (default si se omite)
