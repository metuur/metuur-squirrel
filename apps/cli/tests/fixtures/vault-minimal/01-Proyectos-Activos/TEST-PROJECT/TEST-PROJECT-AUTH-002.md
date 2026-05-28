---
id: TEST-PROJECT-AUTH-002
proyecto: TEST-PROJECT
estado: in-progress
prioridad: alta
creado: 2026-05-20
deadline: 2026-05-25
tags: [intent, proyecto/TEST-PROJECT, estado/wip, componente/auth]
---

# TEST-PROJECT-AUTH-002 — Validación de state CSRF

## 🎯 Intent (qué/por qué)
> Implementar validación del parámetro `state` en el OAuth callback para prevenir
> ataques CSRF.

## ✅ Definition of Done
- [x] Generar state criptográfico (32 bytes random hex)
- [x] State se guarda en sesión server-side
- [ ] Validación en `/auth/callback`
- [ ] Test unitario
- [ ] Test E2E
- [ ] Code review aprobado

## 🔨 Tareas concretas (next physical actions)
- [x] Investigar approach (crypto.randomBytes vs JWT signed state)
- [x] Implementar generación en auth.controller.ts línea 23
- [ ] Implementar validación en auth.controller.ts línea 47
- [ ] Escribir test unitario
- [ ] Escribir test E2E
- [ ] Pedir code review a @colega-senior

## 📝 Notas / Context
- Decisión: usar `crypto.randomBytes(32).toString('hex')` por simplicidad
- El state se guarda con TTL de 10 min
- Referencia: https://datatracker.ietf.org/doc/html/rfc6749#section-10.12

## 🔗 Relacionados
- **Parent**: [[TEST-PROJECT]]
- **Bloquea**: [[TEST-PROJECT-TESTING-001]]
- **Bloqueado por**: nada

## 🔄 Shutdown notes (más reciente arriba)

### 2026-05-22 17:30
- **Estado**: terminé la generación del state criptográfico. Faltan validación y tests.
- **Next physical action**: abrir auth.controller.ts línea 47 y agregar validación del state contra el guardado en sesión.
- **Hipótesis activa**: el problema con tokens duplicados que vi ayer era race condition en el middleware.
- **Bloqueado por**: nada
- **Decisiones tomadas hoy**: usar crypto.randomBytes(32) en vez de JWT signed.

### 2026-05-20 18:00
- **Estado**: arranqué con el endpoint, lectura del code funciona
- **Next physical action**: implementar generación del state criptográfico
- **Bloqueado por**: nada
