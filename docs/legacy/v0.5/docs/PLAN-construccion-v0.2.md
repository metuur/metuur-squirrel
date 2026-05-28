# 🏗️ Plan de Construcción — squirrel v0.2.0

> Plan detallado para construir el plugin completo, con énfasis en automatización por scripts y mínimo consumo de tokens.

---

## 🎯 Principios de diseño v0.2.0

### Principio 1: Scripts hacen el trabajo determinístico
Cada operación que NO requiere juicio (parsear, calcular, validar, leer/escribir archivos) la hace un script Python stdlib-only. El LLM solo procesa la salida estructurada.

### Principio 2: Las skills SON delgadas
Cada SKILL.md debe ser ≤200 líneas. Si crece más, es señal de que hay lógica que debería estar en un script.

### Principio 3: Token budget consciente
Cada skill declara su token budget esperado. Si una invocación promedio supera 5K tokens, hay que refactorizar.

### Principio 4: JSON entre script y LLM
Los scripts devuelven JSON estructurado. El LLM lo lee y lo presenta. NO el LLM parsea Markdown crudo del vault.

### Principio 5: Caching agresivo
Operaciones costosas (scan completo del vault) cachean a `<vault>/.squirrel/cache/` con TTL.

---

## 🗂️ Arquitectura v0.2.0

```
squirrel/
├── .claude-plugin/
│   └── plugin.json
│
├── skills/                       # SKILL.md delgados (≤200 líneas cada uno)
│   ├── capture/
│   ├── session-start/
│   ├── session-end/
│   ├── brief/
│   ├── decision/
│   ├── sync-out/
│   ├── sync-in/
│   ├── hyperfocus-guardian/      # NUEVO
│   ├── parakeet/                 # NUEVO
│   ├── task-initiation/          # NUEVO
│   └── chunk-intent/             # NUEVO
│
├── commands/                     # Slash commands (thin wrappers)
│   └── ...
│
├── hooks/
│   └── hooks.json                # Hooks que disparan SCRIPTS, no LLM calls
│
├── lib/                          # ★ EL CORAZÓN — scripts stdlib-only
│   ├── package_protocol.py       # (ya existe, v0.1)
│   ├── vault_io.py               # ★ Lectura/escritura genérica del vault
│   ├── deadline_scanner.py       # NUEVO ★
│   ├── switch_tracker.py         # NUEVO ★
│   ├── chunk_helper.py           # NUEVO ★
│   ├── estimate_buffer.py        # NUEVO ★
│   ├── activity_monitor.py       # NUEVO ★
│   ├── focus_score.py            # NUEVO ★
│   ├── status_aggregator.py      # NUEVO ★ — el más importante
│   ├── intent_parser.py          # ★ parsea frontmatter + secciones
│   └── tag_validator.py          # ★ valida formato de tags
│
├── templates/
│   └── ...
│
├── config/
│   ├── squirrel.toml.example
│   └── parakeet-messages.toml    # NUEVO — mensajes por urgencia
│
├── tests/                        # NUEVO — tests para los scripts
│   ├── test_deadline_scanner.py
│   ├── test_switch_tracker.py
│   ├── test_status_aggregator.py
│   └── test_intent_parser.py
│
└── examples/
    └── ...
```

---

## 📦 Componentes nuevos en detalle

### 1. `lib/intent_parser.py` — La base de todo

**Propósito**: Parsear un archivo de intent (frontmatter YAML + body Markdown) en estructura Python.

**Input**: path a archivo `.md`
**Output**: dict estructurado

**Por qué importa**: Todas las demás funciones se basan en esto. Si está bien, todo está bien.

```python
# Pseudo-código
def parse_intent(path: Path) -> dict:
    return {
        "id": "TRABAJO-PROYECTO-A-AUTH-002",
        "frontmatter": {
            "id": "...",
            "proyecto": "...",
            "estado": "in-progress",
            "prioridad": "alta",
            "creado": date,
            "deadline": date,
            "tags": [...],
        },
        "title": "TRABAJO-PROYECTO-A-AUTH-002 — Validación de state CSRF",
        "sections": {
            "intent": "...",
            "definition_of_done": ["criterio 1", "criterio 2"],
            "definition_of_done_done": ["criterio 0"],  # checkboxes marcadas
            "tareas": [...],
            "notas": "...",
            "relacionados": {...},
            "shutdown_notes": [
                {"timestamp": "2026-05-22 17:30", "estado": "...", "next_action": "...", ...},
                {"timestamp": "2026-05-20 18:00", "estado": "...", ...},
            ],
        },
        "stats": {
            "total_criteria": 5,
            "done_criteria": 2,
            "percent_done": 40,
            "shutdown_count": 2,
            "last_activity": "2026-05-22T17:30:00",
            "days_since_last_activity": 1,
        }
    }
```

