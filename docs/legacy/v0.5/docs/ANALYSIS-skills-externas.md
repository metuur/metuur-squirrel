# 🔍 Análisis: Qué tomar de las skills externas

> Revisión crítica de las 7 skills ADHD externas y qué incorporar a `squirrel`.

---

## 📊 Evaluación skill por skill

### 1. `hyperfocus-management.md` ⭐⭐⭐⭐ INCORPORAR (adaptado)

**Lo valioso:**
- **Detección de hyperfocus** vía actividad continua (commits, edits) — encaja perfecto con nuestros hooks
- **Reglas de intervención escalonadas** (6h gentle / 10h firm) — ADHD-aware
- **Recovery time** post-hyperfocus (2-3h baja productividad) — útil para planning

**Lo que NO sirve tal cual:**
- Asume "PM externo" que monitorea al ingeniero — nosotros NO tenemos un PM, somos el usuario
- Usa Slack DM — irrelevante para nuestro flujo local

**Adaptación a squirrel:**
→ **Skill nueva**: `hyperfocus-guardian` que detecta sesión continua >2h y propone (no impone) check-ins. Lo dispara un **hook ejecutado por script** (no por LLM) que monitorea el state.json y emite recordatorios baratos.

---

### 2. `context-switching.md` ⭐⭐⭐⭐⭐ INCORPORAR (datos clave)

**Lo valioso:**
- **El "ADHD Context-Switching Tax"** cuantificado (30-45 min por switch vs 15 min neurotípico) — este dato debe estar EN las skills nuestras como justificación de las reglas
- **Switch budget diario** (max 2 voluntarios) — concepto excelente, ya tenemos algo similar pero menos explícito
- **Free blocks calendar API** — útil para script de planning
- **Tracking de switches** con focus_score — perfecto para `/sq-status`

**Lo que NO sirve tal cual:**
- El código Python es decente pero no integra con nuestro vault de Markdown
- No usa nuestros tags semánticos

**Adaptación:**
→ **Script nuevo**: `lib/switch_tracker.py` que registra context switches en `<vault>/.squirrel/switches.jsonl` y calcula focus_score diario. **Lo invocan los hooks** cuando detectan `/sq-start` con un proyecto distinto al activo.
→ **Datos en SKILL.md de session-start**: mencionar el 30-45 min como justificación de por qué el loading note ahorra tiempo.

---

### 3. `parakeet-reminders.md` ⭐⭐⭐⭐ INCORPORAR (la filosofía + escalado)

**Lo valioso:**
- **Filosofía "parakeet"**: friendly, non-judgmental, escalating — tono perfecto para ADHD
- **5 niveles de urgencia** (FYI / Upcoming / Soon / Urgent / Critical) con frecuencias específicas — sistema concreto, no vague
- **Frequency map** según urgencia — evita el "nag" sin perder el recordatorio

**Lo que NO sirve tal cual:**
- Asume Slack DM externo
- No conecta a deadlines del vault

**Adaptación:**
→ **Skill nueva**: `parakeet` que lee deadlines de los intents y los muestra en `/sq-status` y `/sq-where-am-i` con tono apropiado al urgency level.
→ **Script nuevo**: `lib/deadline_scanner.py` escanea frontmatter `deadline:` de todos los intents, calcula días restantes, devuelve JSON con urgencias. El skill lo consume — barato.

---

### 4. `task-chunking.md` ⭐⭐⭐ INCORPORAR (parcial)

**Lo valioso:**
- **Chunks <60 min** con criterios claros — alineado con lo que ya tenemos
- **Fases de proyecto con %** (Research 15% / Setup 20% / Core 40% / Polish 15% / Test 10%) — útil como template
- **Dopamine reward emoji** por chunk completado — refuerzo positivo barato

**Lo que NO sirve tal cual:**
- El chunker automático es algo simplista (asume distribución uniforme)
- Tiempos estimados sin ajuste por usuario

