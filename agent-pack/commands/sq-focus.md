---
description: "Muestra o cambia el manual focus pick (hoy / esta semana). Uso: /sq-focus | /sq-focus today TAG/INTENT-SLUG | /sq-focus week TAG/INTENT-SLUG | /sq-focus today --clear | /sq-focus week --clear"
allowed-tools: [Bash]
---

# /sq-focus

Argumentos: `$ARGUMENTS`

Gestiona el **manual focus pick** del usuario para hoy y esta semana, hablándole al backend de squirrel (`http://127.0.0.1:3939`).

Formas válidas de invocación:

- `/sq-focus` — muestra el foco actual de hoy y de esta semana.
- `/sq-focus today TAG/INTENT-SLUG` — fija el foco de hoy.
- `/sq-focus week TAG/INTENT-SLUG` — fija el foco de esta semana.
- `/sq-focus today --clear` — limpia el foco de hoy.
- `/sq-focus week --clear` — limpia el foco de esta semana.

**Importante (R-7.8):** NO leas ni escribas archivos del vault directamente. Toda la lectura/escritura va por `/api/focus/*`.

## Paso 1: Parsear argumentos

```bash
# Normalizar args en variables POSIX. $ARGUMENTS es la línea cruda detrás de /sq-focus.
set -- $ARGUMENTS
SUBCMD="${1:-}"
TARGET="${2:-}"

BASE="http://127.0.0.1:3939"
```

Casos:

- Sin `$1` → branch GET (Paso 2).
- `$1` = `today` o `week` y `$2` = `--clear` → branch CLEAR (Paso 4).
- `$1` = `today` o `week` y `$2` con forma `TAG/INTENT-SLUG` → branch SET (Paso 3).
- Cualquier otra combinación (`today` sin slug, slot desconocido, etc.) → mostrar uso y exit 1:
  ```
  Usage: /sq-focus | /sq-focus today TAG/INTENT-SLUG | /sq-focus week TAG/INTENT-SLUG | /sq-focus today --clear | /sq-focus week --clear
  ```

## Paso 2: Bare invocation — GET /api/focus  (R-7.2)

```bash
RESP=$(curl -sS --max-time 2 "$BASE/api/focus" 2>/dev/null)
CURL_RC=$?
if [ "$CURL_RC" -eq 7 ] || [ "$CURL_RC" -eq 28 ] || [ "$CURL_RC" -eq 6 ] || [ "$CURL_RC" -eq 52 ]; then
  echo "Backend offline — run \`make backend-start\`"
  exit 1
fi
if [ "$CURL_RC" -ne 0 ]; then
  echo "Backend offline — run \`make backend-start\`"
  exit 1
fi

printf '%s' "$RESP" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print("Today: (none)")
    print("This week: (none)")
    sys.exit(0)

def fmt(slot, label):
    pick = data.get(slot)
    if not pick:
        return f"{label}: (none)"
    pt = pick.get("project_title") or pick.get("project_slug") or "?"
    it = pick.get("intent_title")  or pick.get("intent_slug")  or "?"
    return f"{label}: {pt} / {it}"

print(fmt("today", "Today"))
print(fmt("week",  "This week"))
'
exit 0
```

Salida esperada (exactamente dos líneas; R-7.2):

```
Today: {project_title} / {intent_title}
This week: {project_title} / {intent_title}
```

Si un slot es `null`, esa línea debe decir `Today: (none)` o `This week: (none)`.

## Paso 3: SET — PUT /api/focus/{slot}  (R-7.3, R-7.4)

Cuando `$SUBCMD` es `today` o `week` y `$TARGET` tiene forma `TAG/INTENT-SLUG`:

