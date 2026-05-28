---
description: Crea un nuevo proyecto en el vault (project page + intent opcional). Uso: /sq-new-project [TAG] [--tipo A|B|C] [--deadline YYYY-MM-DD] [--description "..."] [--first-intent-tag TAG-X-001 --first-intent-title "..."] [--stakeholders "@a,@b"] [--vault NAME] [--force]
allowed-tools: [Bash, Read, Write]
---

# /sq-new-project

Crea un nuevo proyecto en el vault con argumentos `$ARGUMENTS`.

Invoca el skill `squirrel:new-project` que:

1. Valida el tag de proyecto (UPPERCASE, sin esquema de intent).
2. Valida `tipo` (A/B/C), `deadline` (ISO date) y el tag opcional del primer intent.
3. Chequea capacidad WIP del vault (rechaza si está al tope salvo `--force`).
4. Escribe `01-Proyectos-Activos/<TAG>/<TAG>.md` (project page) y, si se pidió,
   `01-Proyectos-Activos/<TAG>/<FIRST-INTENT>.md` desde `templates/intent.md`.
5. No sobreescribe — si el proyecto existe, sale con error.

## Ejemplos

```
/sq-new-project MYAPP --tipo C
/sq-new-project VISA-FAMILIA-2027 --tipo B --deadline 2027-01-15
/sq-new-project SIDEPROJECT-WIDGET --tipo C --first-intent-tag SIDEPROJECT-WIDGET-SETUP-001 --first-intent-title "Inicializar repo y CI"
```

Si faltan campos obligatorios (`tag`, `tipo`), el skill pregunta antes de escribir.
