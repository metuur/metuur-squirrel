---
description: Genera un paquete SQUIRREL para transferir manualmente al otro entorno (personal↔trabajo) vía email o clipboard.
allowed-tools: [Read, Glob, Grep, Bash]
---

# /sq-sync-out

Genera paquete para transferir al otro entorno. Argumentos: $ARGUMENTS

Invoca el skill `squirrel:sync-out` que:
1. Determina scope (intent / proyecto / research / decisiones / manual)
2. Recolecta archivos del vault local
3. Ejecuta compliance check (escaneo de secretos, validación de dirección)
4. Compone paquete Markdown con header, hash SHA-256, payload
5. Muestra el paquete en pantalla
6. Ofrece: copiar al clipboard / abrir mailto: / guardar a archivo / solo mostrar
7. Loguea el export en `<vault>/.squirrel/outgoing/log.jsonl`

Scopes válidos:
- `--scope=<TAG>` — un intent específico
- `--scope=<PROJECT>:research` — toda la investigación de un proyecto
- `--scope=<PROJECT>:decisions` — solo decisiones
- `--scope=<PROJECT>:*` — proyecto completo
- `--since=<DATE>` — modificado desde fecha
- `--manual` — selección interactiva

Flags adicionales:
- `--encrypt` — pasar por GPG (si configurado)
- `--no-shutdown-notes` — excluir shutdown notes (paquete más liviano)
- `--vault NAME` — operar sobre un vault específico (default si se omite)