```bash
SLOT="$SUBCMD"   # today | week
if ! printf '%s' "$TARGET" | grep -q '/'; then
  echo "Usage: /sq-focus | /sq-focus today TAG/INTENT-SLUG | /sq-focus week TAG/INTENT-SLUG | /sq-focus today --clear | /sq-focus week --clear"
  exit 1
fi
TAG="${TARGET%%/*}"
SLUG="${TARGET#*/}"
if [ -z "$TAG" ] || [ -z "$SLUG" ] || [ "$TAG" = "$TARGET" ]; then
  echo "Usage: /sq-focus | /sq-focus today TAG/INTENT-SLUG | /sq-focus week TAG/INTENT-SLUG | /sq-focus today --clear | /sq-focus week --clear"
  exit 1
fi

BODY=$(printf '{"project_slug":"%s","intent_slug":"%s"}' "$TAG" "$SLUG")
HTTP_STATUS=$(curl -sS --max-time 2 -o /tmp/sq-focus-resp.json -w "%{http_code}" \
    -X PUT "$BASE/api/focus/$SLOT" \
    -H "Content-Type: application/json" \
    -d "$BODY" 2>/dev/null)
CURL_RC=$?

if [ "$CURL_RC" -eq 7 ] || [ "$CURL_RC" -eq 28 ] || [ "$CURL_RC" -eq 6 ] || [ "$CURL_RC" -eq 52 ] || [ -z "$HTTP_STATUS" ]; then
  echo "Backend offline — run \`make backend-start\`"
  exit 1
fi
if [ "$HTTP_STATUS" = "404" ]; then
  echo "No such intent: $TAG/$SLUG"
  exit 1
fi
if [ "$HTTP_STATUS" != "200" ] && [ "$HTTP_STATUS" != "204" ]; then
  echo "Error ($HTTP_STATUS): $(cat /tmp/sq-focus-resp.json 2>/dev/null)"
  exit 1
fi

if [ "$SLOT" = "today" ]; then
  echo "Today's focus set: $TAG/$SLUG"
else
  echo "This week's focus set: $TAG/$SLUG"
fi
exit 0
```

## Paso 4: CLEAR — PUT /api/focus/{slot} con {"clear": true}  (R-7.5)

Cuando `$SUBCMD` es `today` o `week` y `$TARGET` es `--clear`:

```bash
SLOT="$SUBCMD"

HTTP_STATUS=$(curl -sS --max-time 2 -o /tmp/sq-focus-resp.json -w "%{http_code}" \
    -X PUT "$BASE/api/focus/$SLOT" \
    -H "Content-Type: application/json" \
    -d '{"clear": true}' 2>/dev/null)
CURL_RC=$?

if [ "$CURL_RC" -eq 7 ] || [ "$CURL_RC" -eq 28 ] || [ "$CURL_RC" -eq 6 ] || [ "$CURL_RC" -eq 52 ] || [ -z "$HTTP_STATUS" ]; then
  echo "Backend offline — run \`make backend-start\`"
  exit 1
fi
if [ "$HTTP_STATUS" != "200" ] && [ "$HTTP_STATUS" != "204" ]; then
  echo "Error ($HTTP_STATUS): $(cat /tmp/sq-focus-resp.json 2>/dev/null)"
  exit 1
fi

if [ "$SLOT" = "today" ]; then
  echo "Today's focus cleared."
else
  echo "This week's focus cleared."
fi
exit 0
```

## Notas

- **Backend offline (R-7.6):** detectamos `curl` exit code 7 (connection refused), 28 (timeout), 6 (no resolvió host) o 52 (sin respuesta). En todos esos casos imprimimos exactamente `Backend offline — run \`make backend-start\`` y salimos con status 1.
- **404 intent_not_found (R-7.7):** cuando el HTTP status es `404` (cualquier branch SET), imprimimos `No such intent: TAG/INTENT-SLUG` y salimos con 1. No inspeccionamos el body — el backend ya devuelve `{"error":"intent_not_found"}` por contrato.
- **No vault writes (R-7.8):** todo viaja por `/api/focus/*`. No tocar archivos del vault desde acá.
- **Sin jq:** la respuesta GET se parsea con `python3 -c` (stdlib) — match con la convención de los otros `sq-*`.
