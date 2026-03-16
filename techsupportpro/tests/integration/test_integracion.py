"""
Tests de integración — Fase 4.

Usan adaptadores REALES en memoria (Fakes), no Mocks.
Esto verifica que los casos de uso orquestan correctamente
con implementaciones concretas de los puertos.

La diferencia con los tests unitarios de Fase 3:
  Fase 3: MagicMock()  → verifica que el UC llama los métodos correctos
  Fase 4: FakeAdapter  → verifica que el flujo completo produce resultados reales
"""
import sys, os, unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from techsupportpro.config import Contenedor
from techsupportpro.application.dtos import (
    RegistrarClienteDTO, LoginDTO, CrearTicketDTO, ActualizarTicketDTO,
    CalificarTicketDTO, CrearAlquilerDTO, ProcesarPagoDTO,
)
from techsupportpro.domain.entities import (
    Tecnico, TipoServicio, RolTecnico, EstadoTicket,
)
from techsupportpro.domain.value_objects import (
    Email, PasswordHash, NombrePersona,
)
from techsupportpro.domain.exceptions import (
    EmailYaRegistrado, CredencialesInvalidas, TokenInvalidoOExpirado,
    LimiteTicketsPlanExcedido,
)


def crear_contenedor() -> Contenedor:
    return Contenedor.crear(modo="memoria")

def registrar_cliente(c, nombre="Carlos Muñoz", email="carlos@empresa.com",
                       password="TechPro123"):
    return c.registrar_cliente.ejecutar(RegistrarClienteDTO(
        nombre=nombre, email=email, password=password,
    ))

def agregar_tecnico(c) -> Tecnico:
    """Agrega un técnico directamente al repositorio (simula alta desde admin)."""
    tec = Tecnico.crear(
        nombre=NombrePersona("Ana García"),
        email=Email("ana@tech.com"),
        password_hash=PasswordHash("s:TechPro123"),
        rol=RolTecnico.TECNICO,
        especialidades=[TipoServicio.SOPORTE_REMOTO, TipoServicio.REPARACION_PC],
    )
    tec.disponible = True
    c._tecnicos.guardar(tec)
    return tec

def agregar_admin(c) -> Tecnico:
    admin = Tecnico.crear(
        nombre=NombrePersona("Luis Admin"),
        email=Email("admin@tech.com"),
        password_hash=PasswordHash("s:Admin123"),
        rol=RolTecnico.ADMIN,
        especialidades=[],
    )
    admin.disponible = True
    c._tecnicos.guardar(admin)
    return admin


# ================================================================
# INTEGRACIÓN: FLUJO COMPLETO REGISTRO → LOGIN → TICKET
# ================================================================
class TestFlujoCompletoTicket(unittest.TestCase):

    def test_registro_login_crear_ticket(self):
        """Flujo feliz completo: registro → login → ticket → resolución → calificación."""
        c = crear_contenedor()
        tec = agregar_tecnico(c)

        # 1. Registrar cliente
        cliente_dto = registrar_cliente(c)
        self.assertEqual(cliente_dto.email, "carlos@empresa.com")
        self.assertTrue(cliente_dto.codigo_cliente.startswith("CLI-"))

        # 2. Login — TokenServiceMemoria genera "cliente:{id}"
        login = c.login_cliente.ejecutar(LoginDTO("carlos@empresa.com", "TechPro123"))
        self.assertTrue(login.token.startswith("cliente:"))
        self.assertEqual(login.plan, "basico")

        # 3. Crear ticket — se auto-asigna si hay técnico disponible
        token = login.token
        ticket = c.crear_ticket.ejecutar(token, CrearTicketDTO(
            tipo_servicio="SOPORTE_REMOTO",
            titulo="PC no enciende",
            descripcion="El equipo no enciende desde esta mañana después de la tormenta.",
            prioridad="MEDIA",
        ))
        # Con técnico disponible el ticket queda ASIGNADO automáticamente
        self.assertIn(ticket.estado, ("NUEVO", "ASIGNADO"))
        self.assertEqual(ticket.costo_estimado, 45_000.0)
        self.assertTrue(ticket.numero.startswith("TSP-"))

        # 4. El técnico actualiza a EN_PROCESO
        token_tec = f"tecnico:{tec.id}"
        # primero ASIGNADO (el ticket ya se asignó automáticamente)
        ticket_id = ticket.id
        c.actualizar_ticket.ejecutar(token_tec, ActualizarTicketDTO(
            ticket_id=ticket_id, nuevo_estado="EN_PROCESO",
        ))

        # 5. Resolver con diagnóstico
        resultado = c.actualizar_ticket.ejecutar(token_tec, ActualizarTicketDTO(
            ticket_id=ticket_id, nuevo_estado="RESUELTO",
            diagnostico="Fuente de poder dañada",
            solucion="Reemplazo de fuente de poder",
            costo_final=45_000.0,
        ))
        self.assertEqual(resultado.estado, "RESUELTO")

        # 6. Cliente califica
        c.calificar_ticket.ejecutar(token, CalificarTicketDTO(ticket_id, 5.0))

        # 7. Verificar notificaciones
        notifs = c._notificaciones.log
        tipos = [n["tipo"] for n in notifs]
        self.assertIn("bienvenida", tipos)
        self.assertIn("ticket_creado", tipos)
        self.assertIn("ticket_resuelto", tipos)

        # 8. Verificar auditoría
        eventos = c._auditoria.eventos
        acciones = [e["accion"] for e in eventos]
        self.assertIn("REGISTRO", acciones)
        self.assertIn("LOGIN", acciones)
        self.assertIn("TICKET_CREADO", acciones)

    def test_mis_tickets_refleja_estado_real(self):
        """Los tickets creados aparecen en mis-tickets con métricas correctas."""
        c = crear_contenedor()
        agregar_tecnico(c)
        registrar_cliente(c)
        login = c.login_cliente.ejecutar(LoginDTO("carlos@empresa.com", "TechPro123"))
        token = login.token

        # Crear 2 tickets
        for titulo in ["Problema impresora", "Red caída"]:
            c.crear_ticket.ejecutar(token, CrearTicketDTO(
                tipo_servicio="SOPORTE_REMOTO", titulo=titulo,
                descripcion="Descripción del problema técnico reportado.",
            ))

        lista = c.mis_tickets.ejecutar(token)
        self.assertEqual(lista.total, 2)
        self.assertEqual(lista.abiertos, 2)
        self.assertEqual(lista.resueltos, 0)

    def test_limite_tickets_plan_basico_integrado(self):
        """Plan básico: máximo 2 tickets abiertos simultáneos."""
        c = crear_contenedor()
        agregar_tecnico(c)
        registrar_cliente(c)
        login = c.login_cliente.ejecutar(LoginDTO("carlos@empresa.com", "TechPro123"))
        token = login.token

        for i in range(2):
            c.crear_ticket.ejecutar(token, CrearTicketDTO(
                tipo_servicio="SOPORTE_REMOTO",
                titulo=f"Ticket {i+1}",
                descripcion="Descripción del problema técnico reportado.",
            ))

        with self.assertRaises(LimiteTicketsPlanExcedido):
            c.crear_ticket.ejecutar(token, CrearTicketDTO(
                tipo_servicio="SOPORTE_REMOTO",
                titulo="Ticket 3 — debe fallar",
                descripcion="Descripción del problema técnico reportado.",
            ))


