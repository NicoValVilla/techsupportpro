"""
DTOs (Data Transfer Objects) de la capa de aplicación.

Los DTOs son objetos simples que transportan datos entre la capa de
aplicación y el mundo exterior (HTTP, CLI, tests).

Regla: los DTOs no contienen lógica de negocio.
La validación de formato básico (campos vacíos, tipos) sí puede vivir aquí.
Las reglas de negocio viven en las entidades y value objects del dominio.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


# ================================================================
# DTOs DE ENTRADA — CLIENTE
# ================================================================
@dataclass
class RegistrarClienteDTO:
    nombre:   str
    email:    str
    password: str
    empresa:  str = ""
    telefono: str = ""
    ciudad:   str = "Bogotá"

    def __post_init__(self):
        if not self.nombre.strip():
            raise ValueError("El nombre es requerido")
        if not self.email.strip():
            raise ValueError("El email es requerido")
        if not self.password:
            raise ValueError("La contraseña es requerida")


@dataclass
class LoginDTO:
    email:    str
    password: str

    def __post_init__(self):
        if not self.email.strip():
            raise ValueError("El email es requerido")
        if not self.password:
            raise ValueError("La contraseña es requerida")


# ================================================================
# DTOs DE SALIDA — CLIENTE
# ================================================================
@dataclass
class ClienteResumenDTO:
    id:              str
    nombre:          str
    email:           str
    plan:            str
    verificado:      bool
    empresa:         str
    ciudad:          str
    codigo_cliente:  str
    creado_en:       str

    @classmethod
    def desde_entidad(cls, cliente) -> "ClienteResumenDTO":
        return cls(
            id=cliente.id,
            nombre=str(cliente.nombre),
            email=str(cliente.email),
            plan=cliente.plan.value,
            verificado=cliente.verificado,
            empresa=cliente.empresa,
            ciudad=cliente.ciudad,
            codigo_cliente=cliente.codigo_cliente(),
            creado_en=cliente.creado_en.isoformat(),
        )


@dataclass
class LoginRespuestaDTO:
    token:      str
    cliente_id: str
    nombre:     str
    plan:       str
    expira_en:  str


# ================================================================
# DTOs DE ENTRADA — TICKET
# ================================================================
@dataclass
class CrearTicketDTO:
    tipo_servicio:    str
    titulo:           str
    descripcion:      str
    prioridad:        str = "MEDIA"
    direccion_visita: str = ""
    fecha_programada: str = ""

    def __post_init__(self):
        if not self.tipo_servicio.strip():
            raise ValueError("El tipo de servicio es requerido")
        if not self.titulo.strip():
            raise ValueError("El título es requerido")
        if not self.descripcion.strip():
            raise ValueError("La descripción es requerida")


@dataclass
class ActualizarTicketDTO:
    ticket_id:    str
    nuevo_estado: Optional[str] = None
    diagnostico:  Optional[str] = None
    solucion:     Optional[str] = None
    costo_final:  Optional[float] = None

    def __post_init__(self):
        if not self.ticket_id.strip():
            raise ValueError("El ID del ticket es requerido")
        if self.costo_final is not None and self.costo_final < 0:
            raise ValueError("El costo final no puede ser negativo")


@dataclass
class CalificarTicketDTO:
    ticket_id: str
    nota:      float

    def __post_init__(self):
        if not 1.0 <= self.nota <= 5.0:
            raise ValueError("La nota debe estar entre 1.0 y 5.0")


# ================================================================
# DTOs DE SALIDA — TICKET
# ================================================================
@dataclass
class TicketResumenDTO:
    id:             str
    numero:         str
    tipo_servicio:  str
    estado:         str
    prioridad:      str
    titulo:         str
    descripcion:    str
    costo_estimado: Optional[float]
    costo_final:    Optional[float]
    tecnico_nombre: Optional[str]
    calificacion:   Optional[float]
    creado_en:      str
    resuelto_en:    Optional[str]

    @classmethod
    def desde_entidad(cls, ticket, tecnico_nombre: Optional[str] = None) -> "TicketResumenDTO":
        return cls(
            id=ticket.id,
            numero=ticket.numero,
            tipo_servicio=ticket.tipo_servicio.value,
            estado=ticket.estado.value,
            prioridad=ticket.prioridad.value,
            titulo=ticket.titulo,
            descripcion=ticket.descripcion,
            costo_estimado=ticket.costo_estimado.pesos if ticket.costo_estimado else None,
            costo_final=ticket.costo_final.pesos if ticket.costo_final else None,
            tecnico_nombre=tecnico_nombre,
            calificacion=ticket.calificacion,
            creado_en=ticket.creado_en.isoformat(),
            resuelto_en=ticket.resuelto_en.isoformat() if ticket.resuelto_en else None,
        )


@dataclass
class ListaTicketsDTO:
    tickets:               list
    total:                 int
    abiertos:              int
    resueltos:             int
    costo_total_historico: float


# ================================================================
# DTOs DE ENTRADA — ALQUILER
# ================================================================
@dataclass
class CrearAlquilerDTO:
    equipo_tipo:   str
    fecha_inicio:  str
    fecha_fin:     str
    costo_diario:  float
    equipo_marca:  str = ""
    equipo_modelo: str = ""

    def __post_init__(self):
        if not self.equipo_tipo.strip():
            raise ValueError("El tipo de equipo es requerido")
        if not self.fecha_inicio.strip():
            raise ValueError("La fecha de inicio es requerida")
        if not self.fecha_fin.strip():
            raise ValueError("La fecha de fin es requerida")
        if self.costo_diario <= 0:
            raise ValueError("El costo diario debe ser mayor a cero")


# ================================================================
# DTOs DE SALIDA — ALQUILER
# ================================================================
@dataclass
class AlquilerResumenDTO:
    id:           str
    equipo_tipo:  str
    equipo_marca: str
    fecha_inicio: str
    fecha_fin:    str
    dias:         int
    costo_diario: float
    costo_total:  float
    deposito:     float
    estado:       str
    creado_en:    str

    @classmethod
    def desde_entidad(cls, alquiler) -> "AlquilerResumenDTO":
        return cls(
            id=alquiler.id,
            equipo_tipo=alquiler.equipo_tipo,
            equipo_marca=alquiler.equipo_marca,
            fecha_inicio=alquiler.periodo.inicio.isoformat(),
            fecha_fin=alquiler.periodo.fin.isoformat(),
            dias=alquiler.periodo.dias,
            costo_diario=alquiler.costo_diario.pesos,
            costo_total=alquiler.costo_total.pesos,
            deposito=alquiler.deposito.pesos,
            estado=alquiler.estado.value,
            creado_en=alquiler.creado_en.isoformat(),
        )


# ================================================================
# DTOs DE ENTRADA — PAGO
# ================================================================
@dataclass
class ProcesarPagoDTO:
    monto:         float
    metodo:        str
    ticket_id:     Optional[str] = None
    alquiler_id:   Optional[str] = None
    token_tarjeta: Optional[str] = None

    def __post_init__(self):
        if self.monto <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        if not self.metodo.strip():
            raise ValueError("El método de pago es requerido")
        if not self.ticket_id and not self.alquiler_id:
            raise ValueError("Debe asociar el pago a un ticket o a un alquiler")
        if self.metodo.lower() == "tarjeta_credito" and not self.token_tarjeta:
            raise ValueError("Se requiere token de tarjeta para pagos con tarjeta")


# ================================================================
# DTOs DE SALIDA — PAGO
# ================================================================
@dataclass
class PagoResumenDTO:
    id:                 str
    monto:              float
    metodo:             str
    estado:             str
    referencia_externa: Optional[str]
    creado_en:          str

    @classmethod
    def desde_entidad(cls, pago) -> "PagoResumenDTO":
        return cls(
            id=pago.id,
            monto=pago.monto.pesos,
            metodo=pago.metodo.value,
            estado=pago.estado,
            referencia_externa=pago.referencia_externa,
            creado_en=pago.creado_en.isoformat(),
        )


# ================================================================
# DTOs DE SALIDA — DASHBOARD
# ================================================================
@dataclass
class DashboardDTO:
    tickets_total:       int
    tickets_nuevos:      int
    tickets_en_proceso:  int
    tickets_resueltos:   int
    clientes_activos:    int
    tecnicos_activos:    int
    ingresos_mes_cop:    float
    tasa_resolucion_pct: float
    tiempo_promedio_min: Optional[float]
