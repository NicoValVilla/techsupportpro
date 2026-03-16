# COMPARATIVA — Monolito vs. Arquitectura Hexagonal
## TechSupport Pro — Ingeniería de Software II — 2026

---

## 1. Líneas de Código por Módulo

| Módulo | Monolito (main.py) | Hexagonal | Observación |
|--------|-------------------|-----------|-------------|
| Lógica de negocio | ~420 líneas mezcladas | 567 (entities) + 236 (VOs) + 171 (exceptions) = 974 | Separado y expresivo |
| Puertos / interfaces | 0 | 340 (ports) | No existían |
| Servicios de dominio | 0 | 128 (services) | No existían |
| Casos de uso | 0 (mezclados con HTTP) | 410 (use_cases) | Separados y testeables |
| DTOs | 0 (Pydantic en controladores) | 298 (dtos) | Tipados y validados |
| Adaptador Postgres | ~380 (mezclado con todo) | 421 (adapters_out/postgres) | Aislado |
| Adaptador Memoria | 0 | 354 (adapters_out/memory) | Nuevo — habilita tests |
| Adaptador JSON | 0 | 378 (adapters_out/json_file) | Nuevo — segundo repo |
| API REST | ~480 (mezclada con lógica) | 235 (adapters_in/api_rest) | Solo traducción HTTP |
| CLI | 0 | 222 (adapters_in/cli) | Nuevo canal de entrada |
| Contenedor DI | 0 | 193 (config) | Nuevo — único punto concreto |
| **TOTAL** | **1.263** | **~3.200** | Más expresivo y modular |

---

## 2. Tiempo de Ejecución de Tests

| Métrica | Monolito | Hexagonal | Mejora |
|---------|----------|-----------|--------|
| Setup del entorno | ~3 min (Docker + DB) | 0 segundos | ∞ |
| Tests unitarios (37) | Imposible sin DB | 48ms | ∞ |
| Tests integración (10) | Imposible sin DB | 44ms | ∞ |
| Suite completa (47) | N/A | **102ms** | ∞ |
| Tests del dominio (69) | Imposible | 8ms | ∞ |

---

## 3. Número de Archivos a Modificar por Tipo de Cambio

| Cambio | Monolito | Hexagonal |
|--------|----------|-----------|
| Cambiar límite plan básico (2→3 tickets) | 1 archivo, 3 lugares | 1 archivo, 1 línea |
| Migrar PostgreSQL → MongoDB | Todo el sistema | 1 archivo nuevo |
| Agregar canal CLI | Imposible sin refactorizar | 1 archivo nuevo |
| Cambiar proveedor de emails | Buscar en main.py | 1 archivo nuevo |
| Agregar nuevo tipo de servicio | 5+ lugares | 1 enum + 1 dict |
| Agregar campo a entidad Cliente | 4+ lugares | entidad + adaptadores |

---

## 4. Dependencias por Capa (Verificadas con análisis de imports)

| Capa | Imports externos | Estado |
|------|-----------------|--------|
| domain/entities | Solo stdlib Python | ✅ Puro |
| domain/value_objects | Solo stdlib Python | ✅ Puro |
| domain/exceptions | Solo stdlib Python | ✅ Puro |
| domain/ports | Solo stdlib + domain | ✅ Puro |
| domain/services | Solo stdlib + domain | ✅ Puro |
| application/use_cases | Solo domain + application | ✅ Puro |
| application/dtos | Solo stdlib + domain | ✅ Puro |
| infrastructure/adapters_out/memory | Solo domain | ✅ Correcto |
| infrastructure/adapters_out/postgres | SQLAlchemy + domain | ✅ Correcto |
| infrastructure/adapters_out/json_file | json stdlib + domain | ✅ Correcto |
| infrastructure/adapters_in/api_rest | FastAPI + application | ✅ Correcto |
| infrastructure/adapters_in/cli | Click + application | ✅ Correcto |
| config | Todos (único punto) | ✅ Intencional |

---

## 5. Violaciones Arquitectónicas

| Categoría | Monolito | Hexagonal |
|-----------|----------|-----------|
| Lógica de negocio en controlador | 18 | 0 |
| Acceso directo a DB en controlador | 14 | 0 |
| Sin separación de capas | 12 | 0 |
| Dependencias circulares | 9 | 0 |
| Sin interfaces abstractas | 8 | 0 |
| Validaciones dispersas | 11 | 0 |
| Sin excepciones tipadas | 7 | 0 |
| Constantes mágicas | 4 | 0 |
| Sin pruebas unitarias | 2 | 0 |
| **TOTAL** | **85** | **0** |

---

## 6. Historial de Commits por Fase

```
Fase 1: feat: monolito original con 10 endpoints
Fase 2: feat: dominio hexagonal — entidades, VOs, puertos, servicios (69 tests)
Fase 3: feat: capa de aplicación — 10 casos de uso, 14 DTOs (37 tests)
Fase 4a: feat: adaptadores de salida — memory, postgres, json + contenedor DI
Fase 4b: feat: adaptadores de entrada — FastAPI (14 endpoints) + CLI (7 comandos)
Fase 4c: test: 10 tests de integración con Fakes reales
Fase 5: docs: informe técnico, COMPARATIVA, ARQUITECTURA, presentación
```

---

*Última actualización: 2026 — TechSupport Pro — Ingeniería de Software II*
