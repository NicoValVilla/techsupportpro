"""
Adaptadores de salida EN MEMORIA — Fake Adapters.

Implementan los puertos del dominio usando estructuras Python en RAM.
Propósito:
  1. Pruebas de integración sin base de datos (milisegundos)
  2. Desarrollo local sin PostgreSQL instalado
  3. Demos y presentaciones sin infraestructura

Uso en contenedor:
    MODO_REPO=memoria  →  usa estos adaptadores
    MODO_REPO=postgres →  usa SQLAlchemy
    MODO_REPO=json     →  usa archivos JSON
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from collections import defaultdict

from techsupportpro.domain.ports import (
    IClienteRepository, ITecnicoRepository, ITicketRepository,
    IAlquilerRepository, IPagoRepository,
    INotificacionService, IPagoGateway, ITokenService,
    IPasswordService, IAuditoriaRepository,
)
from techsupportpro.domain.entities import (
    Cliente, Tecnico, Ticket, AlquilerEquipo, Pago, EstadoTicket,
)
from techsupportpro.domain.value_objects import Email, PasswordHash, COP


# ================================================================
# REPOSITORIOS EN MEMORIA
# ================================================================

class ClienteRepositoryMemoria(IClienteRepository):
    """Repositorio de clientes en memoria."""

    def __init__(self):
        self._store: dict[str, Cliente] = {}

    def guardar(self, cliente: Cliente) -> None:
        self._store[cliente.id] = cliente

    def actualizar(self, cliente: Cliente) -> None:
        self._store[cliente.id] = cliente

    def buscar_por_id(self, cliente_id: str) -> Optional[Cliente]:
        return self._store.get(cliente_id)

    def buscar_por_email(self, email: Email) -> Optional[Cliente]:
        for c in self._store.values():
            if str(c.email) == str(email):
                return c
        return None

    def listar_todos(self) -> list[Cliente]:
        return list(self._store.values())

    def contar_activos(self) -> int:
        return sum(1 for c in self._store.values() if c.activo and c.verificado)


class TecnicoRepositoryMemoria(ITecnicoRepository):
    """Repositorio de técnicos en memoria."""

    def __init__(self):
        self._store: dict[str, Tecnico] = {}

    def guardar(self, tecnico: Tecnico) -> None:
        self._store[tecnico.id] = tecnico

    def actualizar(self, tecnico: Tecnico) -> None:
        self._store[tecnico.id] = tecnico

    def buscar_por_id(self, tecnico_id: str) -> Optional[Tecnico]:
        return self._store.get(tecnico_id)

    def buscar_por_email(self, email: Email) -> Optional[Tecnico]:
        for t in self._store.values():
            if str(t.email) == str(email):
                return t
        return None

    def listar_disponibles(self) -> list[Tecnico]:
        return [t for t in self._store.values() if t.disponible and t.activo]

    def listar_todos(self) -> list[Tecnico]:
        return list(self._store.values())

    def contar_activos(self) -> int:
        return sum(1 for t in self._store.values() if t.activo)


class TicketRepositoryMemoria(ITicketRepository):
    """Repositorio de tickets en memoria."""

    def __init__(self):
        self._store: dict[str, Ticket] = {}

    def guardar(self, ticket: Ticket) -> None:
        self._store[ticket.id] = ticket

    def actualizar(self, ticket: Ticket) -> None:
        self._store[ticket.id] = ticket

    def buscar_por_id(self, ticket_id: str) -> Optional[Ticket]:
        return self._store.get(ticket_id)

    def listar_por_cliente(
        self, cliente_id: str, estado: Optional[EstadoTicket] = None
    ) -> list[Ticket]:
        tickets = [t for t in self._store.values() if t.cliente_id == cliente_id]
        if estado:
            tickets = [t for t in tickets if t.estado == estado]
        return sorted(tickets, key=lambda t: t.creado_en, reverse=True)

    def listar_por_tecnico(
        self, tecnico_id: str, estado: Optional[EstadoTicket] = None
    ) -> list[Ticket]:
        tickets = [t for t in self._store.values() if t.tecnico_id == tecnico_id]
        if estado:
            tickets = [t for t in tickets if t.estado == estado]
        return sorted(tickets, key=lambda t: t.creado_en, reverse=True)

    def siguiente_numero(self) -> str:
        n = len(self._store) + 1
        return f"TSP-{n:05d}"

    def contar_abiertos_por_cliente(self, cliente_id: str) -> int:
        return sum(
            1 for t in self._store.values()
            if t.cliente_id == cliente_id and t.esta_abierto()
        )

    def contar_total(self) -> int:
        return len(self._store)

    def contar_por_estado(self, estado: EstadoTicket) -> int:
        return sum(1 for t in self._store.values() if t.estado == estado)

    def listar_todos(self) -> list[Ticket]:
        return list(self._store.values())


class AlquilerRepositoryMemoria(IAlquilerRepository):
    """Repositorio de alquileres en memoria."""

    def __init__(self):
        self._store: dict[str, AlquilerEquipo] = {}

    def guardar(self, alquiler: AlquilerEquipo) -> None:
        self._store[alquiler.id] = alquiler

    def actualizar(self, alquiler: AlquilerEquipo) -> None:
        self._store[alquiler.id] = alquiler

    def buscar_por_id(self, alquiler_id: str) -> Optional[AlquilerEquipo]:
        return self._store.get(alquiler_id)

    def listar_por_cliente(self, cliente_id: str) -> list[AlquilerEquipo]:
        return [a for a in self._store.values() if a.cliente_id == cliente_id]

    def listar_activos_por_cliente(self, cliente_id: str) -> list[AlquilerEquipo]:
        from techsupportpro.domain.entities import EstadoAlquiler
        return [a for a in self._store.values()
                if a.cliente_id == cliente_id and a.estado == EstadoAlquiler.ACTIVO]

    def contar_activos_por_cliente(self, cliente_id: str) -> int:
        return len(self.listar_activos_por_cliente(cliente_id))

    def listar_todos(self) -> list[AlquilerEquipo]:
        return list(self._store.values())


class PagoRepositoryMemoria(IPagoRepository):
    """Repositorio de pagos en memoria."""

    def __init__(self):
        self._store: dict[str, Pago] = {}

    def guardar(self, pago: Pago) -> None:
        self._store[pago.id] = pago

    def actualizar(self, pago: Pago) -> None:
        self._store[pago.id] = pago

    def buscar_por_id(self, pago_id: str) -> Optional[Pago]:
        return self._store.get(pago_id)

    def listar_por_cliente(self, cliente_id: str) -> list[Pago]:
        return [p for p in self._store.values() if p.cliente_id == cliente_id]

    def sumar_ingresos_desde(self, desde: datetime) -> COP:
        total = sum(
            p.monto.centavos
            for p in self._store.values()
            if p.creado_en >= desde and p.estado == "confirmado"
        )
        return COP(centavos=total)

    def listar_todos(self) -> list[Pago]:
        return list(self._store.values())


# ================================================================
# SERVICIOS DE INFRAESTRUCTURA EN MEMORIA
# ================================================================

class NotificacionServiceMemoria(INotificacionService):
    """
    Servicio de notificaciones en memoria.
    Guarda un log de todo lo enviado — útil para verificar en tests.
    """

    def __init__(self):
        self.log: list[dict] = []

    def enviar_bienvenida(self, cliente) -> None:
        self.log.append({"tipo": "bienvenida", "cliente_id": cliente.id,
                         "email": str(cliente.email), "ts": datetime.utcnow()})
        print(f"[NOTIF] Bienvenida → {cliente.email}")

    def enviar_ticket_creado(self, cliente, ticket) -> None:
        self.log.append({"tipo": "ticket_creado", "ticket": ticket.numero,
                         "cliente_id": cliente.id, "ts": datetime.utcnow()})
        print(f"[NOTIF] Ticket creado {ticket.numero} → {cliente.email}")

    def enviar_ticket_asignado(self, tecnico, ticket) -> None:
        self.log.append({"tipo": "ticket_asignado", "ticket": ticket.numero,
                         "tecnico_id": tecnico.id, "ts": datetime.utcnow()})
        print(f"[NOTIF] Ticket {ticket.numero} asignado → {tecnico.email}")

    def enviar_ticket_resuelto(self, cliente, ticket) -> None:
        self.log.append({"tipo": "ticket_resuelto", "ticket": ticket.numero,
                         "cliente_id": cliente.id, "ts": datetime.utcnow()})
        print(f"[NOTIF] Ticket {ticket.numero} resuelto → {cliente.email}")

    def enviar_confirmacion_alquiler(self, cliente, alquiler) -> None:
        self.log.append({"tipo": "alquiler_confirmado", "alquiler_id": alquiler.id,
                         "cliente_id": cliente.id, "ts": datetime.utcnow()})
        print(f"[NOTIF] Alquiler confirmado → {cliente.email}")

    def enviar_recibo_pago(self, cliente, pago) -> None:
        self.log.append({"tipo": "recibo_pago", "pago_id": pago.id,
                         "monto": pago.monto.pesos, "ts": datetime.utcnow()})
        print(f"[NOTIF] Recibo ${pago.monto.pesos:,.0f} COP → {cliente.email}")

    def notificaciones_de_tipo(self, tipo: str) -> list[dict]:
        return [n for n in self.log if n["tipo"] == tipo]


class PagoGatewayMemoria(IPagoGateway):
    """
    Pasarela de pagos simulada.
    Aprueba todo — útil para tests sin Wompi real.
    """

    def __init__(self, simular_fallo: bool = False):
        self._simular_fallo = simular_fallo
        self.transacciones: list[dict] = []

    def procesar_tarjeta(self, monto, token_tarjeta: str, descripcion: str) -> str:
        if self._simular_fallo:
            raise ValueError("Tarjeta rechazada (simulación)")
        ref = f"WOMPI-FAKE-{len(self.transacciones)+1:06d}"
        self.transacciones.append({
            "ref": ref, "monto": monto.pesos,
            "token": token_tarjeta, "ts": datetime.utcnow()
        })
        print(f"[PASARELA] Pago ${monto.pesos:,.0f} COP aprobado → {ref}")
        return ref


    def reembolsar(self, referencia: str, monto) -> str:
        ref = f"REFUND-{referencia}"
        self.transacciones.append({"ref": ref, "tipo": "reembolso", "ts": datetime.utcnow()})
        print(f"[PASARELA] Reembolso {ref}")
        return ref

    def verificar_transaccion(self, referencia: str) -> dict:
        for t in self.transacciones:
            if t.get("ref") == referencia:
                return {"referencia": referencia, "estado": "aprobado", "monto": t.get("monto")}
        return {"referencia": referencia, "estado": "no_encontrada"}


class TokenServiceMemoria(ITokenService):
    """
    Servicio de tokens JWT simulado.
    Usa tokens simples en formato 'tipo:usuario_id' para desarrollo.
    """

    def generar_token(self, usuario_id: str, tipo: str, horas: int = 12) -> str:
        token = f"{tipo}:{usuario_id}"
        print(f"[TOKEN] Generado para {tipo} {usuario_id[:8]}...")
        return token

    def revocar_token(self, token: str) -> None:
        print(f"[TOKEN] Revocado: {token[:20]}...")

    def verificar_token(self, token: str) -> Optional[dict]:
        try:
            partes = token.split(":", 1)
            if len(partes) != 2:
                return None
            tipo, usuario_id = partes
            if tipo not in ("cliente", "tecnico"):
                return None
            return {"tipo": tipo, "usuario_id": usuario_id}
        except Exception:
            return None


class PasswordServiceMemoria(IPasswordService):
    """
    Servicio de contraseñas en memoria.
    Usa prefijo 'hashed:' para simular — NO apto para producción.
    """

    def hashear(self, password_plana: str) -> PasswordHash:
        return PasswordHash(f"salt123:{password_plana}")

    def verificar(self, password_plana: str, password_hash: PasswordHash) -> bool:
        partes = str(password_hash).split(":", 1)
        if len(partes) != 2:
            return False
        return partes[1] == password_plana


class AuditoriaRepositoryMemoria(IAuditoriaRepository):
    """Repositorio de auditoría en memoria con log completo."""

    def __init__(self):
        self.eventos: list[dict] = []

    def registrar(
        self, usuario_id: str, tipo_usuario: str, accion: str, detalle: str
    ) -> None:
        evento = {
            "usuario_id": usuario_id,
            "tipo_usuario": tipo_usuario,
            "accion": accion,
            "detalle": detalle,
            "ts": datetime.utcnow().isoformat(),
        }
        self.eventos.append(evento)
        print(f"[AUDIT] {tipo_usuario.upper()} {accion}: {detalle}")

    def listar_por_usuario(self, usuario_id: str) -> list[dict]:
        return [e for e in self.eventos if e["usuario_id"] == usuario_id]

    def listar_por_accion(self, accion: str) -> list[dict]:
        return [e for e in self.eventos if e["accion"] == accion]
