---
description: Aplica el buffer de foco a una estimación de tiempo. Uso: /sq-estimate <duración>
allowed-tools: [Bash]
---

# /sq-estimate

Argumentos: `$ARGUMENTS`

Aplica el multiplicador de foco a la estimación provista ejecutando `estimate_buffer.py`.

## Paso 1: Validar argumento

`$ARGUMENTS` es la estimación del usuario (ej: `2h`, `30 min`, `1.5 hours`, `90`).
Si está vacío, preguntar: "¿Cuánto estimás que va a llevar?"

## Paso 2: Localizar el script

```bash
SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/estimate_buffer.py" \
    "$(find "${HOME}/.claude" -name 'estimate_buffer.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'estimate_buffer.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ No se encontró estimate_buffer.py. Verificá la instalación del plugin." && exit 1
```

## Paso 3: Ejecutar el script

```bash
RESULT=$(python3 "$SCRIPT" --estimate "$ARGUMENTS" --pretty 2>&1)
EXIT_CODE=$?
```

Si `EXIT_CODE != 0`, mostrar el error y detener.

## Paso 4: Renderizar el resultado

Con el JSON devuelto, renderizar:

```
⏱️  Estimación con buffer de foco

  Tu estimación:  <user_estimate_human>
  Multiplicador:  ×<multiplier>
  Estimación real: <adjusted_human>

  💡 <explanation>
```

Luego ofrecer: "¿Querés que divida <adjusted_human> en chunks manejables? Corrés /sq-chunk <adjusted_human>."
