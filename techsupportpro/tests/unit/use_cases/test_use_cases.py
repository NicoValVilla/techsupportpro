"""
Tests de casos de uso — Fase 3.

Cada test usa mocks de los puertos (repositorios, servicios externos).
Esto demuestra que los casos de uso son testeables sin base de datos ni red.
"""
import sys, os, unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

sys.path.insert(0, '/home/claude/fase3')

from techsupportpro.domain.entities import (
    Cliente, Tecnico, Ticket, AlquilerEquipo,
    TipoServicio, EstadoTicket, Prioridad, PlanCliente, RolTecnico,
)
from techsupportpro.domain.value_objects import (
    Email, PasswordHash, NombrePersona, COP, Periodo,
)
from techsupportpro.domain.exceptions import (
    EmailYaRegistrado, CredencialesInvalidas, ClienteSuspendido,
    TokenInvalidoOExpirado, LimiteTicketsPlanExcedido,
    TicketNoEncontrado, AccesoNoAutorizado, DiagnosticoRequerido,
    TicketYaCalificado,
)
from techsupportpro.application.dtos import (
    RegistrarClienteDTO, LoginDTO, CrearTicketDTO,
    ActualizarTicketDTO, CalificarTicketDTO, CrearAlquilerDTO,
    ProcesarPagoDTO,
)
from techsupportpro.application.use_cases import (
    RegistrarClienteUseCase, LoginClienteUseCase, CrearTicketUseCase,
    ActualizarTicketUseCase, CalificarTicketUseCase, MisTicketsUseCase,
    CrearAlquilerUseCase, DevolverAlquilerUseCase,
    ProcesarPagoUseCase, DashboardAdminUseCase,
)


# ── FACTORIES ────────────────────────────────────────────────────
def cliente_fixture(plan=PlanCliente.BASICO, activo=True, verificado=True):
    c = Cliente.crear(
        nombre=NombrePersona("Carlos Muñoz"),
        email=Email("carlos@empresa.com"),
        password_hash=PasswordHash("salt:hash"),
        plan=plan,
    )
    c.activo     = activo
    c.verificado = verificado
    return c

def tecnico_fixture(rol=RolTecnico.TECNICO):
    t = Tecnico.crear(
        nombre=NombrePersona("Ana García"),
        email=Email("ana@techsupportpro.com"),
        password_hash=PasswordHash("s:h"),
        rol=rol,
        especialidades=[TipoServicio.SOPORTE_REMOTO, TipoServicio.REPARACION_IMPRESORA],
    )
    t.disponible = True
    return t

def ticket_fixture(cliente_id: str, estado=EstadoTicket.NUEVO):
    t = Ticket.crear(
        cliente_id=cliente_id,
        tipo_servicio=TipoServicio.SOPORTE_REMOTO,
        titulo="Equipo no enciende",
        descripcion="El equipo no enciende desde esta mañana después de la tormenta.",
        prioridad=Prioridad.MEDIA,
        numero="TSP-202604-00001",
    )
    t.estado = estado
    return t

def mocks_cliente():
    """Retorna mocks de todos los puertos necesarios para casos de uso de cliente."""
    return {
        "clientes":       MagicMock(),
        "passwords":      MagicMock(),
        "tokens":         MagicMock(),
        "notificaciones": MagicMock(),
        "auditoria":      MagicMock(),
        "tickets":        MagicMock(),
        "tecnicos":       MagicMock(),
        "alquileres":     MagicMock(),
        "pagos":          MagicMock(),
        "pasarela":       MagicMock(),
    }


