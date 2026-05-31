# Ejemplo: Paquete completo personal → trabajo

## Contexto del ejemplo
- En la PC personal investigaste 3 librerías de auth para `TRABAJO-PROYECTO-A`
- Generaste tabla comparativa y tomaste una decisión preliminar
- Ahora querés llevarte la investigación + decisión al trabajo

## Comando ejecutado en personal
```
/cb-sync-out --scope=TRABAJO-PROYECTO-A:research --scope=TRABAJO-PROYECTO-A:decisions
```

## Resultado (este es el bloque que copiás al email/clipboard)

```
<!-- CONTEXT-BRIDGE-PACKAGE v1 -->
<!--
  from: personal
  to: work
  generated_at: 2026-05-23T19:30:00Z
  generated_by: claude-code@home-mbp
  scope: TRABAJO-PROYECTO-A:research,TRABAJO-PROYECTO-A:decisions
  files_count: 2
  hash_sha256: a3f5b8c9d1e2f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9
  intent: research-results-for-work-auth-decision
  receiver_instructions: apply-with-sync-in
-->

# 📦 Context Bridge Package

**De**: personal  →  **Para**: work
**Generado**: 23 mayo 2026, 19:30 (local)
**Scope**: TRABAJO-PROYECTO-A:research, TRABAJO-PROYECTO-A:decisions
**Archivos**: 2

> 📋 Para aplicar: en el otro entorno, abrí Claude Code / Codex y pegá ESTE bloque completo
> en el chat. El skill `context-bridge:sync-in` lo procesará automáticamente.

---

## 📑 Resumen del paquete

- `01-Proyectos-Activos/TRABAJO-PROYECTO-A/TRABAJO-PROYECTO-A-RESEARCH-001.md` — create — Comparación Auth.js vs Clerk vs Lucia
- `01-Proyectos-Activos/TRABAJO-PROYECTO-A/TRABAJO-PROYECTO-A-DECISION-001.md` — create — Decisión preliminar: Auth.js v5

---

## 📂 Archivos a aplicar

### Archivo 1: 01-Proyectos-Activos/TRABAJO-PROYECTO-A/TRABAJO-PROYECTO-A-RESEARCH-001.md

**Operación**: create
**Tag**: `TRABAJO-PROYECTO-A-RESEARCH-001`
**Conflicto si existe**: ask

` ` `markdown
---
id: TRABAJO-PROYECTO-A-RESEARCH-001
proyecto: TRABAJO-PROYECTO-A
tipo: research
estado: done
creado: 2026-05-23
imported_from: personal
tags: [research, proyecto/TRABAJO-PROYECTO-A]
---

# TRABAJO-PROYECTO-A-RESEARCH-001 — Comparación de librerías de auth

## Contexto
Necesitamos elegir librería de auth para el feature OAuth+JWT del proyecto.
Candidatos: Auth.js (NextAuth), Clerk, Lucia.

## Hallazgos

| Criterio | Auth.js v5 | Clerk | Lucia |
|---|---|---|---|
| Costo | Free (self-hosted) | Free tier limitado, $25/mo | Free (self-hosted) |
| Madurez | Alta | Muy alta | Media |
| Customización | Alta | Media | Muy alta |
| OAuth providers | 80+ built-in | 30+ built-in | DIY |
| Mobile SDK | No nativo | Sí, oficial | DIY |
| Vendor lock-in | Bajo | Alto | Ninguno |
| Tiempo de setup | 1-2 días | <1 día | 3-5 días |
| Bundle size | Medio | Grande | Pequeño |

## Recomendación
**Auth.js v5** es el balance óptimo para nuestro caso:
- Free, self-hosted, sin vendor lock-in
- Madurez suficiente (v5 es estable desde 2024)
- 80+ providers (Google ya implementado built-in)
- Comunidad activa
- Aplicable a nuestro stack Next.js 14

Clerk es atractivo por su DX pero el lock-in y el costo a escala lo descartan.
Lucia es más flexible pero requiere demasiado código boilerplate para nuestro timeline.

## Referencias
- https://authjs.dev/getting-started/installation
- https://clerk.com/pricing
- https://lucia-auth.com/
- Discussion: https://github.com/nextauthjs/next-auth/discussions/...

## Source
- Session: 2026-05-23 19:00-19:30 (personal)
- Agent: claude-code
- Triggered by: research request before work decision
` ` `

---

### Archivo 2: 01-Proyectos-Activos/TRABAJO-PROYECTO-A/TRABAJO-PROYECTO-A-DECISION-001.md

**Operación**: create
**Tag**: `TRABAJO-PROYECTO-A-DECISION-001`
**Conflicto si existe**: ask

` ` `markdown
---
id: TRABAJO-PROYECTO-A-DECISION-001
proyecto: TRABAJO-PROYECTO-A
tipo: decision
estado: proposed
creado: 2026-05-23
revisado: 2026-05-23
imported_from: personal
tags: [decision, proyecto/TRABAJO-PROYECTO-A]
stakeholders: [arquitecto, lead, PM-Sarah]
---

# TRABAJO-PROYECTO-A-DECISION-001 — Usar Auth.js v5 para auth

## 📌 Estado
proposed (revisar con @arquitecto en el trabajo antes de aceptar)

