"""
Adaptadores de salida JSON — segundo adaptador de persistencia.

Guarda cada entidad como un archivo JSON en disco.
Demuestra la evolución sin tocar el dominio ni los casos de uso:
  MODO_REPO=json  →  todo persiste en ./data/*.json

Estructura de archivos:
    data/
    ├── clientes.json
    ├── tecnicos.json
    ├── tickets.json
    ├── alquileres.json
    ├── pagos.json
    └── auditoria.json
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Optional

from techsupportpro.domain.ports import (
    IClienteRepository, ITecnicoRepository, ITicketRepository,
    IAlquilerRepository, IPagoRepository, IAuditoriaRepository,
)
from techsupportpro.domain.entities import (
    Cliente, Tecnico, Ticket, AlquilerEquipo, Pago,
    PlanCliente, RolTecnico, TipoServicio, EstadoTicket, Prioridad,
    MetodoPago, EstadoAlquiler,
)
from techsupportpro.domain.value_objects import (
    Email, PasswordHash, NombrePersona, TelefonoColombia, COP, Periodo,
)


def _dt(v) -> Optional[datetime]:
    return datetime.fromisoformat(v) if v else None

def _cop(v) -> Optional[COP]:
    return COP.de_pesos(v) if v is not None else None


class _JSONStore:
    """Base para todos los repositorios JSON."""

    def __init__(self, directorio: str, nombre: str):
        os.makedirs(directorio, exist_ok=True)
        self._path = os.path.join(directorio, f"{nombre}.json")
        self._data: dict = self._cargar()

    def _cargar(self) -> dict:
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _guardar(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2, default=str)

    def _set(self, clave: str, valor: dict) -> None:
        self._data[clave] = valor
        self._guardar()

    def _get(self, clave: str) -> Optional[dict]:
        return self._data.get(clave)

    def _all(self) -> list[dict]:
        return list(self._data.values())


def _cliente_to_dict(c: Cliente) -> dict:
    return {
        "id": c.id, "nombre": str(c.nombre), "email": str(c.email),
        "password_hash": str(c.password_hash), "plan": c.plan.value,
        "activo": c.activo, "verificado": c.verificado, "empresa": c.empresa,
        "telefono": str(c.telefono) if c.telefono else "",
        "ciudad": c.ciudad,
        "creado_en": c.creado_en.isoformat(),
        "ultimo_login": c.ultimo_login.isoformat() if c.ultimo_login else None,
    }

def _dict_to_cliente(d: dict) -> Cliente:
    c = object.__new__(Cliente)
    c.id            = d["id"]
    c.nombre        = NombrePersona(d["nombre"])
    c.email         = Email(d["email"])
    c.password_hash = PasswordHash(d["password_hash"])
    c.plan          = PlanCliente(d["plan"])
    c.activo        = d["activo"]
    c.verificado    = d["verificado"]
    c.empresa       = d.get("empresa", "")
    c.telefono      = TelefonoColombia(d["telefono"]) if d.get("telefono") else None
    c.ciudad        = d.get("ciudad", "Bogotá")
    c.creado_en     = _dt(d["creado_en"])
    c.ultimo_login  = _dt(d.get("ultimo_login"))
    return c


def _tecnico_to_dict(t: Tecnico) -> dict:
    return {
        "id": t.id, "nombre": str(t.nombre), "email": str(t.email),
        "password_hash": str(t.password_hash), "rol": t.rol.value,
        "activo": t.activo, "disponible": t.disponible,
        "especialidades": [e.value for e in t.especialidades],
        "calificacion": t.calificacion_promedio,
        "tickets_resueltos": t.tickets_resueltos,
        "creado_en": t.creado_en.isoformat(),
    }

def _dict_to_tecnico(d: dict) -> Tecnico:
    t = object.__new__(Tecnico)
    t.id                = d["id"]
    t.nombre            = NombrePersona(d["nombre"])
    t.email             = Email(d["email"])
    t.password_hash     = PasswordHash(d["password_hash"])
    t.rol               = RolTecnico(d["rol"])
    t.activo            = d["activo"]
    t.disponible        = d["disponible"]
    t.especialidades    = [TipoServicio(e) for e in d.get("especialidades", [])]
    t.calificacion      = d.get("calificacion", 0.0)
    t.tickets_resueltos = d.get("tickets_resueltos", 0)
    t.creado_en         = _dt(d["creado_en"])
    return t


def _ticket_to_dict(t: Ticket) -> dict:
    return {
        "id": t.id, "numero": t.numero,
        "cliente_id": t.cliente_id, "tecnico_id": t.tecnico_id,
        "tipo_servicio": t.tipo_servicio.value, "estado": t.estado.value,
        "prioridad": t.prioridad.value, "titulo": t.titulo,
        "descripcion": t.descripcion, "diagnostico": t.diagnostico,
        "solucion": t.solucion,
        "costo_estimado": t.costo_estimado.pesos if t.costo_estimado else None,
        "costo_final": t.costo_final.pesos if t.costo_final else None,
        "calificacion": t.calificacion,
        "direccion_visita": t.direccion_visita,
        "fecha_programada": t.fecha_programada.isoformat() if t.fecha_programada else None,
        "creado_en": t.creado_en.isoformat(),
        "resuelto_en": t.resuelto_en.isoformat() if t.resuelto_en else None,
    }

def _dict_to_ticket(d: dict) -> Ticket:
    t = object.__new__(Ticket)
    t.id               = d["id"]
    t.numero           = d["numero"]
    t.cliente_id       = d["cliente_id"]
    t.tecnico_id       = d.get("tecnico_id")
    t.tipo_servicio    = TipoServicio(d["tipo_servicio"])
    t.estado           = EstadoTicket(d["estado"])
    t.prioridad        = Prioridad(d["prioridad"])
    t.titulo           = d["titulo"]
    t.descripcion      = d["descripcion"]
    t.diagnostico      = d.get("diagnostico")
    t.solucion         = d.get("solucion")
    t.costo_estimado   = _cop(d.get("costo_estimado"))
    t.costo_final      = _cop(d.get("costo_final"))
    t.calificacion     = d.get("calificacion")
    t.direccion_visita = d.get("direccion_visita", "")
    t.fecha_programada = _dt(d.get("fecha_programada"))
    t.creado_en        = _dt(d["creado_en"])
    t.resuelto_en      = _dt(d.get("resuelto_en"))
    return t


class ClienteRepositoryJSON(_JSONStore, IClienteRepository):
    def __init__(self, directorio: str):
        _JSONStore.__init__(self, directorio, "clientes")

    def guardar(self, c: Cliente) -> None:
        self._set(c.id, _cliente_to_dict(c))

    def actualizar(self, c: Cliente) -> None:
        self._set(c.id, _cliente_to_dict(c))

    def buscar_por_id(self, cid: str) -> Optional[Cliente]:
        d = self._get(cid)
        return _dict_to_cliente(d) if d else None

    def buscar_por_email(self, email: Email) -> Optional[Cliente]:
        for d in self._all():
            if d["email"] == str(email):
                return _dict_to_cliente(d)
        return None

    def listar_todos(self) -> list[Cliente]:
        return [_dict_to_cliente(d) for d in self._all()]

    def contar_activos(self) -> int:
        return sum(1 for d in self._all() if d["activo"] and d["verificado"])


class TecnicoRepositoryJSON(_JSONStore, ITecnicoRepository):
    def __init__(self, directorio: str):
        _JSONStore.__init__(self, directorio, "tecnicos")

    def guardar(self, t: Tecnico) -> None:
        self._set(t.id, _tecnico_to_dict(t))

    def actualizar(self, t: Tecnico) -> None:
        self._set(t.id, _tecnico_to_dict(t))

    def buscar_por_id(self, tid: str) -> Optional[Tecnico]:
        d = self._get(tid)
        return _dict_to_tecnico(d) if d else None

    def buscar_por_email(self, email: Email) -> Optional[Tecnico]:
        for d in self._all():
            if d["email"] == str(email):
                return _dict_to_tecnico(d)
        return None

    def listar_disponibles(self) -> list[Tecnico]:
        return [_dict_to_tecnico(d) for d in self._all()
                if d["disponible"] and d["activo"]]

    def listar_todos(self) -> list[Tecnico]:
        return [_dict_to_tecnico(d) for d in self._all()]

    def contar_activos(self) -> int:
        return sum(1 for d in self._all() if d["activo"])


class TicketRepositoryJSON(_JSONStore, ITicketRepository):
    def __init__(self, directorio: str):
        _JSONStore.__init__(self, directorio, "tickets")

    def guardar(self, t: Ticket) -> None:
        self._set(t.id, _ticket_to_dict(t))

    def actualizar(self, t: Ticket) -> None:
        self._set(t.id, _ticket_to_dict(t))

    def buscar_por_id(self, tid: str) -> Optional[Ticket]:
        d = self._get(tid)
        return _dict_to_ticket(d) if d else None

    def listar_por_cliente(self, cid: str, estado=None) -> list[Ticket]:
        items = [_dict_to_ticket(d) for d in self._all() if d["cliente_id"] == cid]
        if estado:
            items = [t for t in items if t.estado == estado]
        return sorted(items, key=lambda t: t.creado_en, reverse=True)

    def listar_por_tecnico(self, tid: str, estado=None) -> list[Ticket]:
        items = [_dict_to_ticket(d) for d in self._all() if d.get("tecnico_id") == tid]
        if estado:
            items = [t for t in items if t.estado == estado]
        return sorted(items, key=lambda t: t.creado_en, reverse=True)

    def siguiente_numero(self) -> str:
        n = len(self._data) + 1
        return f"TSP-{n:05d}"

    def contar_abiertos_por_cliente(self, cid: str) -> int:
        abiertos = {"NUEVO", "ASIGNADO", "DIAGNOSTICO", "EN_PROCESO", "EN_ESPERA"}
        return sum(1 for d in self._all()
                   if d["cliente_id"] == cid and d["estado"] in abiertos)

    def contar_total(self) -> int:
        return len(self._data)

    def contar_por_estado(self, estado) -> int:
        return sum(1 for d in self._all() if d["estado"] == estado.value)

    def listar_todos(self) -> list[Ticket]:
        return [_dict_to_ticket(d) for d in self._all()]


class AlquilerRepositoryJSON(_JSONStore, IAlquilerRepository):
    def __init__(self, directorio: str):
        _JSONStore.__init__(self, directorio, "alquileres")

    def guardar(self, a: AlquilerEquipo) -> None:
        self._set(a.id, {
            "id": a.id, "cliente_id": a.cliente_id, "equipo_tipo": a.equipo_tipo,
            "equipo_marca": a.equipo_marca, "equipo_modelo": a.equipo_modelo,
            "fecha_inicio": a.periodo.inicio.isoformat(),
            "fecha_fin": a.periodo.fin.isoformat(),
            "costo_diario": a.costo_diario.pesos, "costo_total": a.costo_total.pesos,
            "deposito": a.deposito.pesos, "estado": a.estado.value,
            "creado_en": a.creado_en.isoformat(),
        })

    def actualizar(self, a: AlquilerEquipo) -> None:
        self.guardar(a)

    def buscar_por_id(self, aid: str) -> Optional[AlquilerEquipo]:
        d = self._get(aid)
        if not d: return None
        a = object.__new__(AlquilerEquipo)
        a.id = d["id"]; a.cliente_id = d["cliente_id"]
        a.equipo_tipo = d["equipo_tipo"]; a.equipo_marca = d["equipo_marca"]
        a.equipo_modelo = d["equipo_modelo"]
        a.periodo = Periodo(inicio=_dt(d["fecha_inicio"]), fin=_dt(d["fecha_fin"]))
        a.costo_diario = COP.de_pesos(d["costo_diario"])
        a.costo_total = COP.de_pesos(d["costo_total"])
        a.deposito = COP.de_pesos(d["deposito"])
        a.estado = EstadoAlquiler(d["estado"])
        a.creado_en = _dt(d["creado_en"])
        return a

    def listar_por_cliente(self, cid: str) -> list[AlquilerEquipo]:
        return [self.buscar_por_id(d["id"]) for d in self._all() if d["cliente_id"] == cid]

    def listar_activos_por_cliente(self, cid: str) -> list[AlquilerEquipo]:
        return [self.buscar_por_id(d["id"]) for d in self._all()
                if d["cliente_id"] == cid and d["estado"] == "activo"]

    def contar_activos_por_cliente(self, cid: str) -> int:
        return len(self.listar_activos_por_cliente(cid))

    def listar_todos(self) -> list[AlquilerEquipo]:
        return [self.buscar_por_id(d["id"]) for d in self._all()]


class PagoRepositoryJSON(_JSONStore, IPagoRepository):
    def __init__(self, directorio: str):
        _JSONStore.__init__(self, directorio, "pagos")

    def guardar(self, p: Pago) -> None:
        self._set(p.id, {
            "id": p.id, "cliente_id": p.cliente_id,
            "monto": p.monto.pesos, "metodo": p.metodo.value,
            "estado": p.estado, "ticket_id": p.ticket_id,
            "alquiler_id": p.alquiler_id,
            "referencia_externa": p.referencia_externa,
            "creado_en": p.creado_en.isoformat(),
        })

    def buscar_por_id(self, pid: str) -> Optional[Pago]:
        d = self._get(pid)
        if not d: return None
        p = object.__new__(Pago)
        p.id = d["id"]; p.cliente_id = d["cliente_id"]
        p.monto = COP.de_pesos(d["monto"]); p.metodo = MetodoPago(d["metodo"])
        p.estado = d["estado"]; p.ticket_id = d.get("ticket_id")
        p.alquiler_id = d.get("alquiler_id")
        p.referencia_externa = d.get("referencia_externa")
        p.creado_en = _dt(d["creado_en"])
        return p

    def actualizar(self, p: Pago) -> None:
        self.guardar(p)

    def listar_por_cliente(self, cid: str) -> list[Pago]:
        return [self.buscar_por_id(d["id"]) for d in self._all() if d["cliente_id"] == cid]

    def sumar_ingresos_desde(self, desde: datetime) -> COP:
        total = sum(
            d["monto"] for d in self._all()
            if _dt(d["creado_en"]) >= desde and d["estado"] == "confirmado"
        )
        return COP.de_pesos(total)

    def listar_todos(self) -> list[Pago]:
        return [self.buscar_por_id(d["id"]) for d in self._all()]


class AuditoriaRepositoryJSON(_JSONStore, IAuditoriaRepository):
    def __init__(self, directorio: str):
        _JSONStore.__init__(self, directorio, "auditoria")
        self._contador = len(self._data)

    def registrar(self, usuario_id: str, tipo_usuario: str, accion: str, detalle: str) -> None:
        self._contador += 1
        self._set(str(self._contador), {
            "id": self._contador, "usuario_id": usuario_id,
            "tipo_usuario": tipo_usuario, "accion": accion,
            "detalle": detalle, "ts": datetime.utcnow().isoformat(),
        })

    def listar_por_usuario(self, uid: str) -> list[dict]:
        return [d for d in self._all() if d["usuario_id"] == uid]

    def listar_por_accion(self, accion: str) -> list[dict]:
        return [d for d in self._all() if d["accion"] == accion]