# ================================================================
# TESTS: REGISTRAR CLIENTE
# ================================================================
class TestRegistrarCliente(unittest.TestCase):

    def _uc(self, m):
        return RegistrarClienteUseCase(
            clientes=m["clientes"], passwords=m["passwords"],
            notificaciones=m["notificaciones"], auditoria=m["auditoria"],
        )

    def test_registro_exitoso(self):
        m = mocks_cliente()
        m["clientes"].buscar_por_email.return_value = None
        m["passwords"].hashear.return_value = PasswordHash("salt:hash")

        resultado = self._uc(m).ejecutar(RegistrarClienteDTO(
            nombre="Carlos Muñoz", email="carlos@empresa.com", password="TechPro123",
        ))

        self.assertEqual(resultado.email, "carlos@empresa.com")
        self.assertEqual(resultado.plan, "basico")
        m["clientes"].guardar.assert_called_once()
        m["notificaciones"].enviar_bienvenida.assert_called_once()
        m["auditoria"].registrar.assert_called_once()

    def test_email_duplicado_lanza_error(self):
        m = mocks_cliente()
        m["clientes"].buscar_por_email.return_value = cliente_fixture()

        with self.assertRaises(EmailYaRegistrado):
            self._uc(m).ejecutar(RegistrarClienteDTO(
                nombre="Carlos Muñoz", email="carlos@empresa.com", password="TechPro123",
            ))
        m["clientes"].guardar.assert_not_called()
        m["notificaciones"].enviar_bienvenida.assert_not_called()

    def test_email_invalido_lanza_error(self):
        m = mocks_cliente()
        with self.assertRaises(ValueError):
            self._uc(m).ejecutar(RegistrarClienteDTO(
                nombre="Carlos Muñoz", email="no-es-email", password="TechPro123",
            ))

    def test_nombre_invalido_lanza_error(self):
        m = mocks_cliente()
        with self.assertRaises(ValueError):
            self._uc(m).ejecutar(RegistrarClienteDTO(
                nombre="A", email="carlos@empresa.com", password="TechPro123",
            ))

    def test_password_debil_lanza_error(self):
        m = mocks_cliente()
        m["clientes"].buscar_por_email.return_value = None
        # PasswordPlana valida antes de llegar a hashear
        with self.assertRaises(ValueError):
            self._uc(m).ejecutar(RegistrarClienteDTO(
                nombre="Carlos Muñoz", email="carlos@empresa.com", password="corta",
            ))


# ================================================================
# TESTS: LOGIN CLIENTE
# ================================================================
class TestLoginCliente(unittest.TestCase):

    def _uc(self, m):
        return LoginClienteUseCase(
            clientes=m["clientes"], passwords=m["passwords"],
            tokens=m["tokens"], auditoria=m["auditoria"],
        )

    def test_login_exitoso(self):
        m = mocks_cliente()
        c = cliente_fixture()
        m["clientes"].buscar_por_email.return_value = c
        m["passwords"].verificar.return_value = True
        m["tokens"].generar_token.return_value = "token-abc-123"

        resultado = self._uc(m).ejecutar(LoginDTO("carlos@empresa.com", "TechPro123"))

        self.assertEqual(resultado.token, "token-abc-123")
        self.assertEqual(resultado.plan, "basico")
        m["clientes"].actualizar.assert_called_once()

    def test_usuario_no_existe_lanza_error(self):
        m = mocks_cliente()
        m["clientes"].buscar_por_email.return_value = None
        with self.assertRaises(CredencialesInvalidas):
            self._uc(m).ejecutar(LoginDTO("noexiste@empresa.com", "pass"))

    def test_password_incorrecta_lanza_error(self):
        m = mocks_cliente()
        m["clientes"].buscar_por_email.return_value = cliente_fixture()
        m["passwords"].verificar.return_value = False
        with self.assertRaises(CredencialesInvalidas):
            self._uc(m).ejecutar(LoginDTO("carlos@empresa.com", "MalPassword123"))

    def test_cliente_suspendido_lanza_error(self):
        m = mocks_cliente()
        c = cliente_fixture(activo=False)
        m["clientes"].buscar_por_email.return_value = c
        with self.assertRaises(ClienteSuspendido):
            self._uc(m).ejecutar(LoginDTO("carlos@empresa.com", "TechPro123"))
        m["passwords"].verificar.assert_not_called()


