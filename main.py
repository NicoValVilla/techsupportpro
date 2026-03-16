"""
Punto de entrada — TechSupport Pro API REST.

Modos de ejecución:
    MODO_REPO=memoria  uvicorn main:app --reload          (sin DB)
    MODO_REPO=postgres uvicorn main:app --reload          (con PostgreSQL)
    MODO_REPO=json     uvicorn main:app --reload          (con archivos JSON)
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from techsupportpro.config import Contenedor
from techsupportpro.infrastructure.adapters_in.api_rest import crear_router

# Esquema de seguridad — le dice a Swagger que use Bearer token
bearer_scheme = HTTPBearer(auto_error=False)

# Ensamblar aplicación
_contenedor = Contenedor.crear()

app = FastAPI(
    title="TechSupport Pro API",
    description="""
API REST del sistema TechSupport Pro.
Arquitectura Hexagonal — Ingeniería de Software II.

## Cómo autenticarse

1. Llama a `POST /api/clientes/registro` para crear una cuenta
2. Llama a `POST /api/clientes/login` y copia el valor del campo **token**
3. Haz clic en el botón **Authorize** 🔒 arriba a la derecha
4. En el campo escribe el token exactamente así: `Bearer cliente:abc123...`
5. Clic en **Authorize** → **Close**
6. Ahora todos los endpoints funcionan con tu sesión

**Modos de repositorio:** memoria · postgres · json
    """,
    version="4.0.0",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(crear_router(_contenedor))


@app.get("/", include_in_schema=False)
def raiz():
    return {
        "mensaje": "TechSupport Pro API",
        "docs": "/docs",
        "modo_repo": os.getenv("MODO_REPO", "memoria"),
        "version": "4.0.0",
    }
@app.post("/dev/seed", include_in_schema=True, tags=["Dev"])
def seed():
    """Crea un técnico de prueba. Solo para demos en modo memoria."""
    from techsupportpro.domain.entities import Tecnico, RolTecnico, TipoServicio
    from techsupportpro.domain.value_objects import Email, PasswordHash, NombrePersona

    tecnico = Tecnico.crear(
        nombre=NombrePersona("Ana García"),
        email=Email("ana@techsupport.com"),
        password_hash=PasswordHash("s:TechPro123"),
        rol=RolTecnico.ADMIN,
        especialidades=[TipoServicio.SOPORTE_REMOTO, TipoServicio.REPARACION_PC],
    )
    tecnico.disponible = True
    _contenedor._tecnicos.guardar(tecnico)

    token = f"tecnico:{tecnico.id}"
    return {
        "mensaje": "Técnico admin creado",
        "email": "ana@techsupport.com",
        "token": token,
        "instruccion": f"Usa este token en Authorize: {token}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