**Test coverage**: 90%+ porque todo depende de él.

---

### 2. `lib/deadline_scanner.py` — Parakeet engine

**Propósito**: Escanear todo el vault, encontrar intents con deadline, calcular urgencia.

**Uso**:
```bash
python3 lib/deadline_scanner.py --vault ~/vault-tdah --output json
```

**Output (JSON)**:
```json
{
  "scanned_at": "2026-05-23T19:30:00Z",
  "total_intents_with_deadline": 12,
  "by_urgency": {
    "critical": [
      {"id": "TRABAJO-A-AUTH-002", "deadline": "2026-05-24", "hours_left": 3.5, "title": "..."}
    ],
    "urgent": [
      {"id": "VISA-FAMILIA-DOCS-001", "deadline": "2026-05-25", "days_left": 2, "title": "..."}
    ],
    "soon": [...],
    "upcoming": [...],
    "future_fyi": [...]
  },
  "overdue": [
    {"id": "SIDEPROJECT-FOYER-FAMILY-DEPLOY-001", "deadline": "2026-05-15", "days_overdue": 8, "title": "..."}
  ]
}
```

**Token saving**: en lugar de que el LLM lea 30 archivos para encontrar deadlines, llama al script y recibe 1 JSON.

---

### 3. `lib/switch_tracker.py` — Context switch ledger

**Propósito**: Registrar cada `/sq-start` con proyecto distinto al anterior. Calcular focus_score diario.

**Uso**:
```bash
# Al hacer /sq-start
python3 lib/switch_tracker.py record --from "TRABAJO-A" --to "FOYER-FAMILY" --reason voluntary

# Al hacer /sq-status
python3 lib/switch_tracker.py status --vault ~/vault-tdah
```

**Storage**: `<vault>/.squirrel/switches.jsonl` (append-only, audit-friendly)

**Output de `status`**:
```json
{
  "today": {
    "date": "2026-05-23",
    "switches": 3,
    "budget": 2,
    "over_budget": true,
    "focus_score": 40,
    "contexts": ["TRABAJO-PROYECTO-A", "SIDEPROJECT-FOYER-FAMILY", "VISA-FAMILIA"]
  },
  "this_week": {
    "total_switches": 14,
    "avg_per_day": 2.8,
    "best_day": {"date": "2026-05-20", "switches": 1, "focus_score": 80},
    "worst_day": {"date": "2026-05-22", "switches": 5, "focus_score": 0}
  }
}
```

**Trigger desde hook**: el comando `/sq-start <X>` invoca el script ANTES de cargar contexto. Si está over-budget, el skill puede preguntar antes de continuar.

---

### 4. `lib/status_aggregator.py` — El comando más usado

**Propósito**: Generar el JSON de estado completo del vault. **Reemplaza ~3000 tokens de lectura del LLM por una llamada de script.**

**Uso**:
```bash
python3 lib/status_aggregator.py --vault ~/vault-tdah --output json
```