# ================================================================
# TESTS: CREAR TICKET
# ================================================================
class TestCrearTicket(unittest.TestCase):

    def _uc(self, m):
        return CrearTicketUseCase(
            clientes=m["clientes"], tickets=m["tickets"], tecnicos=m["tecnicos"],
            tokens=m["tokens"], notificaciones=m["notificaciones"], auditoria=m["auditoria"],
        )

    def _setup_token(self, m, cliente):
        m["tokens"].verificar_token.return_value = {"usuario_id": cliente.id, "tipo": "cliente"}
        m["clientes"].buscar_por_id.return_value = cliente
        m["tickets"].contar_abiertos_por_cliente.return_value = 0
        m["tickets"].contar_total.return_value = 0
        m["tickets"].guardar.return_value = None
        m["tickets"].actualizar.return_value = None
        m["tecnicos"].listar_disponibles.return_value = []

    def test_crear_ticket_exitoso(self):
        m = mocks_cliente()
        c = cliente_fixture()
        self._setup_token(m, c)

        resultado = self._uc(m).ejecutar("token-ok", CrearTicketDTO(
            tipo_servicio="SOPORTE_REMOTO",
            titulo="Equipo no enciende",
            descripcion="El equipo no enciende desde esta mañana.",
        ))

        self.assertEqual(resultado.tipo_servicio, "SOPORTE_REMOTO")
        self.assertEqual(resultado.estado, "NUEVO")
        self.assertEqual(resultado.costo_estimado, 45_000.0)
        m["tickets"].guardar.assert_called_once()
        m["notificaciones"].enviar_ticket_creado.assert_called_once()

    def test_plan_basico_descuento_cero(self):
        m = mocks_cliente()
        c = cliente_fixture(plan=PlanCliente.BASICO)
        self._setup_token(m, c)
        resultado = self._uc(m).ejecutar("token-ok", CrearTicketDTO(
            tipo_servicio="SOPORTE_REMOTO",
            titulo="Equipo no enciende",
            descripcion="El equipo no enciende desde esta mañana.",
        ))
        self.assertEqual(resultado.costo_estimado, 45_000.0)

    def test_plan_profesional_aplica_descuento_15pct(self):
        m = mocks_cliente()
        c = cliente_fixture(plan=PlanCliente.PROFESIONAL)
        self._setup_token(m, c)
        resultado = self._uc(m).ejecutar("token-ok", CrearTicketDTO(
            tipo_servicio="SOPORTE_REMOTO",
            titulo="Equipo no enciende",
            descripcion="El equipo no enciende desde esta mañana.",
        ))
        # 45.000 * 0.85 = 38.250
        self.assertEqual(resultado.costo_estimado, 38_250.0)

    def test_asigna_tecnico_disponible(self):
        m = mocks_cliente()
        c = cliente_fixture()
        self._setup_token(m, c)
        tec = tecnico_fixture()
        m["tecnicos"].listar_disponibles.return_value = [tec]

        resultado = self._uc(m).ejecutar("token-ok", CrearTicketDTO(
            tipo_servicio="SOPORTE_REMOTO",
            titulo="Equipo no enciende",
            descripcion="El equipo no enciende desde esta mañana.",
        ))

        self.assertEqual(resultado.tecnico_nombre, "Ana García")
        m["notificaciones"].enviar_ticket_asignado.assert_called_once()

    def test_token_invalido_lanza_error(self):
        m = mocks_cliente()
        m["tokens"].verificar_token.return_value = None
        with self.assertRaises(TokenInvalidoOExpirado):
            self._uc(m).ejecutar("token-malo", CrearTicketDTO(
                tipo_servicio="SOPORTE_REMOTO",
                titulo="Título válido aquí",
                descripcion="Descripción válida con suficientes caracteres.",
            ))

    def test_limite_tickets_plan_basico(self):
        m = mocks_cliente()
        c = cliente_fixture(plan=PlanCliente.BASICO)
        self._setup_token(m, c)
        m["tickets"].contar_abiertos_por_cliente.return_value = 2  # ya tiene 2, límite es 2

        with self.assertRaises(LimiteTicketsPlanExcedido):
            self._uc(m).ejecutar("token-ok", CrearTicketDTO(
                tipo_servicio="SOPORTE_REMOTO",
                titulo="Otro problema urgente",
                descripcion="Descripción válida con suficientes caracteres.",
            ))

    def test_tipo_servicio_invalido_lanza_error(self):
        m = mocks_cliente()
        c = cliente_fixture()
        self._setup_token(m, c)
        with self.assertRaises(ValueError):
            self._uc(m).ejecutar("token-ok", CrearTicketDTO(
                tipo_servicio="SERVICIO_INVALIDO",
                titulo="Título válido aquí",
                descripcion="Descripción válida con suficientes caracteres.",
            ))