**Adaptación:**
→ **Skill nueva**: `chunk-intent` que toma un intent grande y lo descompone usando el template de fases. **El LLM lo hace** porque requiere entender el dominio, pero usando un script que sugiere la estructura.
→ **Script nuevo**: `lib/chunk_helper.py` solo da la **estructura de fases con %** según horas estimadas. El LLM completa los nombres específicos.

---

### 5. `dopamine-menu.md` ⭐⭐⭐ INCORPORAR (estructura)

**Lo valioso:**
- **Menú estructurado por nivel de esfuerzo** (Appetizers / Starters / Mains / Desserts) — ya tenemos algo similar en el vault
- **Temptation Bundling** — concepto bueno, no estaba en lo nuestro
- **Dopamine Activity Log** — útil para weekly review
- **Emergency Dopamine Protocol** — script-able

**Lo que NO sirve tal cual:**
- Muy largo, mucho contenido es educacional (no operacional)
- Las activities son del autor, no del usuario

**Adaptación:**
→ Ya tenemos `Dopamine-Menu.md` en el vault TDAH. Lo **fortalecemos** con Temptation Bundling y Activity Log, pero NO es parte del plugin — vive en el vault.
→ **Skill nueva (opcional)**: `dopamine-suggest` para sugerir actividad apropiada según contexto (post-sesión larga / pre-tarea aburrida / break entre Pomodoros). Esto sí es del plugin.

---

### 6. `executive-function-toolkit.md` ⭐⭐⭐⭐⭐ INCORPORAR (templates + protocolos)

**Lo valioso:**
- **2-Minute Start Protocol** — antídoto al freeze, accionable
- **5-4-3-2-1 Launch** — script-able como prompt del skill
- **If-Then Implementation** — sistema concreto
- **Time Estimation Worksheet** con multiplicadores (×2-×3) — DATO CRÍTICO para ADHD
- **The One-Touch Rule**, **Launch Pad**, **STOP Technique**, **Frustration Scripts**
- **Minimum Viable Day** — protocolo crisis
- **Crisis Protocols**

**Lo que NO sirve tal cual:**
- Es muy completo (~500 líneas) — no debe ser una sola skill
- Mucho es del vault, no del plugin

**Adaptación:**
→ Fortalecemos `Protocolos-de-Emergencia.md` del vault con: Minimum Viable Day, STOP, 5-4-3-2-1
→ **Skill nueva**: `task-initiation` que detecta cuando el usuario está atascado iniciando una tarea (lenguaje: "no puedo arrancar", "estoy bloqueado", "no sé por dónde empezar") y aplica los protocolos (2-minute start, smallest action, body double).
→ **Script nuevo**: `lib/estimate_buffer.py` que toma una estimación del usuario y aplica los multiplicadores ADHD. Súper barato.

---

### 7. `patterns-and-components.md` ⭐⭐ NO INCORPORAR (mostly)

**Por qué casi nada sirve:**
- Es código SwiftUI para apps móviles — fuera del scope
- Los "patterns" son sobre UX de apps, no sobre flujo del usuario
- Lo único valioso es el **Rejection Sensitivity Shield** (wording sin shame) — ya está en nuestro tono

**Adaptación:**
→ Skip. Tomamos solo el principio de "wording sin shame" que ya está implícito en nuestras skills.

---

### 8. `SKILL.md` (project-management-guru-adhd) ⭐⭐⭐ ÚTIL COMO GUÍA

**Lo valioso:**
- **Estructura de skill** bien organizada
- **When to use / NOT to use** explícito
- **Anti-patterns** sección — agregamos esta sección a nuestras skills
- **References académicas** (Barkley, Hallowell, Ratey, Leroy, Mark, Ashinoff)

**Lo que NO sirve tal cual:**
- Asume rol de "manager" — nosotros somos el usuario, no un manager
- Activación es vague ("ADHD project management") — la nuestra debe ser más específica