**Output**:
```json
{
  "vault_path": "/home/user/vault-tdah",
  "scanned_at": "2026-05-23T19:30:00Z",
  "config": {
    "wip_max": 3,
    "active_projects_configured": ["TRABAJO-PROYECTO-A", "SIDEPROJECT-FOYER-FAMILY", "VISA-FAMILIA"]
  },
  "wip": {
    "count": 3,
    "max": 3,
    "at_capacity": true,
    "projects": [
      {
        "id": "TRABAJO-PROYECTO-A",
        "type": "A",
        "deadline": "2026-06-15",
        "days_to_deadline": 23,
        "intents": {
          "total": 12,
          "done": 4,
          "in_progress": 1,
          "pending": 6,
          "blocked": 1,
          "percent_done": 33
        },
        "active_intent": "TRABAJO-PROYECTO-A-AUTH-002",
        "last_activity": "2026-05-22T17:30:00",
        "days_since_activity": 1,
        "next_physical_action": "abrir auth.controller.ts línea 47..."
      },
      {
        "id": "SIDEPROJECT-FOYER-FAMILY",
        "type": "B",
        "deadline": "2026-06-07",
        "days_to_deadline": 15,
        "priority_flag": "finishing-tax",
        "intents": {"total": 8, "done": 7, "in_progress": 1, "pending": 0, "percent_done": 90},
        "active_intent": "SIDEPROJECT-FOYER-FAMILY-DEPLOY-001",
        "last_activity": "2026-04-10T18:00:00",
        "days_since_activity": 43,
        "alert": "STALE — 43 days without activity, marked finishing-tax"
      }
    ]
  },
  "parking_lot": {"count": 3, "items": [...]},
  "areas": {"count": 5, "items": [...]},
  "deadlines": {/* output of deadline_scanner */},
  "switches_today": {/* output of switch_tracker */},
  "alerts": [
    "SIDEPROJECT-FOYER-FAMILY stale 43 días (finishing-tax)",
    "TRABAJO-PROYECTO-A-AUTH-002 deadline en 3h",
    "Switch budget excedido hoy (3 > 2)"
  ],
  "recommended_focus": {
    "intent_id": "SIDEPROJECT-FOYER-FAMILY-DEPLOY-001",
    "reason": "Finishing tax + 90% complete + 43 días sin actividad + deadline en 15 días"
  }
}
```

**Esto cambia el juego**. El comando `/sq-status` ahora consume ~500 tokens en lugar de ~3000. El comando `/sq-where-am-i` igual.

---

### 5. `lib/chunk_helper.py` — Asistente de chunking

**Propósito**: Dada una estimación de horas, devolver estructura de fases con tiempos.

**Uso**:
```bash
python3 lib/chunk_helper.py --hours 8 --task "implement auth"
```

**Output**:
```json
{
  "total_minutes": 480,
  "phases": [
    {"name": "Research & Planning", "minutes": 72, "percent": 15, "chunks": 1},
    {"name": "Setup & Scaffolding", "minutes": 96, "percent": 20, "chunks": 2},
    {"name": "Core Implementation", "minutes": 192, "percent": 40, "chunks": 4},
    {"name": "Polish & Edge Cases", "minutes": 72, "percent": 15, "chunks": 2},
    {"name": "Testing & Documentation", "minutes": 48, "percent": 10, "chunks": 1}
  ],
  "sessions": [
    {"id": 1, "minutes": 168, "phases": ["Research", "Setup x1"]},
    {"id": 2, "minutes": 144, "phases": ["Setup x1", "Core x2"]},
    {"id": 3, "minutes": 144, "phases": ["Core x2", "Polish x1"]},
    {"id": 4, "minutes": 120, "phases": ["Polish x1", "Test"]}
  ],
  "estimated_days": 2
}
```

El LLM toma esto y le pone nombres específicos a cada chunk (eso sí requiere juicio).

---

### 6. `lib/estimate_buffer.py` — ADHD time multiplier

**Propósito**: Aplicar el multiplicador ADHD (2-3×) a estimaciones del usuario.

**Uso**:
```bash
python3 lib/estimate_buffer.py --estimate "30 min"
# o
python3 lib/estimate_buffer.py --estimate-minutes 30
```

**Output**:
```json
{
  "user_estimate_minutes": 30,
  "multiplier": 3.0,
  "adjusted_minutes": 90,
  "human_estimate": "1.5 hours",
  "explanation": "ADHD time blindness factor: tasks estimated <60 min typically take 3×"
}
```

**Reglas de multiplicador**:
- ≤5 min → ×3
- 6-30 min → ×3
- 30-60 min → ×2.5
- 1-4h → ×2
- 4-8h → ×2
- 8h+ → ×1.5

---

### 7. `lib/activity_monitor.py` — Hyperfocus detector

**Propósito**: Detectar sesiones de hyperfocus monitoreando actividad (git commits, archivos modificados, state.json updates).

**Uso (daemon o on-demand)**:
```bash
python3 lib/activity_monitor.py check --vault ~/vault-tdah
```

**Output**:
```json
{
  "current_session": {
    "active": true,
    "started_at": "2026-05-23T14:30:00Z",
    "duration_minutes": 187,
    "duration_human": "3h 7min",
    "intent": "TRABAJO-PROYECTO-A-AUTH-002",
    "commits_during_session": 4,
    "files_modified": 7
  },
  "hyperfocus_status": "moderate",
  "should_intervene": false,
  "intervention_level": null,
  "next_check_in_minutes": 173
}
```