# ================================================================
# INTEGRACIÓN: ALQUILER COMPLETO
# ================================================================
class TestFlujoAlquiler(unittest.TestCase):

    def test_crear_y_devolver_alquiler(self):
        c = crear_contenedor()
        registrar_cliente(c)
        login = c.login_cliente.ejecutar(LoginDTO("carlos@empresa.com", "TechPro123"))
        token = login.token

        alquiler = c.crear_alquiler.ejecutar(token, CrearAlquilerDTO(
            equipo_tipo="laptop",
            fecha_inicio="2026-05-01",
            fecha_fin="2026-05-08",   # 7 días → descuento 8%
            costo_diario=35_000,
        ))
        self.assertEqual(alquiler.dias, 7)
        self.assertEqual(alquiler.estado, "activo")
        # 7 días × 35.000 × 0.92 = 225.400
        self.assertAlmostEqual(alquiler.costo_total, 225_400.0)
        # depósito = 30% del total
        self.assertAlmostEqual(alquiler.deposito, 67_620.0)

        # Devolver
        devuelto = c.devolver_alquiler.ejecutar(token, alquiler.id)
        self.assertEqual(devuelto.estado, "devuelto")

        # Verificar notificación
        tipos = [n["tipo"] for n in c._notificaciones.log]
        self.assertIn("alquiler_confirmado", tipos)

    def test_alquiler_persiste_en_repositorio(self):
        """Verificación directa del repositorio — el alquiler queda guardado."""
        c = crear_contenedor()
        registrar_cliente(c)
        login = c.login_cliente.ejecutar(LoginDTO("carlos@empresa.com", "TechPro123"))
        token = login.token

        alquiler_dto = c.crear_alquiler.ejecutar(token, CrearAlquilerDTO(
            equipo_tipo="impresora",
            fecha_inicio="2026-06-01",
            fecha_fin="2026-06-05",
            costo_diario=25_000,
        ))

        # Acceder directamente al repositorio para verificar persistencia
        alquiler_guardado = c._alquileres.buscar_por_id(alquiler_dto.id)
        self.assertIsNotNone(alquiler_guardado)
        self.assertEqual(alquiler_guardado.equipo_tipo, "impresora")