**Adaptación:**
→ Agregar sección **"Anti-patterns"** a nuestras skills críticas (session-start, session-end, brief)
→ Agregar **References académicas** en SKILL.md cuando aplique (le da seriedad y autoridad)
→ Adoptar el formato `metadata: category / pairs-with / tags`

---

## 🎯 Resumen: Qué se agrega al plugin

### Nuevas skills (4)
1. **`hyperfocus-guardian`** — detecta sesiones largas y propone check-ins escalados
2. **`parakeet`** — recordatorios de deadlines con tono según urgencia
3. **`task-initiation`** — antídotos a la parálisis de inicio
4. **`chunk-intent`** — descomposición de intents grandes en chunks ADHD-friendly

### Nuevos scripts auxiliares (5)
1. **`lib/deadline_scanner.py`** — escanea frontmatter de todos los intents, calcula urgencias
2. **`lib/switch_tracker.py`** — registra context switches, calcula focus_score
3. **`lib/chunk_helper.py`** — sugiere estructura de fases para chunking
4. **`lib/estimate_buffer.py`** — aplica multiplicadores ADHD a estimaciones
5. **`lib/activity_monitor.py`** — daemon ligero que detecta hyperfocus vía commits/edits

### Mejoras a skills existentes
- `session-start`: agregar focus_score y switch budget restante del día
- `session-end`: tomar tiempo trabajado y log al switch tracker
- `brief`: incluir urgencias de deadlines (parakeet integration)
- `where-am-i`: detectar proyectos sin actividad >3 días y otros patrones

### Mejoras a SKILL.md
- Agregar `metadata` con category/pairs-with/tags (formato estándar)
- Sección "Anti-patterns" donde corresponda
- References académicas

---

## 🧠 Filosofía clave de diseño

> **Scripts hacen lo determinístico. LLM solo hace lo que requiere juicio.**

| Tarea | ¿Quién la hace? | Por qué |
|---|---|---|
| Calcular días hasta deadline | Script | Pura aritmética |
| Decidir nivel de urgencia | Script | Reglas claras |
| Buscar intents activos en vault | Script | Glob + parse YAML |
| Escribir mensaje "parakeet" con tono apropiado | LLM | Requiere natural language |
| Generar shutdown note de una conversación | LLM | Requiere entender contexto |
| Aplicar paquete sync-in al vault | Script | I/O determinístico |
| Validar hash SHA-256 | Script | Crypto, no necesita LLM |
| Sugerir cuál intent priorizar | LLM | Requiere juicio multifactor |
| Chunk un intent grande en sub-tareas | LLM (con script de fases) | Necesita entender el dominio |
| Detectar hyperfocus (>2h continuas) | Script | Comparación de timestamps |
| Decidir "¿interrumpo o no?" | Script + reglas | Reglas claras (deadline cerca, etc.) |

**Ahorro estimado de tokens:**
- Sin scripts: cada `/sq-status` corre ~3000 tokens leyendo todos los intents
- Con scripts: el script devuelve JSON estructurado, el LLM solo formatea ~500 tokens
- **6× ahorro** en operaciones recurrentes

---

## 📋 Lo que NO se agrega (decisiones explícitas)

- ❌ **Gamification compleja** (streaks, levels, badges) — agrega complejidad sin valor proporcional
- ❌ **SwiftUI components** — fuera del scope del plugin
- ❌ **Auto-sync con Slack** — viola el principio de air-gap
- ❌ **Medication tracking** — fuera del scope (es vault content, no skill)
- ❌ **Body doubling digital** — interesante pero requiere infra externa
- ❌ **Confetti animations** — visual chrome sin valor en CLI

---

## 🔄 Próximo paso

Después de este análisis, voy a:
1. Crear el plan detallado de construcción del plugin v0.2.0
2. Especificar cada script auxiliar con su input/output exacto
3. Especificar cada skill nueva con triggers, workflow, anti-patterns
4. Definir el orden de implementación (fase 1 / 2 / 3)
5. Construir un primer set de scripts probados end-to-end
