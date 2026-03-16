"""
Entidades del dominio TechSupport Pro.
Clases Python puras — sin ORM, sin FastAPI, sin infraestructura.
Toda la lógica de negocio que estaba dispersa en main.py vive aquí.
"""
from __future__ import annotations
import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from techsupportpro.domain.value_objects import (
    Email, PasswordHash, COP, Periodo, NombrePersona, TelefonoColombia
)
from techsupportpro.domain.exceptions import (
    TransicionDeEstadoInvalida, DiagnosticoRequerido,
    LimiteTicketsPlanExcedido, LimiteAlquilerPlanExcedido,
    TicketYaCalificado, TicketNoResuelto,
)


# ================================================================
# ENUMERACIONES DEL DOMINIO
# ================================================================
class TipoServicio(enum.Enum):
    SOPORTE_PRESENCIAL   = "SOPORTE_PRESENCIAL"
    SOPORTE_REMOTO       = "SOPORTE_REMOTO"
    REPARACION_PC        = "REPARACION_PC"
    REPARACION_LAPTOP    = "REPARACION_LAPTOP"
    REPARACION_IMPRESORA = "REPARACION_IMPRESORA"
    MANTENIMIENTO_PREV   = "MANTENIMIENTO_PREV"
    ALQUILER_EQUIPO      = "ALQUILER_EQUIPO"
    DESARROLLO_SOFTWARE  = "DESARROLLO_SOFTWARE"
    REDES_INFRAESTRUCTURA = "REDES_INFRAESTRUCTURA"
    CONSULTORIA_TI       = "CONSULTORIA_TI"


class EstadoTicket(enum.Enum):
    NUEVO       = "NUEVO"
    ASIGNADO    = "ASIGNADO"
    DIAGNOSTICO = "DIAGNOSTICO"
    EN_PROCESO  = "EN_PROCESO"
    EN_ESPERA   = "EN_ESPERA"
    RESUELTO    = "RESUELTO"
    CERRADO     = "CERRADO"
    CANCELADO   = "CANCELADO"

    # Máquina de estados encapsulada — antes estaba en el controlador
    _TRANSICIONES: dict = {}

    @classmethod
    def transiciones_validas(cls) -> dict[EstadoTicket, list[EstadoTicket]]:
        return {
            cls.NUEVO:       [cls.ASIGNADO, cls.CANCELADO],
            cls.ASIGNADO:    [cls.DIAGNOSTICO, cls.EN_PROCESO, cls.CANCELADO],
            cls.DIAGNOSTICO: [cls.EN_PROCESO, cls.EN_ESPERA, cls.CANCELADO],
            cls.EN_PROCESO:  [cls.EN_ESPERA, cls.RESUELTO, cls.CANCELADO],
            cls.EN_ESPERA:   [cls.EN_PROCESO, cls.CANCELADO],
            cls.RESUELTO:    [cls.CERRADO],
            cls.CERRADO:     [],
            cls.CANCELADO:   [],
        }

    def puede_transicionar_a(self, destino: EstadoTicket) -> bool:
        return destino in self.transiciones_validas().get(self, [])


class Prioridad(enum.Enum):
    BAJA    = "BAJA"
    MEDIA   = "MEDIA"
    ALTA    = "ALTA"
    CRITICA = "CRITICA"

    def factor_recargo(self) -> float:
        """Recargo sobre el costo base — antes hardcoded en el controlador."""
        return {
            Prioridad.BAJA:    1.00,
            Prioridad.MEDIA:   1.00,
            Prioridad.ALTA:    1.35,
            Prioridad.CRITICA: 1.70,
        }[self]


