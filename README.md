# TechSupport Pro — Arquitectura Hexagonal

Sistema de soporte técnico B2B refactorizado de monolito a **Arquitectura Hexagonal (Ports & Adapters)**.

**Asignatura:** Ingeniería de Software II  
**Docente:** Ing. Germán González Rozo  

---

## Ejecución rápida (sin instalaciones)

```bash
# 1. Ejecutar todos los tests — no requiere PostgreSQL ni nada instalado
python run_tests.py

# Resultado esperado:
# ✅ TODOS LOS TESTS PASAN
# Ejecutados: 47 | Errores: 0 | Fallos: 0
```

## Ejecución de la API REST

```bash
pip install -r requirements.txt

# Modo memoria (sin DB)
MODO_REPO=memoria uvicorn main:app --reload
# → http://localhost:8000/docs

# Modo PostgreSQL
docker-compose up postgres -d
MODO_REPO=postgres uvicorn main:app --reload

# Modo JSON (archivos en disco)
MODO_REPO=json uvicorn main:app --reload
```

## CLI

```bash
python cli.py --help
python cli.py registrar
python cli.py login
python cli.py tickets
python cli.py crear
python cli.py cargar-csv clientes.csv   # carga masiva
```

## Estructura del proyecto

Ver [ARQUITECTURA.md](ARQUITECTURA.md) para el diagrama completo.

## Comparativa monolito vs hexagonal

Ver [COMPARATIVA.md](COMPARATIVA.md) para métricas detalladas.

---

**Prueba de pureza arquitectónica del dominio:**

```bash
python3 -c "
import ast, os, sys
prohibidos = ['fastapi','sqlalchemy','click','requests','pydantic']
for root,_,files in os.walk('techsupportpro/domain'):
    for f in files:
        if not f.endswith('.py'): continue
        for node in ast.walk(ast.parse(open(os.path.join(root,f)).read())):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                modulo=(getattr(node,'module','') or '')
                for p in prohibidos:
                    if p in modulo: print(f'VIOLACION: {root}/{f} -> {p}'); sys.exit(1)
print('✅ Dominio puro — 0 violaciones')
"
```
