"""
Adaptador de Entrada — API REST con FastAPI.
VERSIÓN CORREGIDA — el token se lee del header Authorization correctamente.
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from techsupportpro.application.dtos import (
    RegistrarClienteDTO, LoginDTO, CrearTicketDTO, ActualizarTicketDTO,
    CalificarTicketDTO, CrearAlquilerDTO, ProcesarPagoDTO,
)

# ── Esquema Bearer ────────────────────────────────────────────────────────────
# auto_error=False para que endpoints sin token devuelvan 401 controlado
_bearer = HTTPBearer(auto_error=False)

# ── Modelos Pydantic ──────────────────────────────────────────────────────────

class RegistroRequest(BaseModel):
    nombre: str
    email: str
    password: str
    empresa: str = ""
    telefono: str = ""
    ciudad: str = "Bogotá"

class LoginRequest(BaseModel):
    email: str
    password: str

class CrearTicketRequest(BaseModel):
    tipo_servicio: str
    titulo: str
    descripcion: str
    prioridad: str = "MEDIA"
    direccion_visita: str = ""

class ActualizarTicketRequest(BaseModel):
    nuevo_estado: str
    diagnostico: Optional[str] = None
    solucion: Optional[str] = None
    costo_final: Optional[float] = None

class CalificarRequest(BaseModel):
    calificacion: float = Field(ge=1.0, le=5.0)

class CrearAlquilerRequest(BaseModel):
    equipo_tipo: str
    fecha_inicio: str
    fecha_fin: str
    costo_diario: float
    equipo_marca: str = ""
    equipo_modelo: str = ""

class PagoRequest(BaseModel):
    monto: float
    metodo: str
    ticket_id: Optional[str] = None
    alquiler_id: Optional[str] = None
    token_tarjeta: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

HTTP_CODES = {
    "EmailYaRegistrado": 409, "CredencialesInvalidas": 401,
    "TokenInvalidoOExpirado": 401, "ClienteNoEncontrado": 404,
    "TicketNoEncontrado": 404, "AlquilerNoEncontrado": 404,
    "LimiteTicketsPlanExcedido": 422, "EstadoTicketInvalido": 422,
    "AccesoNoAutorizado": 403, "PagoInvalido": 422,
}

def _extraer_token(credenciales: HTTPAuthorizationCredentials) -> str:
    """Extrae el token del header Authorization gestionado por FastAPI."""
    if not credenciales:
        raise HTTPException(401, "Token requerido. Usa el botón Authorize 🔒 en Swagger.")
    return credenciales.credentials   # FastAPI ya quitó el prefijo "Bearer "

def _run(fn, *args, **kwargs):
    import dataclasses
    try:
        result = fn(*args, **kwargs)
        return dataclasses.asdict(result) if dataclasses.is_dataclass(result) else result
    except HTTPException:
        raise
    except Exception as e:
        status = HTTP_CODES.get(type(e).__name__, 400)
        raise HTTPException(status, str(e))


# ── Router ────────────────────────────────────────────────────────────────────

def crear_router(contenedor):
    router = APIRouter(prefix="/api")

    @router.get("/health", tags=["Sistema"])
    def health():
        return {"status": "ok", "servicio": "TechSupport Pro"}

    # ── Clientes ──────────────────────────────────────────────────────────────

    @router.post("/clientes/registro", status_code=201, tags=["Clientes"])
    def registrar(req: RegistroRequest):
        return _run(contenedor.registrar_cliente.ejecutar, RegistrarClienteDTO(
            nombre=req.nombre, email=req.email, password=req.password,
            empresa=req.empresa, telefono=req.telefono, ciudad=req.ciudad,
        ))

    @router.post("/clientes/login", tags=["Clientes"])
    def login(req: LoginRequest):
        return _run(contenedor.login_cliente.ejecutar, LoginDTO(req.email, req.password))

    @router.get("/clientes/perfil", tags=["Clientes"])
    def perfil(cred: HTTPAuthorizationCredentials = Security(_bearer)):
        token = _extraer_token(cred)
        info = contenedor._tokens.verificar_token(token)
        if not info or info["tipo"] != "cliente":
            raise HTTPException(401, "Token de cliente requerido")
        c = contenedor._clientes.buscar_por_id(info["usuario_id"])
        if not c:
            raise HTTPException(404, "Cliente no encontrado")
        return {"id": c.id, "nombre": str(c.nombre), "email": str(c.email),
                "plan": c.plan.value, "empresa": c.empresa, "ciudad": c.ciudad}

    # ── Tickets ───────────────────────────────────────────────────────────────

    @router.get("/tickets", tags=["Tickets"])
    def mis_tickets(estado: Optional[str] = None,
                    cred: HTTPAuthorizationCredentials = Security(_bearer)):
        return _run(contenedor.mis_tickets.ejecutar,
                    _extraer_token(cred), estado)

    @router.post("/tickets", status_code=201, tags=["Tickets"])
    def crear_ticket(req: CrearTicketRequest,
                     cred: HTTPAuthorizationCredentials = Security(_bearer)):
        return _run(contenedor.crear_ticket.ejecutar, _extraer_token(cred),
                    CrearTicketDTO(tipo_servicio=req.tipo_servicio, titulo=req.titulo,
                                   descripcion=req.descripcion, prioridad=req.prioridad,
                                   direccion_visita=req.direccion_visita))

    @router.patch("/tickets/{ticket_id}", tags=["Tickets"])
    def actualizar_ticket(ticket_id: str, req: ActualizarTicketRequest,
                          cred: HTTPAuthorizationCredentials = Security(_bearer)):
        return _run(contenedor.actualizar_ticket.ejecutar, _extraer_token(cred),
                    ActualizarTicketDTO(ticket_id=ticket_id, nuevo_estado=req.nuevo_estado,
                                        diagnostico=req.diagnostico, solucion=req.solucion,
                                        costo_final=req.costo_final))

    @router.post("/tickets/{ticket_id}/calificar", tags=["Tickets"])
    def calificar(ticket_id: str, req: CalificarRequest,
                  cred: HTTPAuthorizationCredentials = Security(_bearer)):
        return _run(contenedor.calificar_ticket.ejecutar, _extraer_token(cred),
                    CalificarTicketDTO(ticket_id=ticket_id, nota=req.calificacion))

    # ── Alquileres ────────────────────────────────────────────────────────────

    @router.get("/alquileres", tags=["Alquileres"])
    def mis_alquileres(cred: HTTPAuthorizationCredentials = Security(_bearer)):
        """Lista alquileres del cliente autenticado. [NUEVO]"""
        token = _extraer_token(cred)
        info = contenedor._tokens.verificar_token(token)
        if not info or info["tipo"] != "cliente":
            raise HTTPException(401, "Token de cliente requerido")
        items = contenedor._alquileres.listar_por_cliente(info["usuario_id"])
        return {"total": len(items), "alquileres": [
            {"id": a.id, "equipo_tipo": a.equipo_tipo,
             "inicio": a.periodo.inicio.strftime("%Y-%m-%d"),
             "fin": a.periodo.fin.strftime("%Y-%m-%d"),
             "dias": a.periodo.dias, "costo_total": a.costo_total.pesos,
             "deposito": a.deposito.pesos, "estado": a.estado.value}
            for a in items
        ]}

    @router.post("/alquileres", status_code=201, tags=["Alquileres"])
    def crear_alquiler(req: CrearAlquilerRequest,
                       cred: HTTPAuthorizationCredentials = Security(_bearer)):
        return _run(contenedor.crear_alquiler.ejecutar, _extraer_token(cred),
                    CrearAlquilerDTO(equipo_tipo=req.equipo_tipo,
                                     fecha_inicio=req.fecha_inicio, fecha_fin=req.fecha_fin,
                                     costo_diario=req.costo_diario,
                                     equipo_marca=req.equipo_marca,
                                     equipo_modelo=req.equipo_modelo))

    @router.post("/alquileres/{alquiler_id}/devolver", tags=["Alquileres"])
    def devolver(alquiler_id: str,
                 cred: HTTPAuthorizationCredentials = Security(_bearer)):
        return _run(contenedor.devolver_alquiler.ejecutar,
                    _extraer_token(cred), alquiler_id)

    # ── Pagos ─────────────────────────────────────────────────────────────────

    @router.post("/pagos", status_code=201, tags=["Pagos"])
    def pago(req: PagoRequest,
             cred: HTTPAuthorizationCredentials = Security(_bearer)):
        return _run(contenedor.procesar_pago.ejecutar, _extraer_token(cred),
                    ProcesarPagoDTO(monto=req.monto, metodo=req.metodo,
                                    ticket_id=req.ticket_id, alquiler_id=req.alquiler_id,
                                    token_tarjeta=req.token_tarjeta))

    # ── Admin ─────────────────────────────────────────────────────────────────

    @router.get("/admin/dashboard", tags=["Admin"])
    def dashboard(cred: HTTPAuthorizationCredentials = Security(_bearer)):
        return _run(contenedor.dashboard_admin.ejecutar, _extraer_token(cred))

    @router.get("/admin/tickets", tags=["Admin"])
    def todos_tickets(estado: Optional[str] = None,
                      cred: HTTPAuthorizationCredentials = Security(_bearer)):
        """Lista TODOS los tickets del sistema. [NUEVO — solo técnicos/admins]"""
        token = _extraer_token(cred)
        info = contenedor._tokens.verificar_token(token)
        if not info or info["tipo"] != "tecnico":
            raise HTTPException(403, "Solo técnicos y admins")
        from techsupportpro.domain.entities import EstadoTicket
        todos = contenedor._tickets.listar_todos()
        if estado:
            try:
                todos = [t for t in todos if t.estado == EstadoTicket(estado.upper())]
            except ValueError:
                raise HTTPException(400, f"Estado inválido: {estado}")
        return {"total": len(todos), "tickets": [
            {"id": t.id, "numero": t.numero, "cliente_id": t.cliente_id,
             "tecnico_id": t.tecnico_id, "tipo": t.tipo_servicio.value,
             "estado": t.estado.value, "prioridad": t.prioridad.value,
             "titulo": t.titulo,
             "costo_estimado": t.costo_estimado.pesos if t.costo_estimado else None,
             "creado_en": t.creado_en.isoformat()}
            for t in sorted(todos, key=lambda x: x.creado_en, reverse=True)
        ]}

    return router