class PlanCliente(enum.Enum):
    BASICO      = "basico"
    PROFESIONAL = "profesional"
    EMPRESARIAL = "empresarial"

    def limite_tickets_simultaneos(self) -> int:
        """Regla de negocio antes hardcoded en el controlador."""
        return {
            PlanCliente.BASICO:      2,
            PlanCliente.PROFESIONAL: 8,
            PlanCliente.EMPRESARIAL: 999,  # ilimitado
        }[self]

    def limite_dias_alquiler(self) -> int:
        return {
            PlanCliente.BASICO:       30,
            PlanCliente.PROFESIONAL:  90,
            PlanCliente.EMPRESARIAL: 365,
        }[self]

    def descuento_servicios(self) -> float:
        return {
            PlanCliente.BASICO:      0.00,
            PlanCliente.PROFESIONAL: 0.15,
            PlanCliente.EMPRESARIAL: 0.25,
        }[self]

    def limite_alquileres_simultaneos(self) -> int:
        return {
            PlanCliente.BASICO:      1,
            PlanCliente.PROFESIONAL: 5,
            PlanCliente.EMPRESARIAL: 99,
        }[self]


class RolTecnico(enum.Enum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN      = "ADMIN"
    TECNICO    = "TECNICO"


class MetodoPago(enum.Enum):
    EFECTIVO         = "efectivo"
    NEQUI            = "nequi"
    DAVIPLATA        = "daviplata"
    TARJETA_CREDITO  = "tarjeta_credito"
    TARJETA_DEBITO   = "tarjeta_debito"
    TRANSFERENCIA_PSE = "transferencia_pse"


class EstadoAlquiler(enum.Enum):
    ACTIVO   = "activo"
    DEVUELTO = "devuelto"
    VENCIDO  = "vencido"


# ================================================================
# ENTIDAD: CLIENTE
# ================================================================
@dataclass
class Cliente:
    """
    Entidad Cliente — raíz de agregado.
    Toda la lógica de validación que estaba en los controladores
    ahora es responsabilidad de esta entidad.
    """
    id: str
    nombre: NombrePersona
    email: Email
    password_hash: PasswordHash
    plan: PlanCliente
    activo: bool = True
    verificado: bool = False
    empresa: str = ""
    telefono: Optional[TelefonoColombia] = None
    ciudad: str = "Bogotá"
    creado_en: datetime = field(default_factory=datetime.utcnow)
    ultimo_login: Optional[datetime] = None
    intentos_login: int = 0

    @classmethod
    def crear(
        cls,
        nombre: NombrePersona,
        email: Email,
        password_hash: PasswordHash,
        empresa: str = "",
        telefono: Optional[TelefonoColombia] = None,
        ciudad: str = "Bogotá",
        plan: PlanCliente = PlanCliente.BASICO,
    ) -> Cliente:
        return cls(
            id=str(uuid4()),
            nombre=nombre,
            email=email,
            password_hash=password_hash,
            plan=plan,
            empresa=empresa,
            telefono=telefono,
            ciudad=ciudad,
        )

    def verificar_limite_tickets(self, tickets_abiertos: int) -> None:
        """Valida que el cliente no haya excedido el límite de tickets de su plan."""
        limite = self.plan.limite_tickets_simultaneos()
        if tickets_abiertos >= limite:
            raise LimiteTicketsPlanExcedido(
                plan=self.plan.value,
                limite=limite,
                actuales=tickets_abiertos,
            )

    def verificar_limite_alquiler(self, dias: int) -> None:
        max_dias = self.plan.limite_dias_alquiler()
        if dias > max_dias:
            raise LimiteAlquilerPlanExcedido(
                plan=self.plan.value,
                max_dias=max_dias,
                dias_solicitados=dias,
            )

    def aplicar_descuento(self, costo: COP) -> COP:
        """Aplica el descuento del plan al costo del servicio."""
        desc = self.plan.descuento_servicios()
        if desc > 0:
            return costo.multiplicar(1 - desc)
        return costo

    def esta_activo(self) -> bool:
        return self.activo and self.verificado

    def codigo_cliente(self) -> str:
        año = self.creado_en.year
        return f"CLI-{año}-{self.id[:6].upper()}"


# ================================================================
# ENTIDAD: TECNICO
# ================================================================
@dataclass
class Tecnico:
    """Entidad Técnico — personal de soporte de TechSupport Pro."""
    id: str
    nombre: NombrePersona
    email: Email
    password_hash: PasswordHash
    rol: RolTecnico
    especialidades: list[TipoServicio] = field(default_factory=list)
    disponible: bool = True
    activo: bool = True
    calificacion_promedio: float = 0.0
    tickets_resueltos: int = 0
    creado_en: datetime = field(default_factory=datetime.utcnow)
    telefono: Optional[TelefonoColombia] = None

    @classmethod
    def crear(
        cls,
        nombre: NombrePersona,
        email: Email,
        password_hash: PasswordHash,
        rol: RolTecnico = RolTecnico.TECNICO,
        especialidades: Optional[list[TipoServicio]] = None,
        telefono: Optional[TelefonoColombia] = None,
    ) -> Tecnico:
        return cls(
            id=str(uuid4()),
            nombre=nombre,
            email=email,
            password_hash=password_hash,
            rol=rol,
            especialidades=especialidades or [],
            telefono=telefono,
        )

    def es_admin(self) -> bool:
        return self.rol in (RolTecnico.ADMIN, RolTecnico.SUPERADMIN)

    def puede_ver_ticket(self, ticket: Ticket) -> bool:
        return self.es_admin() or ticket.tecnico_id == self.id

    def puede_modificar_ticket(self, ticket: Ticket) -> bool:
        return self.es_admin() or ticket.tecnico_id == self.id

    def actualizar_calificacion(self, nueva_nota: float, total_previas: int) -> None:
        """Recalcula el promedio ponderado — antes en el controlador."""
        if nueva_nota < 1 or nueva_nota > 5:
            raise ValueError("La calificación debe estar entre 1 y 5")
        total_puntos = self.calificacion_promedio * total_previas + nueva_nota
        self.calificacion_promedio = round(total_puntos / (total_previas + 1), 2)
        self.tickets_resueltos += 1


# ================================================================
# ENTIDAD: TICKET
# ================================================================
@dataclass
class Ticket:
    """
    Entidad Ticket — raíz de agregado central del sistema.
    Contiene la máquina de estados y todas las reglas de transición
    que antes vivían en el controlador HTTP.
    """
    id: str
    numero: str
    cliente_id: str
    tipo_servicio: TipoServicio
    titulo: str
    descripcion: str
    prioridad: Prioridad
    estado: EstadoTicket = EstadoTicket.NUEVO
    tecnico_id: Optional[str] = None
    diagnostico: Optional[str] = None
    solucion: Optional[str] = None
    costo_estimado: Optional[COP] = None
    costo_final: Optional[COP] = None
    calificacion: Optional[float] = None
    direccion_visita: str = ""
    fecha_programada: Optional[datetime] = None
    creado_en: datetime = field(default_factory=datetime.utcnow)
    actualizado_en: datetime = field(default_factory=datetime.utcnow)
    resuelto_en: Optional[datetime] = None

    # Tabla de costos base por tipo de servicio (antes hardcoded en el controlador)
    _COSTOS_BASE: dict = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        self._COSTOS_BASE = {
            TipoServicio.SOPORTE_PRESENCIAL:    COP.de_pesos(85_000),
            TipoServicio.SOPORTE_REMOTO:        COP.de_pesos(45_000),
            TipoServicio.REPARACION_PC:         COP.de_pesos(130_000),
            TipoServicio.REPARACION_LAPTOP:     COP.de_pesos(150_000),
            TipoServicio.REPARACION_IMPRESORA:  COP.de_pesos(125_000),
            TipoServicio.MANTENIMIENTO_PREV:    COP.de_pesos(100_000),
            TipoServicio.ALQUILER_EQUIPO:       COP.cero(),
            TipoServicio.DESARROLLO_SOFTWARE:   COP.cero(),
            TipoServicio.REDES_INFRAESTRUCTURA: COP.de_pesos(200_000),
            TipoServicio.CONSULTORIA_TI:        COP.de_pesos(90_000),
        }
        if self.costo_estimado is None:
            self.costo_estimado = self._calcular_costo_estimado()

    @classmethod
    def crear(
        cls,
        cliente_id: str,
        tipo_servicio: TipoServicio,
        titulo: str,
        descripcion: str,
        prioridad: Prioridad,
        numero: str,
        direccion_visita: str = "",
        fecha_programada: Optional[datetime] = None,
    ) -> Ticket:
        if len(titulo.strip()) < 5:
            raise ValueError("El título debe tener al menos 5 caracteres")
        if len(descripcion.strip()) < 10:
            raise ValueError("La descripción debe tener al menos 10 caracteres")

        return cls(
            id=str(uuid4()),
            numero=numero,
            cliente_id=cliente_id,
            tipo_servicio=tipo_servicio,
            titulo=titulo.strip(),
            descripcion=descripcion.strip(),
            prioridad=prioridad,
            direccion_visita=direccion_visita,
            fecha_programada=fecha_programada,
        )

    def _calcular_costo_estimado(self) -> COP:
        """Cálculo de costo con recargo por prioridad — antes en el controlador."""
        base = self._COSTOS_BASE.get(self.tipo_servicio, COP.cero())
        return base.multiplicar(self.prioridad.factor_recargo())

    def transicionar_a(self, nuevo_estado: EstadoTicket, **kwargs) -> None:
        """
        Máquina de estados del ticket.
        Antes completamente implementada en el controlador HTTP.
        """
        if not self.estado.puede_transicionar_a(nuevo_estado):
            raise TransicionDeEstadoInvalida(
                estado_actual=self.estado.value,
                estado_destino=nuevo_estado.value,
            )

        if nuevo_estado == EstadoTicket.RESUELTO:
            diagnostico = kwargs.get('diagnostico') or self.diagnostico
            if not diagnostico:
                raise DiagnosticoRequerido()
            self.resuelto_en = datetime.utcnow()

        if 'diagnostico' in kwargs and kwargs['diagnostico']:
            self.diagnostico = kwargs['diagnostico']
        if 'solucion' in kwargs and kwargs['solucion']:
            self.solucion = kwargs['solucion']
        if 'costo_final' in kwargs and kwargs['costo_final'] is not None:
            costo = kwargs['costo_final']
            if isinstance(costo, (int, float)):
                costo = COP.de_pesos(costo)
            self.costo_final = costo

        self.estado = nuevo_estado
        self.actualizado_en = datetime.utcnow()

    def asignar_tecnico(self, tecnico_id: str) -> None:
        self.tecnico_id = tecnico_id
        if self.estado == EstadoTicket.NUEVO:
            self.transicionar_a(EstadoTicket.ASIGNADO)

    def calificar(self, nota: float) -> None:
        """Reglas de calificación — antes en el controlador."""
        if self.calificacion is not None:
            raise TicketYaCalificado(self.id)
        if self.estado not in (EstadoTicket.RESUELTO, EstadoTicket.CERRADO):
            raise TicketNoResuelto(self.id, self.estado.value)
        if not 1 <= nota <= 5:
            raise ValueError("La calificación debe estar entre 1.0 y 5.0")
        self.calificacion = round(nota, 1)

    def esta_abierto(self) -> bool:
        return self.estado not in (EstadoTicket.RESUELTO, EstadoTicket.CERRADO, EstadoTicket.CANCELADO)

    def tiempo_resolucion_minutos(self) -> Optional[int]:
        """Antes calculado en el controlador."""
        if self.resuelto_en and self.creado_en:
            delta = self.resuelto_en - self.creado_en
            return int(delta.total_seconds() / 60)
        return None


# ================================================================
# ENTIDAD: ALQUILER DE EQUIPO
# ================================================================
@dataclass
class AlquilerEquipo:
    """
    Entidad Alquiler — contrato de alquiler de equipos.
    Encapsula cálculos de costo, depósito y descuentos por volumen.
    """
    id: str
    cliente_id: str
    equipo_tipo: str
    periodo: Periodo
    costo_diario: COP
    deposito: COP
    costo_total: COP
    estado: EstadoAlquiler = EstadoAlquiler.ACTIVO
    equipo_marca: str = ""
    equipo_modelo: str = ""
    creado_en: datetime = field(default_factory=datetime.utcnow)

    _TIPOS_VALIDOS = frozenset({
        "laptop", "desktop", "impresora", "servidor",
        "tablet", "monitor", "proyector", "switch", "router"
    })
    _COSTO_DIARIO_MINIMO = COP.de_pesos(20_000)
    _PORCENTAJE_DEPOSITO = 0.30

    @classmethod
    def crear(
        cls,
        cliente: Cliente,
        equipo_tipo: str,
        periodo: Periodo,
        costo_diario: COP,
        equipo_marca: str = "",
        equipo_modelo: str = "",
    ) -> AlquilerEquipo:
        # Validar tipo de equipo
        if equipo_tipo.lower() not in cls._TIPOS_VALIDOS:
            raise ValueError(
                f"Tipo de equipo '{equipo_tipo}' no válido. "
                f"Disponibles: {', '.join(sorted(cls._TIPOS_VALIDOS))}"
            )

        # Validar costo mínimo
        if costo_diario < cls._COSTO_DIARIO_MINIMO:
            from techsupportpro.domain.exceptions import CostoDiarioMinimoViolado
            raise CostoDiarioMinimoViolado(
                minimo=cls._COSTO_DIARIO_MINIMO.pesos,
                recibido=costo_diario.pesos,
            )

        # Validar límite del plan
        cliente.verificar_limite_alquiler(periodo.dias)

        # Calcular costo total con descuentos por volumen
        costo_total = cls._calcular_costo_total(costo_diario, periodo.dias)

        # Aplicar descuento del plan
        costo_total = cliente.aplicar_descuento(costo_total)

        # Calcular depósito
        deposito = costo_total.multiplicar(cls._PORCENTAJE_DEPOSITO)

        return cls(
            id=str(uuid4()),
            cliente_id=cliente.id,
            equipo_tipo=equipo_tipo.lower(),
            periodo=periodo,
            costo_diario=costo_diario,
            deposito=deposito,
            costo_total=costo_total,
            equipo_marca=equipo_marca,
            equipo_modelo=equipo_modelo,
        )

    @staticmethod
    def _calcular_costo_total(costo_diario: COP, dias: int) -> COP:
        """
        Descuentos por volumen — antes hardcoded en el controlador.
        +7 días → 8% descuento, +30 días → 15% descuento.
        """
        total = costo_diario.multiplicar(dias)
        if dias >= 30:
            return total.multiplicar(0.85)
        if dias >= 7:
            return total.multiplicar(0.92)
        return total

    def devolver(self) -> None:
        if self.estado != EstadoAlquiler.ACTIVO:
            raise ValueError(f"El alquiler no está activo (estado: {self.estado.value})")
        self.estado = EstadoAlquiler.DEVUELTO

    def esta_vencido(self) -> bool:
        return datetime.utcnow() > self.periodo.fin and self.estado == EstadoAlquiler.ACTIVO


# ================================================================
# ENTIDAD: PAGO
# ================================================================
@dataclass
class Pago:
    """Entidad Pago — registro de transacciones del sistema."""
    id: str
    cliente_id: str
    monto: COP
    metodo: MetodoPago
    estado: str = "pendiente"
    ticket_id: Optional[str] = None
    alquiler_id: Optional[str] = None
    referencia_externa: Optional[str] = None
    creado_en: datetime = field(default_factory=datetime.utcnow)

    _MONTO_MINIMO = COP.de_pesos(5_000)

    @classmethod
    def crear(
        cls,
        cliente_id: str,
        monto: COP,
        metodo: MetodoPago,
        ticket_id: Optional[str] = None,
        alquiler_id: Optional[str] = None,
    ) -> Pago:
        if monto < cls._MONTO_MINIMO:
            from techsupportpro.domain.exceptions import MontoInvalido
            raise MontoInvalido(monto.pesos, cls._MONTO_MINIMO.pesos)

        if not ticket_id and not alquiler_id:
            raise ValueError("El pago debe asociarse a un ticket o a un alquiler")

        return cls(
            id=str(uuid4()),
            cliente_id=cliente_id,
            monto=monto,
            metodo=metodo,
            ticket_id=ticket_id,
            alquiler_id=alquiler_id,
        )

    def confirmar(self, referencia: str) -> None:
        self.estado = "confirmado"
        self.referencia_externa = referencia

    def rechazar(self) -> None:
        self.estado = "rechazado"

    def esta_confirmado(self) -> bool:
        return self.estado == "confirmado"