# ================================================================
# TESTS: ACTUALIZAR TICKET
# ================================================================
class TestActualizarTicket(unittest.TestCase):

    def _uc(self, m):
        return ActualizarTicketUseCase(
            tickets=m["tickets"], tecnicos=m["tecnicos"], clientes=m["clientes"],
            tokens=m["tokens"], notificaciones=m["notificaciones"], auditoria=m["auditoria"],
        )

    def test_actualizar_a_en_proceso(self):
        m = mocks_cliente()
        tec = tecnico_fixture()
        c   = cliente_fixture()
        t   = ticket_fixture(c.id, estado=EstadoTicket.ASIGNADO)
        t.tecnico_id = tec.id

        m["tokens"].verificar_token.return_value = {"usuario_id": tec.id, "tipo": "tecnico"}
        m["tecnicos"].buscar_por_id.return_value = tec
        m["tickets"].buscar_por_id.return_value = t

        resultado = self._uc(m).ejecutar("token-tec", ActualizarTicketDTO(
            ticket_id=t.id, nuevo_estado="EN_PROCESO",
        ))

        self.assertEqual(resultado.estado, "EN_PROCESO")
        m["tickets"].actualizar.assert_called_once()

    def test_resolver_con_diagnostico(self):
        m = mocks_cliente()
        tec = tecnico_fixture()
        c   = cliente_fixture()
        t   = ticket_fixture(c.id, estado=EstadoTicket.EN_PROCESO)
        t.tecnico_id = tec.id

        m["tokens"].verificar_token.return_value = {"usuario_id": tec.id, "tipo": "tecnico"}
        m["tecnicos"].buscar_por_id.return_value = tec
        m["tickets"].buscar_por_id.return_value = t
        m["clientes"].buscar_por_id.return_value = c

        resultado = self._uc(m).ejecutar("token-tec", ActualizarTicketDTO(
            ticket_id=t.id, nuevo_estado="RESUELTO",
            diagnostico="Fuente de poder quemada",
            solucion="Reemplazo de fuente de poder",
            costo_final=130_000.0,
        ))

        self.assertEqual(resultado.estado, "RESUELTO")
        m["notificaciones"].enviar_ticket_resuelto.assert_called_once()

    def test_resolver_sin_diagnostico_lanza_error(self):
        m = mocks_cliente()
        tec = tecnico_fixture()
        c   = cliente_fixture()
        t   = ticket_fixture(c.id, estado=EstadoTicket.EN_PROCESO)
        t.tecnico_id = tec.id

        m["tokens"].verificar_token.return_value = {"usuario_id": tec.id, "tipo": "tecnico"}
        m["tecnicos"].buscar_por_id.return_value = tec
        m["tickets"].buscar_por_id.return_value = t

        with self.assertRaises(DiagnosticoRequerido):
            self._uc(m).ejecutar("token-tec", ActualizarTicketDTO(
                ticket_id=t.id, nuevo_estado="RESUELTO",
            ))

    def test_tecnico_no_autorizado(self):
        m = mocks_cliente()
        tec = tecnico_fixture()  # técnico SIN el ticket asignado
        c   = cliente_fixture()
        t   = ticket_fixture(c.id)
        t.tecnico_id = "otro-tecnico-id"  # asignado a otro

        m["tokens"].verificar_token.return_value = {"usuario_id": tec.id, "tipo": "tecnico"}
        m["tecnicos"].buscar_por_id.return_value = tec
        m["tickets"].buscar_por_id.return_value = t

        with self.assertRaises(AccesoNoAutorizado):
            self._uc(m).ejecutar("token-tec", ActualizarTicketDTO(
                ticket_id=t.id, nuevo_estado="EN_PROCESO",
            ))

    def test_admin_puede_modificar_cualquier_ticket(self):
        m = mocks_cliente()
        admin = tecnico_fixture(rol=RolTecnico.ADMIN)
        c     = cliente_fixture()
        t     = ticket_fixture(c.id, estado=EstadoTicket.ASIGNADO)
        t.tecnico_id = "otro-tecnico-id"

        m["tokens"].verificar_token.return_value = {"usuario_id": admin.id, "tipo": "tecnico"}
        m["tecnicos"].buscar_por_id.return_value = admin
        m["tickets"].buscar_por_id.return_value = t

        resultado = self._uc(m).ejecutar("token-admin", ActualizarTicketDTO(
            ticket_id=t.id, nuevo_estado="EN_PROCESO",
        ))
        self.assertEqual(resultado.estado, "EN_PROCESO")