# ================================================================
# INTEGRACIÓN: PAGO COMPLETO
# ================================================================
class TestFlujoPago(unittest.TestCase):

    def test_pago_nequi_flujo_completo(self):
        c = crear_contenedor()
        agregar_tecnico(c)
        registrar_cliente(c)
        login = c.login_cliente.ejecutar(LoginDTO("carlos@empresa.com", "TechPro123"))
        token = login.token

        ticket = c.crear_ticket.ejecutar(token, CrearTicketDTO(
            tipo_servicio="SOPORTE_REMOTO",
            titulo="PC no enciende",
            descripcion="Descripción del problema técnico reportado.",
        ))

        pago = c.procesar_pago.ejecutar(token, ProcesarPagoDTO(
            monto=45_000, metodo="nequi", ticket_id=ticket.id,
        ))
        self.assertEqual(pago.estado, "confirmado")
        self.assertEqual(pago.monto, 45_000.0)
        self.assertTrue(pago.referencia_externa.startswith("REF-"))

    def test_pago_tarjeta_usa_pasarela_fake(self):
        c = crear_contenedor()
        agregar_tecnico(c)
        registrar_cliente(c)
        login = c.login_cliente.ejecutar(LoginDTO("carlos@empresa.com", "TechPro123"))
        token = login.token

        ticket = c.crear_ticket.ejecutar(token, CrearTicketDTO(
            tipo_servicio="SOPORTE_REMOTO",
            titulo="PC no enciende",
            descripcion="Descripción del problema técnico reportado.",
        ))

        pago = c.procesar_pago.ejecutar(token, ProcesarPagoDTO(
            monto=45_000, metodo="tarjeta_credito",
            ticket_id=ticket.id, token_tarjeta="tok_test_visa",
        ))
        self.assertTrue(pago.referencia_externa.startswith("WOMPI-FAKE-"))
        # Verificar que la pasarela registró la transacción
        self.assertEqual(len(c._pasarela.transacciones), 1)


# ================================================================
# INTEGRACIÓN: DASHBOARD ADMIN
# ================================================================
class TestDashboardIntegrado(unittest.TestCase):

    def test_dashboard_refleja_datos_reales(self):
        """El dashboard lee del repositorio real, no de mocks."""
        c = crear_contenedor()
        tec = agregar_tecnico(c)
        admin = agregar_admin(c)

        # Crear 2 clientes con tickets
        for nombre, email in [("Ana Torres", "ana@test.com"), ("Pedro Ruiz", "pedro@test.com")]:
            registrar_cliente(c, nombre=nombre, email=email)
            login = c.login_cliente.ejecutar(LoginDTO(email, "TechPro123"))
            c.crear_ticket.ejecutar(login.token, CrearTicketDTO(
                tipo_servicio="SOPORTE_REMOTO",
                titulo=f"Problema de red empresarial",
                descripcion="Descripción del problema técnico reportado.",
            ))

        token_admin = f"tecnico:{admin.id}"
        dash = c.dashboard_admin.ejecutar(token_admin)

        self.assertEqual(dash.tickets_total, 2)
        self.assertEqual(dash.tickets_nuevos, 0)  # se asignaron al técnico
        self.assertEqual(dash.clientes_activos, 0)  # no verificados aún
        self.assertEqual(dash.tecnicos_activos, 2)  # tec + admin


# ================================================================
# INTEGRACIÓN: MODO JSON — mismo flujo, diferente repositorio
# ================================================================
class TestModoJSON(unittest.TestCase):

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_flujo_completo_persiste_en_json(self):
        """Demuestra evolución: mismo flujo, distinto adaptador."""
        os.environ["JSON_DATA_DIR"] = self._tmpdir
        c = Contenedor.crear(modo="json")
        agregar_tecnico(c)

        registrar_cliente(c)
        login = c.login_cliente.ejecutar(LoginDTO("carlos@empresa.com", "TechPro123"))
        ticket = c.crear_ticket.ejecutar(login.token, CrearTicketDTO(
            tipo_servicio="SOPORTE_REMOTO",
            titulo="PC no enciende",
            descripcion="Descripción del problema técnico reportado.",
        ))

        # Verificar archivos JSON creados en disco
        archivos = os.listdir(self._tmpdir)
        self.assertIn("clientes.json", archivos)
        self.assertIn("tickets.json", archivos)

        # Verificar contenido del JSON
        with open(os.path.join(self._tmpdir, "tickets.json")) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(list(data.values())[0]["titulo"], "PC no enciende")

    def test_persistencia_sobrevive_nuevo_contenedor(self):
        """Crear un contenedor nuevo con el mismo directorio recupera los datos."""
        import json as _json
        os.environ["JSON_DATA_DIR"] = self._tmpdir
        c1 = Contenedor.crear(modo="json")
        agregar_tecnico(c1)
        registrar_cliente(c1)

        # Nuevo contenedor — misma carpeta
        c2 = Contenedor.crear(modo="json")
        cliente_recuperado = c2._clientes.buscar_por_email(Email("carlos@empresa.com"))
        self.assertIsNotNone(cliente_recuperado)
        self.assertEqual(str(cliente_recuperado.nombre), "Carlos Muñoz")


import json

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [
        TestFlujoCompletoTicket, TestFlujoAlquiler,
        TestFlujoPago, TestDashboardIntegrado, TestModoJSON,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
