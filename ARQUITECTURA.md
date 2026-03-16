# ARQUITECTURA — TechSupport Pro
## Sistema Hexagonal — Diagrama y Descripción Completa

---

## 1. Estructura de Capas

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CAPA DE INFRAESTRUCTURA                         │
│                                                                         │
│   DRIVING SIDE (Entrada)         NÚCLEO           DRIVEN SIDE (Salida)  │
│                                                                         │
│  ┌────────────────┐     ┌────────────────────────┐   ┌───────────────┐ │
│  │  FastAPI REST  │────►│                        │──►│  PostgreSQL   │ │
│  │  14 endpoints  │     │   CAPA DE APLICACIÓN   │   │  (SQLAlchemy) │ │
│  └────────────────┘     │                        │   └───────────────┘ │
│                         │  10 Casos de Uso       │                     │
│  ┌────────────────┐     │  14 DTOs               │   ┌───────────────┐ │
│  │   Click CLI    │────►│                        │──►│  JSON Files   │ │
│  │   7 comandos   │     │  ┌──────────────────┐  │   │  (stdlib)     │ │
│  └────────────────┘     │  │     DOMINIO       │  │   └───────────────┘ │
│                         │  │                  │  │                     │
│  ┌────────────────┐     │  │  5 Entidades     │  │   ┌───────────────┐ │
│  │  CSV Loader    │────►│  │  7 Value Objects │  │──►│  Memory Fakes │ │
│  │  (carga masiva)│     │  │  20 Excepciones  │  │   │  (tests/demo) │ │
│  └────────────────┘     │  │  4 Servicios     │  │   └───────────────┘ │
│                         │  └──────────────────┘  │                     │
│                         │                        │   ┌───────────────┐ │
│                         │  10 Puertos (ABC)       │──►│  Notificación │ │
│                         │                        │   │  (consola)    │ │
│                         └────────────────────────┘   └───────────────┘ │
│                                                                         │
│          Las dependencias de CÓDIGO siempre apuntan hacia el centro     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Estructura de Carpetas

```
fase2_hexagonal/
├── main.py                                  ← Arrancar API: uvicorn main:app --reload
├── cli.py                                   ← Arrancar CLI: python cli.py --help
├── run_tests.py                             ← Tests: python run_tests.py
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── COMPARATIVA.md
└── techsupportpro/
    │
    ├── domain/                              ← CAPA 1: CERO dependencias externas
    │   ├── entities/__init__.py             │   Cliente, Tecnico, Ticket, AlquilerEquipo, Pago
    │   ├── value_objects/__init__.py        │   Email, COP, Periodo, NombrePersona, ...
    │   ├── exceptions/__init__.py           │   20 excepciones tipadas
    │   ├── ports/__init__.py                │   10 interfaces ABC
    │   └── services/__init__.py             │   TecnicoAsignador, MetricasService, ...
    │
    ├── application/                         ← CAPA 2: solo domain + stdlib
    │   ├── dtos/__init__.py                 │   14 DTOs (7 entrada + 7 salida)
    │   └── use_cases/__init__.py            │   10 casos de uso
    │
    ├── infrastructure/                      ← CAPA 3: librerías externas permitidas aquí
    │   ├── adapters_out/
    │   │   ├── memory/__init__.py           │   10 Fakes en RAM (tests + demos)
    │   │   ├── postgres/__init__.py         │   SQLAlchemy 2.0 — 12 clases ORM + repos
    │   │   ├── postgres/db.py               │   Engine + Session SQLAlchemy
    │   │   └── json_file/__init__.py        │   JSON en disco — segundo adaptador
    │   └── adapters_in/
    │       ├── api_rest/__init__.py          │   FastAPI — 14 endpoints
    │       └── cli/__init__.py              │   Click — 7 comandos + carga CSV
    │
    ├── config/__init__.py                   ← ÚNICO lugar que conoce adaptadores concretos
    │
    └── tests/
        ├── unit/use_cases/
        │   └── test_use_cases.py            ← 37 tests unitarios (MagicMock)
        └── integration/
            └── test_integracion.py          ← 10 tests integración (Fakes reales)
```

---

## 3. Catálogo de Puertos

| Puerto | Tipo | Adaptadores que lo implementan |
|--------|------|-------------------------------|
| IClienteRepository | Salida | Memory, Postgres, JSON |
| ITecnicoRepository | Salida | Memory, Postgres, JSON |
| ITicketRepository | Salida | Memory, Postgres, JSON |
| IAlquilerRepository | Salida | Memory, Postgres, JSON |
| IPagoRepository | Salida | Memory, Postgres, JSON |
| IAuditoriaRepository | Salida | Memory, Postgres, JSON |
| INotificacionService | Salida | Memory (consola) |
| IPagoGateway | Salida | Memory (simulado Wompi) |
| ITokenService | Salida | Memory (prefijo simple) |
| IPasswordService | Salida | Memory (hash simulado) |

---

## 4. Modos de Ejecución

```bash
# Modo memoria (sin instalaciones — para tests y demos)
MODO_REPO=memoria uvicorn main:app --reload

# Modo PostgreSQL (con Docker)
docker-compose up postgres -d
MODO_REPO=postgres uvicorn main:app --reload

# Modo JSON (archivos en disco)
MODO_REPO=json JSON_DATA_DIR=./data uvicorn main:app --reload
```

---

## 5. Regla de Dependencia — Verificación

Ejecutar para verificar que el dominio no tiene imports prohibidos:

```bash
python3 -c "
import ast, os, sys
prohibidos = ['fastapi', 'sqlalchemy', 'click', 'requests', 'pydantic']
carpeta = 'techsupportpro/domain'
for root, dirs, files in os.walk(carpeta):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    nombres = [a.name for a in getattr(node, 'names', [])]
                    modulo = getattr(node, 'module', '') or ''
                    todos = nombres + [modulo]
                    for p in prohibidos:
                        if any(p in n for n in todos):
                            print(f'VIOLACIÓN: {path} importa {p}')
                            sys.exit(1)
print('✅ Dominio puro — 0 violaciones')
"
```

---

*TechSupport Pro — Ingeniería de Software II — 2026*