**Niveles**:
- `none` (<2h): nada
- `moderate` (2-4h): sin intervención
- `deep` (4-6h): logging, no intervención
- `gentle_checkin` (6h): primera sugerencia ("¿comiste? ¿agua?")
- `firm_intervention` (10h): "break obligatorio 30 min"

---

### 8. `lib/focus_score.py` — Métrica diaria

**Propósito**: Calcular un score 0-100 de "calidad de foco" del día.

**Fórmula**:
```
focus_score = 100
  - (switches * 20)              # cada switch resta 20
  - (interruptions * 5)          # cada interrupción no planificada
  + (deep_sessions * 10)         # cada sesión >90min suma
  + (shutdown_notes * 5)         # cada shutdown note bien escrita
clamp to [0, 100]
```

**Storage**: deriva de `switches.jsonl` + parsing de daily notes.

---

## 🆕 Skills nuevas en detalle

### Skill: `hyperfocus-guardian`

**Trigger**: hook periódico (cada 30 min, ejecutado por script externo o cron del usuario) que llama a `activity_monitor.py check`.

**Si `should_intervene: true`**: el skill se dispara con el JSON y compone un mensaje apropiado.

**Output (ejemplo gentle_checkin)**:
```
🦜 Llevás 6h en TRABAJO-PROYECTO-A-AUTH-002 (3 commits, 5 archivos).
Quick check: agua? comida? estiramiento de 2 min?
No urgente — solo respondé "ok" o "más tarde". Volvés cuando quieras.
```

**Por qué barato**: el script ya hizo todo el trabajo. El LLM solo elige tono y compone.

---

### Skill: `parakeet`

**Trigger**: automático en `/sq-status`, `/sq-where-am-i`, o explícito con `/sq-deadlines`.

**Workflow**:
1. Llama `deadline_scanner.py` → recibe JSON con urgencias
2. Por cada urgencia presente, compone mensaje con tono apropiado (5 niveles)
3. Si hay CRITICAL: sugiere acción inmediata
4. Si hay OVERDUE: hace lo mismo + ofrece replanificar deadline

**Mensajes en `config/parakeet-messages.toml`** (configurable por el usuario):
```toml
[future_fyi]
template = "🦜 Solo FYI: {title} vence {date}. Sin acción necesaria."

[critical]
template = "🚨 {title} vence en {hours_left}h. ¿Necesitás soltar algo más?"
```

---

### Skill: `task-initiation`

**Trigger**: lenguaje del usuario indicando bloqueo de inicio:
- "no puedo arrancar"
- "no sé por dónde empezar"
- "estoy procrastinando esto"
- "esto es enorme"
- "evito esto desde hace días"

**Workflow**:
1. Identifica el intent que se está evitando
2. Pregunta una sola cosa: "¿Cuál de estos te ayuda más ahora?"
   - 🚀 **2-Minute Start**: "Trabajá 2 min, después podés parar sin culpa"
   - 🔬 **Smallest Action**: "¿Cuál es la cosa MÁS chica que se puede hacer? (abrir archivo, escribir 1 línea)"
   - 🤝 **Body Double**: "Llamá a alguien en video, trabajen 25 min en silencio"
   - 🎯 **5-4-3-2-1**: "Cuenta atrás y arrancá sin pensar"
   - 🍰 **Temptation Bundling**: "¿Qué dopamina pareás con esta tarea?"
3. Según elección, instruye paso a paso

**Token-efficient**: el skill tiene los 5 protocolos en su SKILL.md (no necesita llamar a otros).

---

### Skill: `chunk-intent`

**Trigger**: `/sq-chunk <INTENT-TAG>` o detección de intent grande sin tareas.

**Workflow**:
1. Lee el intent con `intent_parser.py`
2. Pregunta al usuario: "¿Cuántas horas estimás este intent?"
3. Aplica `estimate_buffer.py` → ajustado
4. Aplica `chunk_helper.py` → estructura de fases
5. El LLM toma la estructura y nombra cada chunk específicamente al dominio del intent
6. Actualiza el intent con las nuevas tareas chunked

---

## 🔄 Mejoras a skills existentes

### `session-start` mejorado

**Antes**: leía Project Page + intents + shutdown notes (~2000 tokens)
**Después**:
1. Llama `status_aggregator.py --project=X` → JSON con todo precomputado
2. Llama `switch_tracker.py status` → si hay over-budget, advierte
3. Compone loading note con datos del JSON (~500 tokens)

**Ahorro**: 4× tokens.

---

### `session-end` mejorado

