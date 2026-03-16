"""
Casos de uso — capa de aplicación TechSupport Pro.

Cada caso de uso:
  1. Recibe un DTO de entrada
  2. Orquesta entidades del dominio y puertos
  3. Retorna un DTO de salida

Los casos de uso NO contienen lógica de negocio — esa vive en el dominio.
Los casos de uso NO saben nada de HTTP, SQL ni infraestructura — usan puertos.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional

from techsupportpro.domain.entities import (
    Cliente, Ticket, AlquilerEquipo, Pago,
    TipoServicio, EstadoTicket, Prioridad, PlanCliente, MetodoPago,
)
from techsupportpro.domain.value_objects import (
    PasswordPlana,
    Email, PasswordPlana, NombrePersona, TelefonoColombia, COP, Periodo,
)
from techsupportpro.domain.ports import (
    IClienteRepository, ITicketRepository, IAlquilerRepository,
    IPagoRepository, ITecnicoRepository,
    INotificacionService, IPagoGateway, ITokenService,
    IPasswordService, IAuditoriaRepository,
)
from techsupportpro.domain.services import (
    TecnicoAsignadorService, NumeradorTicketService, MetricasService,
)
from techsupportpro.domain.exceptions import (
    EmailYaRegistrado, ClienteNoEncontrado, ClienteSuspendido,
    CredencialesInvalidas, TokenInvalidoOExpirado,
    TicketNoEncontrado, TecnicoNoEncontrado, AccesoNoAutorizado,
    AlquilerNoEncontrado,
)
from techsupportpro.application.dtos import (
    RegistrarClienteDTO, LoginDTO, ClienteResumenDTO, LoginRespuestaDTO,
    CrearTicketDTO, ActualizarTicketDTO, CalificarTicketDTO,
    TicketResumenDTO, ListaTicketsDTO,
    CrearAlquilerDTO, AlquilerResumenDTO,
    ProcesarPagoDTO, PagoResumenDTO,
    DashboardDTO,
)


class RegistrarClienteUseCase:
    def __init__(self, clientes, passwords, notificaciones, auditoria):
        self._clientes = clientes
        self._passwords = passwords
        self._notificaciones = notificaciones
        self._auditoria = auditoria

    def ejecutar(self, dto: RegistrarClienteDTO) -> ClienteResumenDTO:
        email  = Email(dto.email)
        nombre = NombrePersona(dto.nombre)
        telefono = TelefonoColombia(dto.telefono) if dto.telefono else None

        if self._clientes.buscar_por_email(email):
            raise EmailYaRegistrado(dto.email)

        PasswordPlana(dto.password)  # valida complejidad antes de delegar
        pwd_hash = self._passwords.hashear(dto.password)

        cliente = Cliente.crear(
            nombre=nombre, email=email, password_hash=pwd_hash,
            empresa=dto.empresa, telefono=telefono, ciudad=dto.ciudad,
        )
        self._clientes.guardar(cliente)
        self._notificaciones.enviar_bienvenida(cliente)
        self._auditoria.registrar(cliente.id, "cliente", "REGISTRO", f"Cliente registrado: {email}")
        return ClienteResumenDTO.desde_entidad(cliente)


class LoginClienteUseCase:
    _HORAS_SESION = 12

    def __init__(self, clientes, passwords, tokens, auditoria):
        self._clientes  = clientes
        self._passwords = passwords
        self._tokens    = tokens
        self._auditoria = auditoria

    def ejecutar(self, dto: LoginDTO) -> LoginRespuestaDTO:
        email   = Email(dto.email)
        cliente = self._clientes.buscar_por_email(email)
        if not cliente:
            raise CredencialesInvalidas()
        if not cliente.activo:
            raise ClienteSuspendido(cliente.id)
        if not self._passwords.verificar(dto.password, cliente.password_hash):
            raise CredencialesInvalidas()

        cliente.ultimo_login = datetime.utcnow()
        self._clientes.actualizar(cliente)

        token = self._tokens.generar_token(cliente.id, "cliente", self._HORAS_SESION)
        self._auditoria.registrar(cliente.id, "cliente", "LOGIN", f"Login: {email}")

        expira = datetime.utcnow() + timedelta(hours=self._HORAS_SESION)
        return LoginRespuestaDTO(
            token=token, cliente_id=cliente.id,
            nombre=str(cliente.nombre), plan=cliente.plan.value,
            expira_en=expira.isoformat(),
        )


class CrearTicketUseCase:
    def __init__(self, clientes, tickets, tecnicos, tokens, notificaciones, auditoria):
        self._clientes = clientes; self._tickets = tickets
        self._tecnicos = tecnicos; self._tokens  = tokens
        self._notificaciones = notificaciones; self._auditoria = auditoria

    def ejecutar(self, token: str, dto: CrearTicketDTO) -> TicketResumenDTO:
        payload = self._tokens.verificar_token(token)
        if not payload or payload.get("tipo") != "cliente":
            raise TokenInvalidoOExpirado()

        cliente = self._clientes.buscar_por_id(payload["usuario_id"])
        if not cliente:
            raise ClienteNoEncontrado(payload["usuario_id"])

        try:
            tipo = TipoServicio(dto.tipo_servicio.upper())
        except ValueError:
            raise ValueError(f"Tipo de servicio inválido: '{dto.tipo_servicio}'")

        try:
            prioridad = Prioridad(dto.prioridad.upper())
        except ValueError:
            raise ValueError(f"Prioridad inválida: '{dto.prioridad}'")

        abiertos = self._tickets.contar_abiertos_por_cliente(cliente.id)
        cliente.verificar_limite_tickets(abiertos)

        correlativo = self._tickets.contar_total() + 1
        numero = NumeradorTicketService.generar_ahora(correlativo)

        fecha_prog = None
        if dto.fecha_programada:
            try:
                fecha_prog = datetime.fromisoformat(dto.fecha_programada)
            except ValueError:
                raise ValueError("Formato de fecha inválido. Use ISO 8601")

        ticket = Ticket.crear(
            cliente_id=cliente.id, tipo_servicio=tipo, titulo=dto.titulo,
            descripcion=dto.descripcion, prioridad=prioridad, numero=numero,
            direccion_visita=dto.direccion_visita, fecha_programada=fecha_prog,
        )
        if ticket.costo_estimado:
            ticket.costo_estimado = cliente.aplicar_descuento(ticket.costo_estimado)

        self._tickets.guardar(ticket)

        tecnicos_disponibles = self._tecnicos.listar_disponibles()
        tecnico = TecnicoAsignadorService.seleccionar_mejor_tecnico(tecnicos_disponibles, tipo)
        tecnico_nombre = None
        if tecnico:
            ticket.asignar_tecnico(tecnico.id)
            self._tickets.actualizar(ticket)
            tecnico_nombre = str(tecnico.nombre)
            self._notificaciones.enviar_ticket_asignado(tecnico, ticket)

        self._notificaciones.enviar_ticket_creado(cliente, ticket)
        self._auditoria.registrar(cliente.id, "cliente", "TICKET_CREADO",
                                  f"Ticket {numero} — {tipo.value}")
        return TicketResumenDTO.desde_entidad(ticket, tecnico_nombre)


class ActualizarTicketUseCase:
    def __init__(self, tickets, tecnicos, clientes, tokens, notificaciones, auditoria):
        self._tickets = tickets; self._tecnicos = tecnicos
        self._clientes = clientes; self._tokens = tokens
        self._notificaciones = notificaciones; self._auditoria = auditoria

    def ejecutar(self, token: str, dto: ActualizarTicketDTO) -> TicketResumenDTO:
        payload = self._tokens.verificar_token(token)
        if not payload or payload.get("tipo") != "tecnico":
            raise TokenInvalidoOExpirado()

        tecnico = self._tecnicos.buscar_por_id(payload["usuario_id"])
        if not tecnico:
            raise TecnicoNoEncontrado(payload["usuario_id"])

        ticket = self._tickets.buscar_por_id(dto.ticket_id)
        if not ticket:
            raise TicketNoEncontrado(dto.ticket_id)

        if not tecnico.puede_modificar_ticket(ticket):
            raise AccesoNoAutorizado(f"Técnico {tecnico.id} no autorizado en ticket {ticket.id}")

        if dto.nuevo_estado:
            try:
                nuevo_estado = EstadoTicket(dto.nuevo_estado.upper())
            except ValueError:
                raise ValueError(f"Estado inválido: '{dto.nuevo_estado}'")
            costo_final = COP.de_pesos(dto.costo_final) if dto.costo_final is not None else None
            ticket.transicionar_a(nuevo_estado, diagnostico=dto.diagnostico,
                                  solucion=dto.solucion, costo_final=costo_final)
        else:
            if dto.diagnostico: ticket.diagnostico = dto.diagnostico
            if dto.solucion:    ticket.solucion = dto.solucion
            if dto.costo_final is not None: ticket.costo_final = COP.de_pesos(dto.costo_final)

        self._tickets.actualizar(ticket)

        if ticket.estado == EstadoTicket.RESUELTO:
            cliente = self._clientes.buscar_por_id(ticket.cliente_id)
            if cliente:
                self._notificaciones.enviar_ticket_resuelto(cliente, ticket)

        self._auditoria.registrar(tecnico.id, "tecnico", "TICKET_ACTUALIZADO",
                                  f"Ticket {ticket.numero} → {ticket.estado.value}")
        return TicketResumenDTO.desde_entidad(ticket, str(tecnico.nombre))


class CalificarTicketUseCase:
    def __init__(self, tickets, tecnicos, clientes, tokens, auditoria):
        self._tickets = tickets; self._tecnicos = tecnicos
        self._clientes = clientes; self._tokens = tokens; self._auditoria = auditoria

    def ejecutar(self, token: str, dto: CalificarTicketDTO) -> None:
        payload = self._tokens.verificar_token(token)
        if not payload or payload.get("tipo") != "cliente":
            raise TokenInvalidoOExpirado()

        ticket = self._tickets.buscar_por_id(dto.ticket_id)
        if not ticket:
            raise TicketNoEncontrado(dto.ticket_id)
        if ticket.cliente_id != payload["usuario_id"]:
            raise AccesoNoAutorizado("Solo puedes calificar tus propios tickets")

        ticket.calificar(dto.nota)
        self._tickets.actualizar(ticket)

        if ticket.tecnico_id:
            tecnico = self._tecnicos.buscar_por_id(ticket.tecnico_id)
            if tecnico:
                tecnico.actualizar_calificacion(dto.nota, tecnico.tickets_resueltos)
                self._tecnicos.actualizar(tecnico)

        self._auditoria.registrar(payload["usuario_id"], "cliente", "TICKET_CALIFICADO",
                                  f"Ticket {ticket.numero} → {dto.nota}/5.0")


class MisTicketsUseCase:
    def __init__(self, tickets, tecnicos, tokens):
        self._tickets = tickets; self._tecnicos = tecnicos; self._tokens = tokens

    def ejecutar(self, token: str, estado: Optional[str] = None) -> ListaTicketsDTO:
        payload = self._tokens.verificar_token(token)
        if not payload or payload.get("tipo") != "cliente":
            raise TokenInvalidoOExpirado()

        filtro = None
        if estado:
            try:
                filtro = EstadoTicket(estado.upper())
            except ValueError:
                raise ValueError(f"Estado inválido: '{estado}'")

        tickets = self._tickets.listar_por_cliente(payload["usuario_id"], filtro)

        cache: dict = {}
        items = []
        for t in tickets:
            nombre_tecnico = None
            if t.tecnico_id:
                if t.tecnico_id not in cache:
                    tec = self._tecnicos.buscar_por_id(t.tecnico_id)
                    cache[t.tecnico_id] = str(tec.nombre) if tec else None
                nombre_tecnico = cache[t.tecnico_id]
            items.append(TicketResumenDTO.desde_entidad(t, nombre_tecnico))

        abiertos  = sum(1 for t in tickets if t.esta_abierto())
        resueltos = sum(1 for t in tickets if t.estado in (EstadoTicket.RESUELTO, EstadoTicket.CERRADO))
        costo_total = MetricasService.costo_historico_cliente(tickets)

        return ListaTicketsDTO(tickets=items, total=len(tickets),
                               abiertos=abiertos, resueltos=resueltos,
                               costo_total_historico=costo_total.pesos)


class CrearAlquilerUseCase:
    def __init__(self, clientes, alquileres, tokens, notificaciones, auditoria):
        self._clientes = clientes; self._alquileres = alquileres
        self._tokens = tokens; self._notificaciones = notificaciones
        self._auditoria = auditoria

    def ejecutar(self, token: str, dto: CrearAlquilerDTO) -> AlquilerResumenDTO:
        payload = self._tokens.verificar_token(token)
        if not payload or payload.get("tipo") != "cliente":
            raise TokenInvalidoOExpirado()

        cliente = self._clientes.buscar_por_id(payload["usuario_id"])
        if not cliente:
            raise ClienteNoEncontrado(payload["usuario_id"])

        periodo      = Periodo.de_strings(dto.fecha_inicio, dto.fecha_fin)
        costo_diario = COP.de_pesos(dto.costo_diario)

        alquiler = AlquilerEquipo.crear(
            cliente=cliente, equipo_tipo=dto.equipo_tipo,
            periodo=periodo, costo_diario=costo_diario,
            equipo_marca=dto.equipo_marca, equipo_modelo=dto.equipo_modelo,
        )
        self._alquileres.guardar(alquiler)
        self._notificaciones.enviar_confirmacion_alquiler(cliente, alquiler)
        self._auditoria.registrar(cliente.id, "cliente", "ALQUILER_CREADO",
                                  f"Alquiler {alquiler.id} — {dto.equipo_tipo} — {periodo.dias} días")
        return AlquilerResumenDTO.desde_entidad(alquiler)


class DevolverAlquilerUseCase:
    def __init__(self, alquileres, clientes, tokens, auditoria):
        self._alquileres = alquileres; self._clientes = clientes
        self._tokens = tokens; self._auditoria = auditoria

    def ejecutar(self, token: str, alquiler_id: str) -> AlquilerResumenDTO:
        payload = self._tokens.verificar_token(token)
        if not payload or payload.get("tipo") != "cliente":
            raise TokenInvalidoOExpirado()

        alquiler = self._alquileres.buscar_por_id(alquiler_id)
        if not alquiler:
            raise AlquilerNoEncontrado(alquiler_id)
        if alquiler.cliente_id != payload["usuario_id"]:
            raise AccesoNoAutorizado("Solo puedes devolver tus propios alquileres")

        alquiler.devolver()
        self._alquileres.actualizar(alquiler)
        self._auditoria.registrar(payload["usuario_id"], "cliente", "ALQUILER_DEVUELTO",
                                  f"Alquiler {alquiler_id} devuelto")
        return AlquilerResumenDTO.desde_entidad(alquiler)


class ProcesarPagoUseCase:
    def __init__(self, clientes, pagos, tokens, pasarela, notificaciones, auditoria):
        self._clientes = clientes; self._pagos = pagos; self._tokens = tokens
        self._pasarela = pasarela; self._notificaciones = notificaciones
        self._auditoria = auditoria

    def ejecutar(self, token: str, dto: ProcesarPagoDTO) -> PagoResumenDTO:
        payload = self._tokens.verificar_token(token)
        if not payload or payload.get("tipo") != "cliente":
            raise TokenInvalidoOExpirado()

        cliente = self._clientes.buscar_por_id(payload["usuario_id"])
        if not cliente:
            raise ClienteNoEncontrado(payload["usuario_id"])

        try:
            metodo = MetodoPago(dto.metodo.lower())
        except ValueError:
            raise ValueError(f"Método '{dto.metodo}' inválido. Opciones: {[m.value for m in MetodoPago]}")

        monto = COP.de_pesos(dto.monto)
        pago  = Pago.crear(cliente_id=cliente.id, monto=monto, metodo=metodo,
                            ticket_id=dto.ticket_id, alquiler_id=dto.alquiler_id)

        if metodo in (MetodoPago.TARJETA_CREDITO, MetodoPago.TARJETA_DEBITO):
            ref = self._pasarela.procesar_tarjeta(monto, dto.token_tarjeta, "TechSupport Pro")
            pago.confirmar(ref)
        else:
            pago.confirmar(f"REF-{pago.id[:8].upper()}")

        self._pagos.guardar(pago)
        self._notificaciones.enviar_recibo_pago(cliente, pago)
        self._auditoria.registrar(cliente.id, "cliente", "PAGO_PROCESADO",
                                  f"Pago ${monto.pesos:,.0f} COP — {metodo.value}")
        return PagoResumenDTO.desde_entidad(pago)


class DashboardAdminUseCase:
    def __init__(self, tickets, clientes, tecnicos, pagos, tokens):
        self._tickets = tickets; self._clientes = clientes
        self._tecnicos = tecnicos; self._pagos = pagos; self._tokens = tokens

    def ejecutar(self, token: str) -> DashboardDTO:
        payload = self._tokens.verificar_token(token)
        if not payload or payload.get("tipo") != "tecnico":
            raise TokenInvalidoOExpirado()

        tecnico = self._tecnicos.buscar_por_id(payload["usuario_id"])
        if not tecnico:
            raise TecnicoNoEncontrado(payload["usuario_id"])
        if not tecnico.es_admin():
            raise AccesoNoAutorizado("Solo administradores pueden ver el dashboard")

        total     = self._tickets.contar_total()
        nuevos    = self._tickets.contar_por_estado(EstadoTicket.NUEVO)
        proceso   = self._tickets.contar_por_estado(EstadoTicket.EN_PROCESO)
        resueltos = self._tickets.contar_por_estado(EstadoTicket.RESUELTO)

        inicio_mes   = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ingresos_mes = self._pagos.sumar_ingresos_desde(inicio_mes)
        tasa         = MetricasService.tasa_resolucion(total, resueltos)

        return DashboardDTO(
            tickets_total=total, tickets_nuevos=nuevos,
            tickets_en_proceso=proceso, tickets_resueltos=resueltos,
            clientes_activos=self._clientes.contar_activos(),
            tecnicos_activos=self._tecnicos.contar_activos(),
            ingresos_mes_cop=ingresos_mes.pesos,
            tasa_resolucion_pct=tasa,
            tiempo_promedio_min=None,
        )