## 🎯 Decisión
Usar **Auth.js v5** (anteriormente NextAuth) como librería de autenticación
para el proyecto, con OAuth de Google como provider principal.

## 🌐 Contexto
Ver [[TRABAJO-PROYECTO-A-RESEARCH-001]] para el análisis comparativo completo.

Restricciones del proyecto:
- Stack: Next.js 14, Node 20, Postgres
- Deadline: 15-jun-2026
- Equipo: 3 personas, sin experiencia profunda en auth
- Mobile: necesitamos soporte para app mobile (futuro)

## 🤔 Alternativas consideradas

### Opción A: Clerk ← descartado
- ✅ Pros: DX excelente, mobile SDK oficial, setup en <1 día
- ❌ Cons: vendor lock-in alto, $25/mo a escala, dependencia externa para auth
- ⚖️ Veredicto: rechazado por lock-in y costo a futuro

### Opción B: Lucia ← descartado
- ✅ Pros: máxima flexibilidad, bundle pequeño, sin lock-in
- ❌ Cons: requiere mucho boilerplate, mobile DIY, timeline ajustado
- ⚖️ Veredicto: rechazado por costo de implementación vs deadline

### Opción C: Auth.js v5 ← ELEGIDA
- ✅ Pros: free, self-hosted, 80+ providers, madurez probada, comunidad activa
- ❌ Cons: mobile no nativo (workaround con tokens REST), bundle medio
- ⚖️ Veredicto: mejor balance costo/beneficio para nuestro caso

## 📊 Consecuencias

### Positivas
- Sin costos de licencia
- Sin vendor lock-in
- Google OAuth built-in (un import)
- Curva de aprendizaje del equipo manejable

### Negativas / costos
- Self-hosting de auth implica responsabilidad de seguridad
- Para mobile vamos a necesitar implementar custom REST endpoints
- Requiere config de NextAuth.config.ts no trivial

### Compromisos a futuro
- Estamos atados a la arquitectura de NextAuth (cambiar costaría)
- Migración futura a Clerk/Auth0 sería costosa (re-implementar flow)

## 🔗 Relacionados
- Parent project: [[TRABAJO-PROYECTO-A]]
- Intents afectados: [[TRABAJO-PROYECTO-A-AUTH-001]], [[TRABAJO-PROYECTO-A-AUTH-002]]
- Research: [[TRABAJO-PROYECTO-A-RESEARCH-001]]

## 📚 Referencias
- https://authjs.dev/
- Internal discussion (a confirmar con @arquitecto)

## 🗒️ Notas de discusión
Investigación hecha desde casa porque en el trabajo no puedo instalar las 3
librerías para evaluarlas. Decisión preliminar — necesita validación con
@arquitecto antes de marcar como `accepted`.

Acción al volver al trabajo:
1. Aplicar este paquete con `/cb-sync-in`
2. Hacer brief con `/cb-brief TRABAJO-PROYECTO-A`
3. Enviar a @arquitecto el research + la propuesta
4. Si aprueba: cambiar estado a `accepted` y empezar implementación
` ` `

---

<!-- END-CONTEXT-BRIDGE-PACKAGE -->
```

## En el trabajo (al día siguiente)

1. Abrís email
2. Copiás el bloque completo (desde `<!-- CONTEXT-BRIDGE-PACKAGE` hasta `END-CONTEXT-BRIDGE-PACKAGE -->`)
3. Pegás en el chat de Claude Code / Codex

## Lo que pasa automáticamente

El hook `UserPromptSubmit` detecta el marker y dispara el skill `sync-in`:

```
📦 Paquete detectado.

De: personal  →  Para: work
Generado: 2026-05-23 19:30
Hash: ✓ válido
Files: 2

📋 Plan de aplicación:

| # | Operación | Archivo | Estado local |
|---|-----------|---------|--------------|
| 1 | CREATE    | TRABAJO-PROYECTO-A-RESEARCH-001.md | no existe ✓ |
| 2 | CREATE    | TRABAJO-PROYECTO-A-DECISION-001.md  | no existe ✓ |

¿Aplico? (sí / selectivo / cancelar)
```

Vos respondés "sí", y:

```
✅ Aplicado:
  • Created: TRABAJO-PROYECTO-A-RESEARCH-001.md
  • Created: TRABAJO-PROYECTO-A-DECISION-001.md

🔗 Sugerencia: linkear estos archivos desde TRABAJO-PROYECTO-A.md:
  - Agregar bajo "Componentes e Intents": [[TRABAJO-PROYECTO-A-RESEARCH-001]]
  - Agregar bajo "Decisiones": [[TRABAJO-PROYECTO-A-DECISION-001]]

¿Aplico los links?
```

"sí" → los links se agregan.

```
Log: ~/work-vault/.context-bridge/applied/2026-05-24T08-15-00Z-a3f5b8c9.json

Sugerencia: corré /cb-brief TRABAJO-PROYECTO-A para ver el estado actualizado
con la nueva investigación y decisión.
```

## Total tiempo invertido

- En personal: 30 min research + 1 min `/cb-sync-out` + 30 seg copiar al email = ~32 min
- Tránsito (email): 0 segundos de tu atención
- En trabajo: 30 seg pegar + 5 seg confirmar = ~1 min

**Beneficio**: investigación completa, estructurada, trazable, sin compartir nada automáticamente, con audit log de qué entró al entorno corporativo.
