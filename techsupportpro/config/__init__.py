"""
Contenedor de inyección de dependencias — TechSupport Pro.

Este archivo es el único lugar donde se mencionan adaptadores concretos.
El resto del sistema solo conoce puertos (interfaces).

Modos de ejecución (variable de entorno MODO_REPO):
  memoria  →  todo en RAM, sin instalaciones (default)
  postgres →  SQLAlchemy + PostgreSQL
  json     →  archivos JSON en disco

Ejemplo:
    MODO_REPO=memoria  python main.py
    MODO_REPO=postgres python main.py
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field

from techsupportpro.application.use_cases import (
    RegistrarClienteUseCase, LoginClienteUseCase,
    CrearTicketUseCase, ActualizarTicketUseCase,
    CalificarTicketUseCase, MisTicketsUseCase,
    CrearAlquilerUseCase, DevolverAlquilerUseCase,
    ProcesarPagoUseCase, DashboardAdminUseCase,
)


@dataclass
class Contenedor:
    """
    Ensamblaje completo de la aplicación.
    Contiene todos los casos de uso ya construidos con sus dependencias.
    """
    # Casos de uso (acceso público)
    registrar_cliente:   RegistrarClienteUseCase = field(init=False)
    login_cliente:       LoginClienteUseCase     = field(init=False)
    crear_ticket:        CrearTicketUseCase       = field(init=False)
    actualizar_ticket:   ActualizarTicketUseCase  = field(init=False)
    calificar_ticket:    CalificarTicketUseCase   = field(init=False)
    mis_tickets:         MisTicketsUseCase        = field(init=False)
    crear_alquiler:      CrearAlquilerUseCase     = field(init=False)
    devolver_alquiler:   DevolverAlquilerUseCase  = field(init=False)
    procesar_pago:       ProcesarPagoUseCase      = field(init=False)
    dashboard_admin:     DashboardAdminUseCase    = field(init=False)

    # Infraestructura (acceso para tests y CLI)
    _clientes:       object = field(init=False, repr=False)
    _tecnicos:       object = field(init=False, repr=False)
    _tickets:        object = field(init=False, repr=False)
    _alquileres:     object = field(init=False, repr=False)
    _pagos:          object = field(init=False, repr=False)
    _notificaciones: object = field(init=False, repr=False)
    _tokens:         object = field(init=False, repr=False)
    _passwords:      object = field(init=False, repr=False)
    _auditoria:      object = field(init=False, repr=False)
    _pasarela:       object = field(init=False, repr=False)

    def __post_init__(self):
        raise NotImplementedError("Usa Contenedor.crear() en lugar del constructor directo")

    @classmethod
    def crear(cls, modo: str = None) -> "Contenedor":
        """
        Fábrica principal. Lee MODO_REPO del entorno si no se pasa explícitamente.
        """
        modo = modo or os.getenv("MODO_REPO", "memoria")
        obj = object.__new__(cls)
        obj._ensamblar(modo)
        return obj

    def _ensamblar(self, modo: str) -> None:
        print(f"[CONTENEDOR] Iniciando en modo: {modo.upper()}")

        # 1. Instanciar adaptadores según el modo
        if modo == "postgres":
            self._instanciar_postgres()
        elif modo == "json":
            self._instanciar_json()
        else:
            self._instanciar_memoria()

        # 2. Ensamblar casos de uso (inyección de dependencias)
        self.registrar_cliente = RegistrarClienteUseCase(
            clientes=self._clientes, passwords=self._passwords,
            notificaciones=self._notificaciones, auditoria=self._auditoria,
        )
        self.login_cliente = LoginClienteUseCase(
            clientes=self._clientes, passwords=self._passwords,
            tokens=self._tokens, auditoria=self._auditoria,
        )
        self.crear_ticket = CrearTicketUseCase(
            clientes=self._clientes, tickets=self._tickets,
            tecnicos=self._tecnicos, tokens=self._tokens,
            notificaciones=self._notificaciones, auditoria=self._auditoria,
        )
        self.actualizar_ticket = ActualizarTicketUseCase(
            tickets=self._tickets, tecnicos=self._tecnicos,
            clientes=self._clientes, tokens=self._tokens,
            notificaciones=self._notificaciones, auditoria=self._auditoria,
        )
        self.calificar_ticket = CalificarTicketUseCase(
            tickets=self._tickets, tecnicos=self._tecnicos,
            clientes=self._clientes, tokens=self._tokens,
            auditoria=self._auditoria,
        )
        self.mis_tickets = MisTicketsUseCase(
            tickets=self._tickets, tecnicos=self._tecnicos, tokens=self._tokens,
        )
        self.crear_alquiler = CrearAlquilerUseCase(
            clientes=self._clientes, alquileres=self._alquileres,
            tokens=self._tokens, notificaciones=self._notificaciones,
            auditoria=self._auditoria,
        )
        self.devolver_alquiler = DevolverAlquilerUseCase(
            alquileres=self._alquileres, clientes=self._clientes,
            tokens=self._tokens, auditoria=self._auditoria,
        )
        self.procesar_pago = ProcesarPagoUseCase(
            clientes=self._clientes, pagos=self._pagos,
            tokens=self._tokens, pasarela=self._pasarela,
            notificaciones=self._notificaciones, auditoria=self._auditoria,
        )
        self.dashboard_admin = DashboardAdminUseCase(
            tickets=self._tickets, clientes=self._clientes,
            tecnicos=self._tecnicos, pagos=self._pagos, tokens=self._tokens,
        )
        print(f"[CONTENEDOR] Listo. 10 casos de uso ensamblados.")

    def _instanciar_memoria(self) -> None:
        from techsupportpro.infrastructure.adapters_out.memory import (
            ClienteRepositoryMemoria, TecnicoRepositoryMemoria,
            TicketRepositoryMemoria, AlquilerRepositoryMemoria,
            PagoRepositoryMemoria, NotificacionServiceMemoria,
            PagoGatewayMemoria, TokenServiceMemoria,
            PasswordServiceMemoria, AuditoriaRepositoryMemoria,
        )
        self._clientes       = ClienteRepositoryMemoria()
        self._tecnicos       = TecnicoRepositoryMemoria()
        self._tickets        = TicketRepositoryMemoria()
        self._alquileres     = AlquilerRepositoryMemoria()
        self._pagos          = PagoRepositoryMemoria()
        self._notificaciones = NotificacionServiceMemoria()
        self._pasarela       = PagoGatewayMemoria()
        self._tokens         = TokenServiceMemoria()
        self._passwords      = PasswordServiceMemoria()
        self._auditoria      = AuditoriaRepositoryMemoria()

    def _instanciar_postgres(self) -> None:
        from techsupportpro.infrastructure.adapters_out.postgres import (
            ClienteRepositoryPostgres, TecnicoRepositoryPostgres,
            TicketRepositoryPostgres, AlquilerRepositoryPostgres,
            PagoRepositoryPostgres, AuditoriaRepositoryPostgres,
        )
        from techsupportpro.infrastructure.adapters_out.postgres.db import crear_sesion
        from techsupportpro.infrastructure.adapters_out.memory import (
            NotificacionServiceMemoria, PagoGatewayMemoria,
            TokenServiceMemoria, PasswordServiceMemoria,
        )
        sesion = crear_sesion()
        self._clientes       = ClienteRepositoryPostgres(sesion)
        self._tecnicos       = TecnicoRepositoryPostgres(sesion)
        self._tickets        = TicketRepositoryPostgres(sesion)
        self._alquileres     = AlquilerRepositoryPostgres(sesion)
        self._pagos          = PagoRepositoryPostgres(sesion)
        self._auditoria      = AuditoriaRepositoryPostgres(sesion)
        # Servicios sin estado — igual en todos los modos
        self._notificaciones = NotificacionServiceMemoria()
        self._pasarela       = PagoGatewayMemoria()
        self._tokens         = TokenServiceMemoria()
        self._passwords      = PasswordServiceMemoria()

    def _instanciar_json(self) -> None:
        from techsupportpro.infrastructure.adapters_out.json_file import (
            ClienteRepositoryJSON, TecnicoRepositoryJSON,
            TicketRepositoryJSON, AlquilerRepositoryJSON,
            PagoRepositoryJSON, AuditoriaRepositoryJSON,
        )
        from techsupportpro.infrastructure.adapters_out.memory import (
            NotificacionServiceMemoria, PagoGatewayMemoria,
            TokenServiceMemoria, PasswordServiceMemoria,
        )
        directorio = os.getenv("JSON_DATA_DIR", "./data")
        self._clientes       = ClienteRepositoryJSON(directorio)
        self._tecnicos       = TecnicoRepositoryJSON(directorio)
        self._tickets        = TicketRepositoryJSON(directorio)
        self._alquileres     = AlquilerRepositoryJSON(directorio)
        self._pagos          = PagoRepositoryJSON(directorio)
        self._auditoria      = AuditoriaRepositoryJSON(directorio)
        self._notificaciones = NotificacionServiceMemoria()
        self._pasarela       = PagoGatewayMemoria()
        self._tokens         = TokenServiceMemoria()
        self._passwords      = PasswordServiceMemoria()
