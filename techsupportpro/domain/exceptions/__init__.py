"""
Excepciones del dominio TechSupport Pro.
Cada excepción describe con precisión qué regla de negocio fue violada.
Sin dependencias de HTTP ni infraestructura.
"""


class DomainError(Exception):
    """Base para todas las excepciones del dominio."""
    pass


# ── CLIENTE ──────────────────────────────────────────────────────
class ClienteNoEncontrado(DomainError):
    def __init__(self, cliente_id: str):
        super().__init__(f"Cliente no encontrado: {cliente_id}")
        self.cliente_id = cliente_id


class EmailYaRegistrado(DomainError):
    def __init__(self, email: str):
        super().__init__(f"Ya existe una cuenta registrada con el email: {email}")
        self.email = email


class ClienteSuspendido(DomainError):
    def __init__(self, cliente_id: str):
        super().__init__(f"La cuenta del cliente está suspendida: {cliente_id}")
        self.cliente_id = cliente_id


class CredencialesInvalidas(DomainError):
    def __init__(self):
        super().__init__("Credenciales inválidas")


class LimiteTicketsPlanExcedido(DomainError):
    def __init__(self, plan: str, limite: int, actuales: int):
        super().__init__(
            f"Plan '{plan}': límite de {limite} tickets simultáneos alcanzado "
            f"({actuales} activos). Actualiza tu plan para más capacidad."
        )
        self.plan    = plan
        self.limite  = limite
        self.actuales = actuales


# ── TICKET ───────────────────────────────────────────────────────
class TicketNoEncontrado(DomainError):
    def __init__(self, ticket_id: str):
        super().__init__(f"Ticket no encontrado: {ticket_id}")
        self.ticket_id = ticket_id


class TransicionDeEstadoInvalida(DomainError):
    def __init__(self, estado_actual: str, estado_destino: str):
        super().__init__(
            f"No se puede transicionar de '{estado_actual}' a '{estado_destino}'"
        )
        self.estado_actual  = estado_actual
        self.estado_destino = estado_destino


class DiagnosticoRequerido(DomainError):
    def __init__(self):
        super().__init__("Se requiere diagnóstico para marcar el ticket como RESUELTO")


class TecnicoNoAutorizado(DomainError):
    def __init__(self, tecnico_id: str, ticket_id: str):
        super().__init__(
            f"El técnico '{tecnico_id}' no está autorizado para modificar "
            f"el ticket '{ticket_id}'"
        )


class TicketYaCalificado(DomainError):
    def __init__(self, ticket_id: str):
        super().__init__(f"El ticket '{ticket_id}' ya fue calificado")


class TicketNoResuelto(DomainError):
    def __init__(self, ticket_id: str, estado: str):
        super().__init__(
            f"Solo se pueden calificar tickets resueltos. "
            f"El ticket '{ticket_id}' está en estado '{estado}'"
        )


# ── ALQUILER ─────────────────────────────────────────────────────
class AlquilerNoEncontrado(DomainError):
    def __init__(self, alquiler_id: str):
        super().__init__(f"Alquiler no encontrado: {alquiler_id}")


class LimiteAlquilerPlanExcedido(DomainError):
    def __init__(self, plan: str, max_dias: int, dias_solicitados: int):
        super().__init__(
            f"Plan '{plan}': máximo {max_dias} días de alquiler. "
            f"Solicitaste {dias_solicitados} días. Actualiza tu plan."
        )
        self.plan             = plan
        self.max_dias         = max_dias
        self.dias_solicitados = dias_solicitados


class CostoDiarioMinimoViolado(DomainError):
    def __init__(self, minimo: float, recibido: float):
        super().__init__(
            f"El costo diario mínimo de alquiler es ${minimo:,.0f} COP. "
            f"Recibido: ${recibido:,.0f} COP"
        )


class AlquilerActivoYaExiste(DomainError):
    def __init__(self, plan: str):
        super().__init__(
            f"Plan '{plan}': solo se permite 1 alquiler activo simultáneo. "
            "Devuelve el equipo actual o actualiza tu plan."
        )


# ── PAGO ─────────────────────────────────────────────────────────
class MontoInvalido(DomainError):
    def __init__(self, monto: float, minimo: float):
        super().__init__(
            f"El monto ${monto:,.0f} COP es inválido. "
            f"Mínimo permitido: ${minimo:,.0f} COP"
        )


class MetodoPagoInvalido(DomainError):
    def __init__(self, metodo: str, validos: list[str]):
        super().__init__(
            f"Método de pago '{metodo}' no válido. "
            f"Métodos aceptados: {', '.join(validos)}"
        )


# ── AUTENTICACIÓN ────────────────────────────────────────────────
class TokenInvalidoOExpirado(DomainError):
    def __init__(self):
        super().__init__("Token de sesión inválido o expirado")


class SesionNoEncontrada(DomainError):
    def __init__(self):
        super().__init__("No se encontró una sesión activa")


class AccesoNoAutorizado(DomainError):
    def __init__(self, razon: str = ""):
        msg = "Acceso no autorizado"
        if razon:
            msg += f": {razon}"
        super().__init__(msg)
        self.razon = razon


# ── TÉCNICO ──────────────────────────────────────────────────────
class TecnicoNoEncontrado(DomainError):
    def __init__(self, tecnico_id: str):
        super().__init__(f"Técnico no encontrado: {tecnico_id}")


class NoHayTecnicosDisponibles(DomainError):
    def __init__(self):
        super().__init__(
            "No hay técnicos disponibles en este momento. "
            "El ticket quedará en estado NUEVO hasta que se asigne manualmente."
        )