# ================================================================
# TESTS: CALIFICAR TICKET
# ================================================================
class TestCalificarTicket(unittest.TestCase):

    def _uc(self, m):
        return CalificarTicketUseCase(
            tickets=m["tickets"], tecnicos=m["tecnicos"], clientes=m["clientes"],
            tokens=m["tokens"], auditoria=m["auditoria"],
        )

    def test_calificar_exitoso(self):
        m = mocks_cliente()
        c   = cliente_fixture()
        tec = tecnico_fixture()
        t   = ticket_fixture(c.id, estado=EstadoTicket.RESUELTO)
        t.tecnico_id = tec.id

        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        m["tickets"].buscar_por_id.return_value = t
        m["tecnicos"].buscar_por_id.return_value = tec

        self._uc(m).ejecutar("token-cli", CalificarTicketDTO(t.id, 4.5))

        self.assertEqual(t.calificacion, 4.5)
        m["tickets"].actualizar.assert_called_once()
        m["tecnicos"].actualizar.assert_called_once()

    def test_calificar_ticket_de_otro_cliente(self):
        m = mocks_cliente()
        c = cliente_fixture()
        t = ticket_fixture("otro-cliente-id", estado=EstadoTicket.RESUELTO)

        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        m["tickets"].buscar_por_id.return_value = t

        with self.assertRaises(AccesoNoAutorizado):
            self._uc(m).ejecutar("token-cli", CalificarTicketDTO(t.id, 4.0))

    def test_nota_invalida_lanza_error_en_dto(self):
        with self.assertRaises(ValueError):
            CalificarTicketDTO(ticket_id="alguno", nota=6.0)


# ================================================================
# TESTS: MIS TICKETS
# ================================================================
class TestMisTickets(unittest.TestCase):

    def _uc(self, m):
        return MisTicketsUseCase(tickets=m["tickets"], tecnicos=m["tecnicos"], tokens=m["tokens"])

    def test_lista_tickets_del_cliente(self):
        m = mocks_cliente()
        c = cliente_fixture()
        t1 = ticket_fixture(c.id)
        t2 = ticket_fixture(c.id, estado=EstadoTicket.RESUELTO)

        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        m["tickets"].listar_por_cliente.return_value = [t1, t2]
        m["tecnicos"].buscar_por_id.return_value = None

        resultado = self._uc(m).ejecutar("token-cli")

        self.assertEqual(resultado.total, 2)
        self.assertEqual(resultado.abiertos, 1)
        self.assertEqual(resultado.resueltos, 1)

    def test_filtro_estado_valido(self):
        m = mocks_cliente()
        c = cliente_fixture()
        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        m["tickets"].listar_por_cliente.return_value = []

        resultado = self._uc(m).ejecutar("token-cli", estado="NUEVO")
        m["tickets"].listar_por_cliente.assert_called_with(c.id, EstadoTicket.NUEVO)

    def test_filtro_estado_invalido_lanza_error(self):
        m = mocks_cliente()
        c = cliente_fixture()
        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        with self.assertRaises(ValueError):
            self._uc(m).ejecutar("token-cli", estado="ESTADO_INVENTADO")


