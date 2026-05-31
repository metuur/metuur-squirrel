---
description: Descompone una estimación de tiempo en chunks ADHD-friendly con distribución por fases. Uso: /sq-chunk <duración> [--custom-phases name1=N,name2=M]
allowed-tools: [Bash]
---

# /sq-chunk

Argumentos: `$ARGUMENTS`

Descompone la tarea en chunks ADHD-friendly ejecutando `chunk_helper.py`.

## Paso 1: Parsear argumentos

De `$ARGUMENTS` extraer:
- **duración**: número + unidad (ej: `4h`, `90min`, `2.5 hours`, `240 minutes`). Convertir a `--hours N` o `--minutes N` para el script.
- **--custom-phases**: si está presente, pasarlo como `--custom-phases "..."`.
- **--threshold**: minutos mínimos antes de activar el chunking (default: 120). Pasar como `--threshold N` al script si está presente.

Si no se especifica duración, preguntar: "¿Cuánto tiempo estimás para esta tarea?"

## Paso 2: Localizar el script

```bash
SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/chunk_helper.py" \
    "$(find "${HOME}/.claude" -name 'chunk_helper.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'chunk_helper.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ No se encontró chunk_helper.py. Verificá la instalación del plugin." && exit 1
```

## Paso 3: Ejecutar el script

```bash
RESULT=$(python3 "$SCRIPT" --hours <N> --threshold <T> --pretty 2>&1)
EXIT_CODE=$?
```

Si `EXIT_CODE != 0`, mostrar el error y detener.

## Paso 4: Renderizar el resultado

Si el JSON contiene `"below_threshold": true`, mostrar:

```
✅ Esta tarea es ≤{threshold_minutes}min — no necesita chunking. ¿Querés arrancar directo?
```

De lo contrario, con el JSON devuelto, renderizar:

```
🧩 Chunk Plan — <total_human>

Fases:
  🔬 Research & Planning   (<min>min)  → <n_chunks> chunk(s)
  🛠  Setup & Scaffolding   (<min>min)  → <n_chunks> chunk(s)
  ⚙️  Core Implementation   (<min>min)  → <n_chunks> chunk(s)
  ✨ Polish & Edge Cases    (<min>min)  → <n_chunks> chunk(s)
  🧪 Testing & Docs         (<min>min)  → <n_chunks> chunk(s)

Sesiones sugeridas (<total_chunks> chunks en <N> sesión/es):
  📅 Sesión 1 (<total_minutes>min): [chunk1, chunk2, ...]
  📅 Sesión 2 (<total_minutes>min): [...]

Estimación: ~<estimated_days> día(s) de trabajo
```

Luego preguntar: "¿Querés nombrar los chunks para este intent específico?"
Si sí, pedir el nombre del intent y proponer nombres contextuales para cada chunk.