**Antes**: composición manual de shutdown note
**Después**:
1. LLM compone shutdown note (necesita juicio, sí)
2. Al guardar, llama `switch_tracker.py record` para registrar fin de sesión
3. Llama `activity_monitor.py mark-end` para cerrar sesión de hyperfocus si abierta

---

### `brief` mejorado

**Antes**: leía todos los intents para componer las 6 secciones
**Después**:
1. Llama `status_aggregator.py --project=X --detailed` → JSON con stats + intents
2. LLM compone las 6 secciones del JSON
3. Para deadlines, incluye datos de `deadline_scanner.py`

**Ahorro**: el 80% de la lectura ahora es del script.

---

### `where-am-i` mejorado

**Antes**: scan completo del vault
**Después**:
1. `status_aggregator.py` → JSON completo
2. Si hay `alerts`, las muestra primero
3. Si hay `recommended_focus`, lo sugiere como acción

Esto convierte `/sq-where-am-i` en una llamada de ~300 tokens del LLM.

---

## 🪝 Hooks nuevos / mejorados

### Hook periódico para hyperfocus (NUEVO)

**Implementación**: cron job o systemd timer del usuario, NO un hook del agente.

```bash
# crontab del usuario
*/30 * * * * /usr/bin/python3 ~/.claude/plugins/squirrel/lib/activity_monitor.py check --notify-if-intervention
```

Si `--notify-if-intervention` y el resultado es `gentle_checkin` o `firm_intervention`:
- Envía notificación de OS (notify-send / osascript / etc.)
- Escribe a `<vault>/.squirrel/inbox/pending-checkin.json`
- Próxima vez que el usuario abra Claude Code, hook `SessionStart` ve el pending y dispara el skill `hyperfocus-guardian`

**Por qué importa**: el hyperfocus pasa cuando el usuario NO está mirando el agente. La detección debe ser independiente del agente.

---

### Hook `UserPromptSubmit` mejorado

Detecta más patrones:
- `<!-- SQUIRREL-PACKAGE` → sync-in
- "decidí|elegí|vamos a usar" → decision
- "mandar update|email a (mi lead|sarah|el equipo)" → brief
- "no puedo arrancar|no sé por dónde|procrastinando|esto es enorme|evito" → task-initiation
- "(/sq-)?start (\\w+)" → si el proyecto es distinto al actual → switch_tracker.py record

---

## 📅 Orden de implementación

### Fase 1 — Foundation (la base)
Sin esto, nada más funciona. Prioridad MÁXIMA.

1. **`lib/intent_parser.py`** — parser de frontmatter + secciones
2. **`lib/vault_io.py`** — utilidades de I/O del vault
3. **`lib/tag_validator.py`** — validación de tags semánticos
4. **`tests/test_intent_parser.py`** — al menos 10 casos
5. Refactor de `package_protocol.py` para usar `intent_parser`

**Output**: scripts probados que pueden leer cualquier vault correctamente.

---

### Fase 2 — Status engine
El cambio de juego en tokens.

6. **`lib/deadline_scanner.py`**
7. **`lib/status_aggregator.py`** — el más importante
8. **`tests/test_deadline_scanner.py`**
9. **`tests/test_status_aggregator.py`**
10. Refactor de skills `where-am-i`, `status`, `brief` para usar el aggregator

**Output**: `/sq-where-am-i` y `/sq-status` consumen 5× menos tokens.

---

### Fase 3 — Activity tracking
Para tener métricas y prevenir hyperfocus dañino.

11. **`lib/switch_tracker.py`**
12. **`lib/activity_monitor.py`**
13. **`lib/focus_score.py`**
14. Hook de cron para activity_monitor
15. Skill `hyperfocus-guardian`

**Output**: el sistema te avisa de hyperfocus largos y trackea calidad de foco diaria.

---

### Fase 4 — Skills nuevas
Las skills que faltan, ahora apoyadas en los scripts.

16. Skill `parakeet` + `config/parakeet-messages.toml`
17. Skill `task-initiation`
18. **`lib/chunk_helper.py`** + **`lib/estimate_buffer.py`**
19. Skill `chunk-intent`

**Output**: cobertura completa de flujos ADHD.

---

### Fase 5 — Polish y docs
Lo que hace el plugin shippable.

20. Mejorar todas las skills existentes con anti-patterns y references
21. Documentación: README, INSTALL, ARCHITECTURE actualizados
22. Examples: 3 escenarios completos
23. CI con tests automatizados
24. Release v0.2.0