# ================================================================
# TESTS: CREAR ALQUILER
# ================================================================
class TestCrearAlquiler(unittest.TestCase):

    def _uc(self, m):
        return CrearAlquilerUseCase(
            clientes=m["clientes"], alquileres=m["alquileres"],
            tokens=m["tokens"], notificaciones=m["notificaciones"], auditoria=m["auditoria"],
        )

    def test_alquiler_exitoso(self):
        m = mocks_cliente()
        c = cliente_fixture()
        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        m["clientes"].buscar_por_id.return_value = c

        resultado = self._uc(m).ejecutar("token-ok", CrearAlquilerDTO(
            equipo_tipo="laptop",
            fecha_inicio="2026-04-01",
            fecha_fin="2026-04-08",
            costo_diario=35_000,
        ))

        self.assertEqual(resultado.equipo_tipo, "laptop")
        self.assertEqual(resultado.dias, 7)
        self.assertEqual(resultado.costo_total, 225_400.0)   # 7 días con dcto 8%
        self.assertEqual(resultado.deposito, 67_620.0)       # 30% del total
        m["alquileres"].guardar.assert_called_once()
        m["notificaciones"].enviar_confirmacion_alquiler.assert_called_once()

    def test_equipo_tipo_invalido(self):
        m = mocks_cliente()
        c = cliente_fixture()
        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        m["clientes"].buscar_por_id.return_value = c

        with self.assertRaises(ValueError):
            self._uc(m).ejecutar("token-ok", CrearAlquilerDTO(
                equipo_tipo="dron", fecha_inicio="2026-04-01",
                fecha_fin="2026-04-04", costo_diario=35_000,
            ))

    def test_plan_basico_max_30_dias(self):
        m = mocks_cliente()
        c = cliente_fixture(plan=PlanCliente.BASICO)
        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        m["clientes"].buscar_por_id.return_value = c

        from techsupportpro.domain.exceptions import LimiteAlquilerPlanExcedido
        with self.assertRaises(LimiteAlquilerPlanExcedido):
            self._uc(m).ejecutar("token-ok", CrearAlquilerDTO(
                equipo_tipo="laptop", fecha_inicio="2026-04-01",
                fecha_fin="2026-05-02",  # 31 días
                costo_diario=35_000,
            ))


