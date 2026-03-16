"""
Adaptadores de salida PostgreSQL — usando SQLAlchemy 2.0.

Cada repositorio implementa su puerto del dominio.
Los modelos ORM viven AQUÍ, nunca en el dominio.
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, Float, Integer, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Session

from techsupportpro.infrastructure.adapters_out.postgres.db import Base
from techsupportpro.domain.ports import (
    IClienteRepository, ITecnicoRepository, ITicketRepository,
    IAlquilerRepository, IPagoRepository, IAuditoriaRepository,
)
from techsupportpro.domain.entities import (
    Cliente, Tecnico, Ticket, AlquilerEquipo, Pago,
    PlanCliente, RolTecnico, TipoServicio, EstadoTicket, Prioridad, MetodoPago,
    EstadoAlquiler,
)
from techsupportpro.domain.value_objects import (
    Email, PasswordHash, NombrePersona, TelefonoColombia, COP, Periodo,
)


# ── MODELOS ORM ────────────────────────────────────────────────
class ClienteORM(Base):
    __tablename__ = "clientes"
    id           = Column(String, primary_key=True)
    nombre       = Column(String, nullable=False)
    email        = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    plan         = Column(String, nullable=False, default="basico")
    activo       = Column(Boolean, default=True)
    verificado   = Column(Boolean, default=False)
    empresa      = Column(String, default="")
    telefono     = Column(String, default="")
    ciudad       = Column(String, default="Bogotá")
    creado_en    = Column(DateTime, default=datetime.utcnow)
    ultimo_login = Column(DateTime, nullable=True)


class TecnicoORM(Base):
    __tablename__ = "tecnicos"
    id              = Column(String, primary_key=True)
    nombre          = Column(String, nullable=False)
    email           = Column(String, unique=True, nullable=False)
    password_hash   = Column(String, nullable=False)
    rol             = Column(String, nullable=False, default="tecnico")
    activo          = Column(Boolean, default=True)
    disponible      = Column(Boolean, default=True)
    especialidades  = Column(Text, default="[]")   # JSON array
    calificacion    = Column(Float, default=0.0)
    tickets_resueltos = Column(Integer, default=0)
    creado_en       = Column(DateTime, default=datetime.utcnow)


class TicketORM(Base):
    __tablename__ = "tickets"
    id               = Column(String, primary_key=True)
    numero           = Column(String, unique=True, nullable=False)
    cliente_id       = Column(String, nullable=False)
    tecnico_id       = Column(String, nullable=True)
    tipo_servicio    = Column(String, nullable=False)
    estado           = Column(String, nullable=False, default="NUEVO")
    prioridad        = Column(String, nullable=False, default="MEDIA")
    titulo           = Column(String, nullable=False)
    descripcion      = Column(Text, nullable=False)
    diagnostico      = Column(Text, nullable=True)
    solucion         = Column(Text, nullable=True)
    costo_estimado   = Column(Float, nullable=True)
    costo_final      = Column(Float, nullable=True)
    calificacion     = Column(Float, nullable=True)
    direccion_visita = Column(String, default="")
    fecha_programada = Column(DateTime, nullable=True)
    creado_en        = Column(DateTime, default=datetime.utcnow)
    resuelto_en      = Column(DateTime, nullable=True)


class AlquilerORM(Base):
    __tablename__ = "alquileres"
    id            = Column(String, primary_key=True)
    cliente_id    = Column(String, nullable=False)
    equipo_tipo   = Column(String, nullable=False)
    equipo_marca  = Column(String, default="")
    equipo_modelo = Column(String, default="")
    fecha_inicio  = Column(DateTime, nullable=False)
    fecha_fin     = Column(DateTime, nullable=False)
    costo_diario  = Column(Float, nullable=False)
    costo_total   = Column(Float, nullable=False)
    deposito      = Column(Float, nullable=False)
    estado        = Column(String, nullable=False, default="activo")
    creado_en     = Column(DateTime, default=datetime.utcnow)


class PagoORM(Base):
    __tablename__ = "pagos"
    id                 = Column(String, primary_key=True)
    cliente_id         = Column(String, nullable=False)
    monto              = Column(Float, nullable=False)
    metodo             = Column(String, nullable=False)
    estado             = Column(String, nullable=False, default="pendiente")
    ticket_id          = Column(String, nullable=True)
    alquiler_id        = Column(String, nullable=True)
    referencia_externa = Column(String, nullable=True)
    creado_en          = Column(DateTime, default=datetime.utcnow)


class AuditoriaORM(Base):
    __tablename__ = "auditoria"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id   = Column(String, nullable=False)
    tipo_usuario = Column(String, nullable=False)
    accion       = Column(String, nullable=False)
    detalle      = Column(Text, nullable=False)
    ts           = Column(DateTime, default=datetime.utcnow)


# ── REPOSITORIOS ──────────────────────────────────────────────

def _cliente_to_entity(orm: ClienteORM) -> Cliente:
    c = object.__new__(Cliente)
    c.id           = orm.id
    c.nombre       = NombrePersona(orm.nombre)
    c.email        = Email(orm.email)
    c.password_hash = PasswordHash(orm.password_hash)
    c.plan         = PlanCliente(orm.plan)
    c.activo       = orm.activo
    c.verificado   = orm.verificado
    c.empresa      = orm.empresa
    c.telefono     = TelefonoColombia(orm.telefono) if orm.telefono else None
    c.ciudad       = orm.ciudad
    c.creado_en    = orm.creado_en
    c.ultimo_login = orm.ultimo_login
    return c

def _tecnico_to_entity(orm: TecnicoORM) -> Tecnico:
    t = object.__new__(Tecnico)
    t.id               = orm.id
    t.nombre           = NombrePersona(orm.nombre)
    t.email            = Email(orm.email)
    t.password_hash    = PasswordHash(orm.password_hash)
    t.rol              = RolTecnico(orm.rol)
    t.activo           = orm.activo
    t.disponible       = orm.disponible
    t.especialidades   = [TipoServicio(e) for e in json.loads(orm.especialidades)]
    t.calificacion     = orm.calificacion
    t.tickets_resueltos = orm.tickets_resueltos
    t.creado_en        = orm.creado_en
    return t

def _ticket_to_entity(orm: TicketORM) -> Ticket:
    t = object.__new__(Ticket)
    t.id               = orm.id
    t.numero           = orm.numero
    t.cliente_id       = orm.cliente_id
    t.tecnico_id       = orm.tecnico_id
    t.tipo_servicio    = TipoServicio(orm.tipo_servicio)
    t.estado           = EstadoTicket(orm.estado)
    t.prioridad        = Prioridad(orm.prioridad)
    t.titulo           = orm.titulo
    t.descripcion      = orm.descripcion
    t.diagnostico      = orm.diagnostico
    t.solucion         = orm.solucion
    t.costo_estimado   = COP.de_pesos(orm.costo_estimado) if orm.costo_estimado else None
    t.costo_final      = COP.de_pesos(orm.costo_final) if orm.costo_final else None
    t.calificacion     = orm.calificacion
    t.direccion_visita = orm.direccion_visita
    t.fecha_programada = orm.fecha_programada
    t.creado_en        = orm.creado_en
    t.resuelto_en      = orm.resuelto_en
    return t

def _alquiler_to_entity(orm: AlquilerORM) -> AlquilerEquipo:
    a = object.__new__(AlquilerEquipo)
    a.id            = orm.id
    a.cliente_id    = orm.cliente_id
    a.equipo_tipo   = orm.equipo_tipo
    a.equipo_marca  = orm.equipo_marca
    a.equipo_modelo = orm.equipo_modelo
    a.periodo       = Periodo(inicio=orm.fecha_inicio, fin=orm.fecha_fin)
    a.costo_diario  = COP.de_pesos(orm.costo_diario)
    a.costo_total   = COP.de_pesos(orm.costo_total)
    a.deposito      = COP.de_pesos(orm.deposito)
    a.estado        = EstadoAlquiler(orm.estado)
    a.creado_en     = orm.creado_en
    return a

def _pago_to_entity(orm: PagoORM) -> Pago:
    p = object.__new__(Pago)
    p.id                 = orm.id
    p.cliente_id         = orm.cliente_id
    p.monto              = COP.de_pesos(orm.monto)
    p.metodo             = MetodoPago(orm.metodo)
    p.estado             = orm.estado
    p.ticket_id          = orm.ticket_id
    p.alquiler_id        = orm.alquiler_id
    p.referencia_externa = orm.referencia_externa
    p.creado_en          = orm.creado_en
    return p


class ClienteRepositoryPostgres(IClienteRepository):
    def __init__(self, session: Session): self._s = session

    def guardar(self, c: Cliente) -> None:
        orm = ClienteORM(
            id=c.id, nombre=str(c.nombre), email=str(c.email),
            password_hash=str(c.password_hash), plan=c.plan.value,
            activo=c.activo, verificado=c.verificado, empresa=c.empresa,
            telefono=str(c.telefono) if c.telefono else "",
            ciudad=c.ciudad, creado_en=c.creado_en,
        )
        self._s.merge(orm); self._s.commit()

    def actualizar(self, c: Cliente) -> None:
        self.guardar(c)

    def buscar_por_id(self, cid: str) -> Optional[Cliente]:
        orm = self._s.get(ClienteORM, cid)
        return _cliente_to_entity(orm) if orm else None

    def buscar_por_email(self, email: Email) -> Optional[Cliente]:
        orm = self._s.query(ClienteORM).filter_by(email=str(email)).first()
        return _cliente_to_entity(orm) if orm else None

    def listar_todos(self) -> list[Cliente]:
        return [_cliente_to_entity(o) for o in self._s.query(ClienteORM).all()]

    def contar_activos(self) -> int:
        return self._s.query(ClienteORM).filter_by(activo=True, verificado=True).count()


class TecnicoRepositoryPostgres(ITecnicoRepository):
    def __init__(self, session: Session): self._s = session

    def guardar(self, t: Tecnico) -> None:
        orm = TecnicoORM(
            id=t.id, nombre=str(t.nombre), email=str(t.email),
            password_hash=str(t.password_hash), rol=t.rol.value,
            activo=t.activo, disponible=t.disponible,
            especialidades=json.dumps([e.value for e in t.especialidades]),
            calificacion=t.calificacion_promedio,
            tickets_resueltos=t.tickets_resueltos, creado_en=t.creado_en,
        )
        self._s.merge(orm); self._s.commit()

    def actualizar(self, t: Tecnico) -> None:
        self.guardar(t)

    def buscar_por_id(self, tid: str) -> Optional[Tecnico]:
        orm = self._s.get(TecnicoORM, tid)
        return _tecnico_to_entity(orm) if orm else None

    def buscar_por_email(self, email: Email) -> Optional[Tecnico]:
        orm = self._s.query(TecnicoORM).filter_by(email=str(email)).first()
        return _tecnico_to_entity(orm) if orm else None

    def listar_disponibles(self) -> list[Tecnico]:
        orms = self._s.query(TecnicoORM).filter_by(disponible=True, activo=True).all()
        return [_tecnico_to_entity(o) for o in orms]

    def listar_todos(self) -> list[Tecnico]:
        return [_tecnico_to_entity(o) for o in self._s.query(TecnicoORM).all()]

    def contar_activos(self) -> int:
        return self._s.query(TecnicoORM).filter_by(activo=True).count()


class TicketRepositoryPostgres(ITicketRepository):
    def __init__(self, session: Session): self._s = session

    def guardar(self, t: Ticket) -> None:
        orm = TicketORM(
            id=t.id, numero=t.numero, cliente_id=t.cliente_id,
            tecnico_id=t.tecnico_id, tipo_servicio=t.tipo_servicio.value,
            estado=t.estado.value, prioridad=t.prioridad.value,
            titulo=t.titulo, descripcion=t.descripcion,
            diagnostico=t.diagnostico, solucion=t.solucion,
            costo_estimado=t.costo_estimado.pesos if t.costo_estimado else None,
            costo_final=t.costo_final.pesos if t.costo_final else None,
            calificacion=t.calificacion,
            direccion_visita=t.direccion_visita,
            fecha_programada=t.fecha_programada,
            creado_en=t.creado_en, resuelto_en=t.resuelto_en,
        )
        self._s.merge(orm); self._s.commit()

    def actualizar(self, t: Ticket) -> None:
        self.guardar(t)

    def buscar_por_id(self, tid: str) -> Optional[Ticket]:
        orm = self._s.get(TicketORM, tid)
        return _ticket_to_entity(orm) if orm else None

    def listar_por_cliente(self, cid: str, estado=None) -> list[Ticket]:
        q = self._s.query(TicketORM).filter_by(cliente_id=cid)
        if estado:
            q = q.filter_by(estado=estado.value)
        return [_ticket_to_entity(o) for o in q.order_by(TicketORM.creado_en.desc()).all()]

    def listar_por_tecnico(self, tid: str, estado=None) -> list[Ticket]:
        q = self._s.query(TicketORM).filter_by(tecnico_id=tid)
        if estado:
            q = q.filter_by(estado=estado.value)
        return [_ticket_to_entity(o) for o in q.order_by(TicketORM.creado_en.desc()).all()]

    def siguiente_numero(self) -> str:
        n = self._s.query(TicketORM).count() + 1
        return f"TSP-{n:05d}"

    def contar_abiertos_por_cliente(self, cid: str) -> int:
        abiertos = ["NUEVO", "ASIGNADO", "DIAGNOSTICO", "EN_PROCESO", "EN_ESPERA"]
        return self._s.query(TicketORM).filter(
            TicketORM.cliente_id == cid,
            TicketORM.estado.in_(abiertos)
        ).count()

    def contar_total(self) -> int:
        return self._s.query(TicketORM).count()

    def contar_por_estado(self, estado) -> int:
        return self._s.query(TicketORM).filter_by(estado=estado.value).count()

    def listar_todos(self) -> list[Ticket]:
        return [_ticket_to_entity(o) for o in self._s.query(TicketORM).all()]


class AlquilerRepositoryPostgres(IAlquilerRepository):
    def __init__(self, session: Session): self._s = session

    def guardar(self, a: AlquilerEquipo) -> None:
        orm = AlquilerORM(
            id=a.id, cliente_id=a.cliente_id, equipo_tipo=a.equipo_tipo,
            equipo_marca=a.equipo_marca, equipo_modelo=a.equipo_modelo,
            fecha_inicio=a.periodo.inicio, fecha_fin=a.periodo.fin,
            costo_diario=a.costo_diario.pesos, costo_total=a.costo_total.pesos,
            deposito=a.deposito.pesos, estado=a.estado.value, creado_en=a.creado_en,
        )
        self._s.merge(orm); self._s.commit()

    def actualizar(self, a: AlquilerEquipo) -> None:
        self.guardar(a)

    def buscar_por_id(self, aid: str) -> Optional[AlquilerEquipo]:
        orm = self._s.get(AlquilerORM, aid)
        return _alquiler_to_entity(orm) if orm else None

    def listar_por_cliente(self, cid: str) -> list[AlquilerEquipo]:
        orms = self._s.query(AlquilerORM).filter_by(cliente_id=cid).all()
        return [_alquiler_to_entity(o) for o in orms]

    def listar_activos_por_cliente(self, cid: str) -> list[AlquilerEquipo]:
        orms = self._s.query(AlquilerORM).filter_by(cliente_id=cid, estado="activo").all()
        return [_alquiler_to_entity(o) for o in orms]

    def contar_activos_por_cliente(self, cid: str) -> int:
        return self._s.query(AlquilerORM).filter_by(cliente_id=cid, estado="activo").count()

    def listar_todos(self) -> list[AlquilerEquipo]:
        return [_alquiler_to_entity(o) for o in self._s.query(AlquilerORM).all()]


class PagoRepositoryPostgres(IPagoRepository):
    def __init__(self, session: Session): self._s = session

    def guardar(self, p: Pago) -> None:
        orm = PagoORM(
            id=p.id, cliente_id=p.cliente_id, monto=p.monto.pesos,
            metodo=p.metodo.value, estado=p.estado,
            ticket_id=p.ticket_id, alquiler_id=p.alquiler_id,
            referencia_externa=p.referencia_externa, creado_en=p.creado_en,
        )
        self._s.merge(orm); self._s.commit()

    def actualizar(self, p: Pago) -> None:
        self.guardar(p)

    def buscar_por_id(self, pid: str) -> Optional[Pago]:
        orm = self._s.get(PagoORM, pid)
        return _pago_to_entity(orm) if orm else None

    def listar_por_cliente(self, cid: str) -> list[Pago]:
        orms = self._s.query(PagoORM).filter_by(cliente_id=cid).all()
        return [_pago_to_entity(o) for o in orms]

    def sumar_ingresos_desde(self, desde: datetime) -> COP:
        from sqlalchemy import func
        resultado = self._s.query(func.sum(PagoORM.monto)).filter(
            PagoORM.creado_en >= desde,
            PagoORM.estado == "confirmado"
        ).scalar() or 0.0
        return COP.de_pesos(resultado)

    def listar_todos(self) -> list[Pago]:
        return [_pago_to_entity(o) for o in self._s.query(PagoORM).all()]


class AuditoriaRepositoryPostgres(IAuditoriaRepository):
    def __init__(self, session: Session): self._s = session

    def registrar(self, usuario_id: str, tipo_usuario: str, accion: str, detalle: str) -> None:
        orm = AuditoriaORM(
            usuario_id=usuario_id, tipo_usuario=tipo_usuario,
            accion=accion, detalle=detalle, ts=datetime.utcnow(),
        )
        self._s.add(orm); self._s.commit()

    def listar_por_usuario(self, uid: str) -> list[dict]:
        orms = self._s.query(AuditoriaORM).filter_by(usuario_id=uid).all()
        return [{"usuario_id": o.usuario_id, "accion": o.accion,
                 "detalle": o.detalle, "ts": o.ts.isoformat()} for o in orms]

    def listar_por_accion(self, accion: str) -> list[dict]:
        orms = self._s.query(AuditoriaORM).filter_by(accion=accion).all()
        return [{"usuario_id": o.usuario_id, "accion": o.accion,
                 "detalle": o.detalle, "ts": o.ts.isoformat()} for o in orms]