---

## 📊 Token budget esperado por operación

| Operación | v0.1.0 (current) | v0.2.0 (target) | Ahorro |
|---|---|---|---|
| `/sq-where-am-i` | ~3000 | ~500 | 6× |
| `/sq-status` | ~3000 | ~500 | 6× |
| `/sq-brief X` | ~2500 | ~800 | 3× |
| `/sq-start X` | ~2000 | ~500 | 4× |
| `/sq-end` | ~1500 | ~1200 | 1.2× (juicio necesario) |
| `/sq-sync-out` | ~2000 | ~600 | 3× (script hace todo) |
| `/sq-sync-in` | ~2500 | ~800 | 3× (script hace todo) |

**Sesión típica de 1h**: de ~25K tokens → ~10K tokens. **2.5× ahorro total.**

---

## 🧪 Testing strategy

Los scripts SON la fuente de verdad. Necesitan tests:

```
tests/
├── fixtures/
│   ├── vault-minimal/        # vault con 2-3 archivos para tests rápidos
│   ├── vault-complete/       # vault con todo (use cases reales)
│   └── packages/             # paquetes sync-in válidos e inválidos
│
├── test_intent_parser.py
├── test_deadline_scanner.py
├── test_status_aggregator.py
├── test_switch_tracker.py
└── test_package_protocol.py
```

**Run**: `python3 -m unittest discover tests/`

**CI**: GitHub Actions con `python -m unittest` sobre Python 3.9, 3.10, 3.11, 3.12.

---

## 🔌 Cómo se invocan los scripts desde las skills

### Patrón estándar:

```markdown
<!-- En SKILL.md de session-start -->

## Workflow

### Step 1: Get current status
Use the Bash tool to run:

`​`​`bash
python3 ~/.claude/plugins/squirrel/lib/status_aggregator.py \
  --vault $(cat ~/.squirrel/config.toml | grep vault_path | cut -d'"' -f2) \
  --project "$PROJECT_ARG" \
  --output json
`​`​`

The script returns a JSON. Parse it and use the fields.

### Step 2: Compose loading note from JSON
Use the `wip.projects[0]` data and `wip.projects[0].active_intent` to build the brief.
```

**Resultado**: las skills son delgadas (pocos tokens), los scripts hacen el trabajo (cero tokens del LLM).

---

## 🎁 Bonus: Helpers para el usuario

### `bin/cb` — CLI standalone

Un binario Python que expone todo sin necesitar el agente:

```bash
cb status                    # status completo
cb start TRABAJO-PROYECTO-A  # registrar inicio de sesión (sin LLM)
cb end                       # registrar fin (sin shutdown note del LLM)
cb deadlines                 # lista de deadlines
cb focus-score               # score de hoy
cb chunk --hours 8 "auth"    # chunking
cb sync-out --scope X        # genera paquete
cb sync-in --input file.md   # aplica paquete
```

Esto es **opcional pero útil**: scripts de cron pueden usarlo, o el usuario puede automatizar cosas sin abrir Claude Code.

---

## 🚦 Hitos de medición

Después de implementar, validamos que:

1. ✅ `python3 lib/status_aggregator.py --vault X` corre en <500ms para vault de 50 archivos
2. ✅ Tests pasan al 100%
3. ✅ Token consumption en `/sq-where-am-i` cae 5×+
4. ✅ Paquete sync-out con scope completo de proyecto genera <2MB
5. ✅ Hash validation rechaza modificaciones de 1 carácter
6. ✅ `chunk_helper` con 8h produce exactamente 4 sesiones según fórmula
7. ✅ `deadline_scanner` clasifica correctamente los 5 niveles

---

## 💾 Compatibilidad con v0.1.0

- Vaults existentes funcionan tal cual (sin migración requerida)
- `config.toml` v0.1.0 sigue siendo válido (campos nuevos opcionales)
- Skills v0.1.0 siguen funcionando si no se actualizan (las nuevas se suman)

---

## 🎬 Próximo paso concreto

**Construir Fase 1 ahora**: los scripts foundation con tests reales. Si esto funciona, el resto se construye sobre cimientos sólidos.

Procedemos con:
1. `lib/intent_parser.py` + tests
2. `lib/vault_io.py`
3. `lib/tag_validator.py`
4. Vault de prueba (`tests/fixtures/vault-minimal/`)
5. Validación end-to-end

Después de Fase 1 probada, seguimos con Fase 2 (`status_aggregator` — el cambio de juego).