# ================================================================
# TESTS: PROCESAR PAGO
# ================================================================
class TestProcesarPago(unittest.TestCase):

    def _uc(self, m):
        return ProcesarPagoUseCase(
            clientes=m["clientes"], pagos=m["pagos"], tokens=m["tokens"],
            pasarela=m["pasarela"], notificaciones=m["notificaciones"], auditoria=m["auditoria"],
        )

    def test_pago_nequi_exitoso(self):
        m = mocks_cliente()
        c = cliente_fixture()
        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        m["clientes"].buscar_por_id.return_value = c

        resultado = self._uc(m).ejecutar("token-ok", ProcesarPagoDTO(
            monto=45_000, metodo="nequi", ticket_id="ticket-001",
        ))

        self.assertEqual(resultado.monto, 45_000.0)
        self.assertEqual(resultado.metodo, "nequi")
        self.assertEqual(resultado.estado, "confirmado")
        m["pasarela"].procesar_tarjeta.assert_not_called()

    def test_pago_tarjeta_usa_pasarela(self):
        m = mocks_cliente()
        c = cliente_fixture()
        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        m["clientes"].buscar_por_id.return_value = c
        m["pasarela"].procesar_tarjeta.return_value = "WOMPI-REF-12345"

        resultado = self._uc(m).ejecutar("token-ok", ProcesarPagoDTO(
            monto=85_000, metodo="tarjeta_credito",
            ticket_id="ticket-001", token_tarjeta="tok_test_123",
        ))

        self.assertEqual(resultado.referencia_externa, "WOMPI-REF-12345")
        m["pasarela"].procesar_tarjeta.assert_called_once()

    def test_metodo_invalido_lanza_error(self):
        m = mocks_cliente()
        c = cliente_fixture()
        m["tokens"].verificar_token.return_value = {"usuario_id": c.id, "tipo": "cliente"}
        m["clientes"].buscar_por_id.return_value = c

        with self.assertRaises(ValueError):
            self._uc(m).ejecutar("token-ok", ProcesarPagoDTO(
                monto=50_000, metodo="bitcoin", ticket_id="t-001",
            ))

    def test_monto_cero_lanza_error_en_dto(self):
        with self.assertRaises(ValueError):
            ProcesarPagoDTO(monto=0, metodo="nequi", ticket_id="t-001")


# ================================================================
# TESTS: DASHBOARD ADMIN
# ================================================================
class TestDashboardAdmin(unittest.TestCase):

    def _uc(self, m):
        return DashboardAdminUseCase(
            tickets=m["tickets"], clientes=m["clientes"], tecnicos=m["tecnicos"],
            pagos=m["pagos"], tokens=m["tokens"],
        )

    def test_dashboard_para_admin(self):
        m = mocks_cliente()
        admin = tecnico_fixture(rol=RolTecnico.ADMIN)
        m["tokens"].verificar_token.return_value = {"usuario_id": admin.id, "tipo": "tecnico"}
        m["tecnicos"].buscar_por_id.return_value = admin
        m["tickets"].contar_total.return_value = 100
        m["tickets"].contar_por_estado.side_effect = [10, 25, 60]  # nuevos, proceso, resueltos
        m["clientes"].contar_activos.return_value = 45
        m["tecnicos"].contar_activos.return_value = 8
        m["pagos"].sumar_ingresos_desde.return_value = COP.de_pesos(5_000_000)

        resultado = self._uc(m).ejecutar("token-admin")

        self.assertEqual(resultado.tickets_total, 100)
        self.assertEqual(resultado.tickets_nuevos, 10)
        self.assertEqual(resultado.tickets_resueltos, 60)
        self.assertEqual(resultado.tasa_resolucion_pct, 60.0)
        self.assertEqual(resultado.ingresos_mes_cop, 5_000_000.0)

    def test_tecnico_sin_rol_admin_lanza_error(self):
        m = mocks_cliente()
        tec = tecnico_fixture(rol=RolTecnico.TECNICO)
        m["tokens"].verificar_token.return_value = {"usuario_id": tec.id, "tipo": "tecnico"}
        m["tecnicos"].buscar_por_id.return_value = tec

        with self.assertRaises(AccesoNoAutorizado):
            self._uc(m).ejecutar("token-tec")

    def test_token_de_cliente_lanza_error(self):
        m = mocks_cliente()
        m["tokens"].verificar_token.return_value = {"usuario_id": "alguien", "tipo": "cliente"}

        with self.assertRaises(TokenInvalidoOExpirado):
            self._uc(m).ejecutar("token-cli")


# ─── RUNNER ─────────────────────────────────────────────────────
if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [
        TestRegistrarCliente, TestLoginCliente, TestCrearTicket,
        TestActualizarTicket, TestCalificarTicket, TestMisTickets,
        TestCrearAlquiler, TestProcesarPago, TestDashboardAdmin,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    import sys; sys.exit(0 if result.wasSuccessful() else 1)
