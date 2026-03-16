"""
Puertos del dominio TechSupport Pro (Ports & Adapters).

Los puertos son interfaces (ABCs) que definen:
  - Puertos de ENTRADA (Input Ports): lo que el sistema OFRECE al mundo exterior
  - Puertos de SALIDA (Output Ports): lo que el dominio NECESITA de la infraestructura

Ninguna clase aquí importa SQLAlchemy, FastAPI, smtplib, requests ni nada de infra.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from techsupportpro.domain.entities import (
    Cliente, Tecnico, Ticket, AlquilerEquipo, Pago,
    TipoServicio, EstadoTicket, Prioridad, PlanCliente,
    MetodoPago, RolTecnico,
)
from techsupportpro.domain.value_objects import Email, PasswordHash, COP, Periodo


# ================================================================
# PUERTOS DE SALIDA — REPOSITORIOS
# ================================================================

class IClienteRepository(ABC):
    """Puerto de salida: persistencia de clientes."""

    @abstractmethod
    def guardar(self, cliente: Cliente) -> None: ...

    @abstractmethod
    def buscar_por_id(self, cliente_id: str) -> Optional[Cliente]: ...

    @abstractmethod
    def buscar_por_email(self, email: Email) -> Optional[Cliente]: ...

    @abstractmethod
    def actualizar(self, cliente: Cliente) -> None: ...

    @abstractmethod
    def contar_activos(self) -> int: ...


class ITecnicoRepository(ABC):
    """Puerto de salida: persistencia de técnicos."""

    @abstractmethod
    def guardar(self, tecnico: Tecnico) -> None: ...

    @abstractmethod
    def buscar_por_id(self, tecnico_id: str) -> Optional[Tecnico]: ...

    @abstractmethod
    def buscar_por_email(self, email: Email) -> Optional[Tecnico]: ...

    @abstractmethod
    def listar_disponibles(self) -> list[Tecnico]: ...

    @abstractmethod
    def actualizar(self, tecnico: Tecnico) -> None: ...

    @abstractmethod
    def contar_activos(self) -> int: ...


class ITicketRepository(ABC):
    """Puerto de salida: persistencia de tickets."""

    @abstractmethod
    def guardar(self, ticket: Ticket) -> None: ...

    @abstractmethod
    def buscar_por_id(self, ticket_id: str) -> Optional[Ticket]: ...

    @abstractmethod
    def listar_por_cliente(
        self,
        cliente_id: str,
        estado: Optional[EstadoTicket] = None,
    ) -> list[Ticket]: ...

    @abstractmethod
    def listar_por_tecnico(
        self,
        tecnico_id: str,
        estado: Optional[EstadoTicket] = None,
    ) -> list[Ticket]: ...

    @abstractmethod
    def contar_abiertos_por_cliente(self, cliente_id: str) -> int: ...

    @abstractmethod
    def siguiente_numero(self) -> str: ...

    @abstractmethod
    def actualizar(self, ticket: Ticket) -> None: ...

    @abstractmethod
    def contar_por_estado(self, estado: EstadoTicket) -> int: ...

    @abstractmethod
    def contar_total(self) -> int: ...


class IAlquilerRepository(ABC):
    """Puerto de salida: persistencia de alquileres."""

    @abstractmethod
    def guardar(self, alquiler: AlquilerEquipo) -> None: ...

    @abstractmethod
    def buscar_por_id(self, alquiler_id: str) -> Optional[AlquilerEquipo]: ...

    @abstractmethod
    def listar_activos_por_cliente(self, cliente_id: str) -> list[AlquilerEquipo]: ...

    @abstractmethod
    def contar_activos_por_cliente(self, cliente_id: str) -> int: ...

    @abstractmethod
    def actualizar(self, alquiler: AlquilerEquipo) -> None: ...


class IPagoRepository(ABC):
    """Puerto de salida: persistencia de pagos."""

    @abstractmethod
    def guardar(self, pago: Pago) -> None: ...

    @abstractmethod
    def buscar_por_id(self, pago_id: str) -> Optional[Pago]: ...

    @abstractmethod
    def listar_por_cliente(self, cliente_id: str) -> list[Pago]: ...

    @abstractmethod
    def sumar_ingresos_desde(self, desde: datetime) -> COP: ...

    @abstractmethod
    def actualizar(self, pago: Pago) -> None: ...


# ================================================================
# PUERTOS DE SALIDA — SERVICIOS EXTERNOS
# ================================================================

class INotificacionService(ABC):
    """Puerto de salida: envío de notificaciones (email, WhatsApp, SMS)."""

    @abstractmethod
    def enviar_bienvenida(self, cliente: Cliente) -> None: ...

    @abstractmethod
    def enviar_ticket_creado(self, cliente: Cliente, ticket: Ticket) -> None: ...

    @abstractmethod
    def enviar_ticket_asignado(self, tecnico: Tecnico, ticket: Ticket) -> None: ...

    @abstractmethod
    def enviar_ticket_resuelto(self, cliente: Cliente, ticket: Ticket) -> None: ...

    @abstractmethod
    def enviar_confirmacion_alquiler(
        self, cliente: Cliente, alquiler: AlquilerEquipo
    ) -> None: ...

    @abstractmethod
    def enviar_recibo_pago(self, cliente: Cliente, pago: Pago) -> None: ...


class IPagoGateway(ABC):
    """Puerto de salida: pasarela de pagos (Wompi Colombia)."""

    @abstractmethod
    def procesar_tarjeta(
        self, monto: COP, token_tarjeta: str, descripcion: str
    ) -> str: ...
    """Retorna referencia externa de la transacción."""

    @abstractmethod
    def verificar_transaccion(self, referencia: str) -> bool: ...

    @abstractmethod
    def reembolsar(self, referencia: str, monto: COP) -> bool: ...


class ITokenService(ABC):
    """Puerto de salida: generación y verificación de tokens de sesión."""

    @abstractmethod
    def generar_token(self, usuario_id: str, tipo: str, horas: int = 12) -> str: ...

    @abstractmethod
    def verificar_token(self, token: str) -> Optional[dict]: ...
    """Retorna {usuario_id, tipo} o None si inválido/expirado."""

    @abstractmethod
    def revocar_token(self, token: str) -> None: ...


class IPasswordService(ABC):
    """Puerto de salida: hashing y verificación de contraseñas."""

    @abstractmethod
    def hashear(self, password_plana: str) -> PasswordHash: ...

    @abstractmethod
    def verificar(self, password_plana: str, hash_guardado: PasswordHash) -> bool: ...


class IAuditoriaRepository(ABC):
    """Puerto de salida: registro de auditoría."""

    @abstractmethod
    def registrar(
        self,
        usuario_id: str,
        tipo_usuario: str,
        accion: str,
        detalle: str,
    ) -> None: ...


class ICRMWebhookService(ABC):
    """Puerto de salida: integración con CRM externo."""

    @abstractmethod
    def notificar_cliente_registrado(self, cliente: Cliente) -> None: ...

    @abstractmethod
    def notificar_ticket_resuelto(self, ticket: Ticket) -> None: ...


# ================================================================
# PUERTOS DE ENTRADA — CASOS DE USO (interfaces)
# ================================================================

class IClienteService(ABC):
    """Puerto de entrada: operaciones sobre clientes."""

    @abstractmethod
    def registrar(
        self,
        nombre: str,
        email: str,
        password: str,
        empresa: str = "",
        telefono: str = "",
        ciudad: str = "Bogotá",
    ) -> Cliente: ...

    @abstractmethod
    def login(self, email: str, password: str) -> str: ...
    """Retorna el token de sesión."""

    @abstractmethod
    def verificar_email(self, token: str) -> None: ...

    @abstractmethod
    def obtener_por_token(self, token: str) -> Cliente: ...


class ITicketService(ABC):
    """Puerto de entrada: operaciones sobre tickets."""

    @abstractmethod
    def crear(
        self,
        token_cliente: str,
        tipo_servicio: str,
        titulo: str,
        descripcion: str,
        prioridad: str,
        direccion_visita: str = "",
        fecha_programada: str = "",
    ) -> Ticket: ...

    @abstractmethod
    def actualizar_estado(
        self,
        token_tecnico: str,
        ticket_id: str,
        nuevo_estado: str,
        diagnostico: Optional[str] = None,
        solucion: Optional[str] = None,
        costo_final: Optional[float] = None,
    ) -> Ticket: ...

    @abstractmethod
    def calificar(
        self, token_cliente: str, ticket_id: str, nota: float
    ) -> None: ...

    @abstractmethod
    def listar_mis_tickets(
        self, token_cliente: str, estado: Optional[str] = None
    ) -> list[Ticket]: ...


class IAlquilerService(ABC):
    """Puerto de entrada: operaciones sobre alquileres."""

    @abstractmethod
    def crear(
        self,
        token_cliente: str,
        equipo_tipo: str,
        fecha_inicio: str,
        fecha_fin: str,
        costo_diario: float,
        equipo_marca: str = "",
        equipo_modelo: str = "",
    ) -> AlquilerEquipo: ...

    @abstractmethod
    def devolver(self, token_cliente: str, alquiler_id: str) -> None: ...


class IPagoService(ABC):
    """Puerto de entrada: operaciones sobre pagos."""

    @abstractmethod
    def procesar(
        self,
        token_cliente: str,
        monto: float,
        metodo: str,
        ticket_id: Optional[str] = None,
        alquiler_id: Optional[str] = None,
        token_tarjeta: Optional[str] = None,
    ) -> Pago: ...


class IAdminService(ABC):
    """Puerto de entrada: operaciones administrativas."""

    @abstractmethod
    def dashboard(self, token_tecnico: str) -> dict: ...
