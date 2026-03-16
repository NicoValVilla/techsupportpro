# ================================================================
# ❌ MONOLITO ACOPLADO — TechSupport Pro
#    Sistema de Gestión de Servicios Técnicos - Colombia
#    Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL
#
#    Servicios: Soporte técnico presencial/remoto,
#    Reparación de equipos e impresoras,
#    Desarrollo de software a medida
#
#    ANTI-PATRÓN: Un solo archivo concentra TODO —
#    HTTP, ORM, reglas de negocio, email, WhatsApp,
#    pasarela de pagos, auditoría, webhooks.
#
#    Este archivo representa la rama 'main' (monolito original)
#    que será refactorizado a Arquitectura Hexagonal.
# ================================================================

from fastapi import FastAPI, HTTPException, Header
from sqlalchemy import (
    create_engine, Column, String, Boolean, DateTime,
    Integer, Float, Text, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime, timedelta
import enum, smtplib, hashlib, secrets, re, requests, json
from email.mime.text import MIMEText

# ================================================================
# CONFIGURACIÓN GLOBAL — ❌ credenciales hardcoded en código fuente
# ================================================================
DATABASE_URL   = "postgresql://techpro:techpro123@localhost/techpro_db"  # ❌
SMTP_HOST      = "smtp.techsupportpro.com.co"
SMTP_PORT      = 587
SMTP_USER      = "notificaciones@techsupportpro.com.co"
SMTP_PASS      = "smtp_pass_techpro_2026"           # ❌ hardcoded
WHATSAPP_TOKEN = "WHATSAPP_BTOKEN_TECHPRO_XYZ123"   # ❌ hardcoded
WOMPI_KEY      = "sk_prod_wompi_key_techpro_abc"    # ❌ hardcoded (pasarela Colombia)
WEBHOOK_CRM    = "https://crm.techsupportpro.com.co/webhook/eventos"
WHATSAPP_PHONE = "+573001234567"

engine       = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base         = declarative_base()

app = FastAPI(
    title="TechSupport Pro — Gestión de Servicios",
    description="API monolítica de gestión de tickets, clientes y técnicos"
)

# ================================================================
# ENUMS DE DOMINIO — mezclados con infraestructura en el mismo módulo
# ================================================================
class TipoServicioEnum(enum.Enum):
    SOPORTE_PRESENCIAL   = "SOPORTE_PRESENCIAL"
    SOPORTE_REMOTO       = "SOPORTE_REMOTO"
    REPARACION_PC        = "REPARACION_PC"
    REPARACION_LAPTOP    = "REPARACION_LAPTOP"
    REPARACION_IMPRESORA = "REPARACION_IMPRESORA"
    MANTENIMIENTO_PREV   = "MANTENIMIENTO_PREV"
    ALQUILER_EQUIPO      = "ALQUILER_EQUIPO"
    DESARROLLO_SOFTWARE  = "DESARROLLO_SOFTWARE"
    CONSULTORIA_TI       = "CONSULTORIA_TI"

class EstadoTicketEnum(enum.Enum):
    NUEVO       = "NUEVO"
    ASIGNADO    = "ASIGNADO"
    DIAGNOSTICO = "DIAGNOSTICO"
    EN_PROCESO  = "EN_PROCESO"
    EN_ESPERA   = "EN_ESPERA"       # esperando repuesto / respuesta cliente
    RESUELTO    = "RESUELTO"
    CERRADO     = "CERRADO"
    CANCELADO   = "CANCELADO"

class PrioridadEnum(enum.Enum):
    BAJA    = "BAJA"
    MEDIA   = "MEDIA"
    ALTA    = "ALTA"
    CRITICA = "CRITICA"

class RolEnum(enum.Enum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN      = "ADMIN"
    TECNICO    = "TECNICO"
    CLIENTE    = "CLIENTE"

class PlanClienteEnum(enum.Enum):
    BASICO      = "BASICO"
    PROFESIONAL = "PROFESIONAL"
    EMPRESARIAL = "EMPRESARIAL"

# ================================================================
# MODELOS ORM — infraestructura mezclada en el módulo principal
# ================================================================
class ClienteORM(Base):
    __tablename__ = "clientes"
    id             = Column(String,  primary_key=True, default=lambda: str(uuid4()))
    nombre         = Column(String,  nullable=False)
    apellido       = Column(String,  nullable=False)
    empresa        = Column(String,  nullable=True)
    email          = Column(String,  unique=True, nullable=False)
    telefono       = Column(String,  nullable=True)
    ciudad         = Column(String,  default="Bogotá")
    departamento   = Column(String,  nullable=True)
    nit_cc         = Column(String,  nullable=True)
    password_hash  = Column(String,  nullable=False)
    plan           = Column(SAEnum(PlanClienteEnum), default=PlanClienteEnum.BASICO)
    activo         = Column(Boolean, default=True)
    verificado     = Column(Boolean, default=False)
    intentos_login = Column(Integer, default=0)
    creado_en      = Column(DateTime, default=datetime.utcnow)
    ultimo_login   = Column(DateTime, nullable=True)

class TecnicoORM(Base):
    __tablename__ = "tecnicos"
    id              = Column(String,  primary_key=True, default=lambda: str(uuid4()))
    nombre          = Column(String,  nullable=False)
    apellido        = Column(String,  nullable=False)
    email           = Column(String,  unique=True, nullable=False)
    telefono        = Column(String,  nullable=True)
    password_hash   = Column(String,  nullable=False)
    rol             = Column(SAEnum(RolEnum), default=RolEnum.TECNICO)
    especialidades  = Column(Text,    nullable=True)   # JSON string de especialidades
    disponible      = Column(Boolean, default=True)
    activo          = Column(Boolean, default=True)
    tickets_activos = Column(Integer, default=0)
    calificacion    = Column(Float,   default=5.0)
    creado_en       = Column(DateTime, default=datetime.utcnow)

class TicketORM(Base):
    __tablename__ = "tickets"
    id               = Column(String,  primary_key=True, default=lambda: str(uuid4()))
    numero           = Column(String,  unique=True, nullable=False)
    cliente_id       = Column(String,  nullable=False)
    tecnico_id       = Column(String,  nullable=True)
    tipo_servicio    = Column(SAEnum(TipoServicioEnum), nullable=False)
    estado           = Column(SAEnum(EstadoTicketEnum), default=EstadoTicketEnum.NUEVO)
    prioridad        = Column(SAEnum(PrioridadEnum),    default=PrioridadEnum.MEDIA)
    titulo           = Column(String,  nullable=False)
    descripcion      = Column(Text,    nullable=False)
    diagnostico      = Column(Text,    nullable=True)
    solucion         = Column(Text,    nullable=True)
    equipo_marca     = Column(String,  nullable=True)
    equipo_modelo    = Column(String,  nullable=True)
    equipo_serial    = Column(String,  nullable=True)
    costo_estimado   = Column(Float,   nullable=True)
    costo_final      = Column(Float,   nullable=True)
    calificacion     = Column(Integer, nullable=True)   # 1-5 estrellas
    comentario_calif = Column(Text,    nullable=True)
    es_garantia      = Column(Boolean, default=False)
    ticket_origen_id = Column(String,  nullable=True)   # si es garantía, referencia al original
    creado_en        = Column(DateTime, default=datetime.utcnow)
    actualizado_en   = Column(DateTime, default=datetime.utcnow)
    resuelto_en      = Column(DateTime, nullable=True)
    tiempo_resolucion_horas = Column(Float, nullable=True)

class AlquilerEquipoORM(Base):
    __tablename__ = "alquileres"
    id            = Column(String,  primary_key=True, default=lambda: str(uuid4()))
    cliente_id    = Column(String,  nullable=False)
    equipo_tipo   = Column(String,  nullable=False)   # laptop, desktop, impresora, servidor
    equipo_marca  = Column(String,  nullable=True)
    equipo_modelo = Column(String,  nullable=True)
    fecha_inicio  = Column(DateTime, nullable=False)
    fecha_fin     = Column(DateTime, nullable=False)
    dias          = Column(Integer,  nullable=False)
    costo_diario  = Column(Float,   nullable=False)
    costo_total   = Column(Float,   nullable=False)
    deposito      = Column(Float,   nullable=False)
    estado        = Column(String,  default="activo")  # activo, devuelto, vencido
    creado_en     = Column(DateTime, default=datetime.utcnow)

class PagoORM(Base):
    __tablename__ = "pagos"
    id          = Column(String, primary_key=True, default=lambda: str(uuid4()))
    ticket_id   = Column(String, nullable=True)
    cliente_id  = Column(String, nullable=False)
    monto       = Column(Float,  nullable=False)
    metodo      = Column(String, nullable=False)  # efectivo, nequi, daviplata, tarjeta, transferencia
    referencia  = Column(String, nullable=True)
    estado      = Column(String, default="pendiente")  # pendiente, aprobado, rechazado
    creado_en   = Column(DateTime, default=datetime.utcnow)

class SesionORM(Base):
    __tablename__ = "sesiones"
    id         = Column(String,  primary_key=True, default=lambda: str(uuid4()))
    usuario_id = Column(String,  nullable=False)
    tipo       = Column(String,  nullable=False)   # cliente, tecnico
    token      = Column(String,  unique=True, nullable=False)
    expira_en  = Column(DateTime, nullable=False)
    activa     = Column(Boolean, default=True)
    ip_origen  = Column(String,  nullable=True)
    creado_en  = Column(DateTime, default=datetime.utcnow)

class AuditoriaORM(Base):
    __tablename__ = "auditoria"
    id         = Column(String,  primary_key=True, default=lambda: str(uuid4()))
    usuario_id = Column(String,  nullable=True)
    tipo       = Column(String,  nullable=False)   # cliente, tecnico
    accion     = Column(String,  nullable=False)
    detalle    = Column(Text,    nullable=True)
    ip         = Column(String,  nullable=True)
    timestamp  = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)


# ================================================================
# DTOs REQUEST / RESPONSE
# ================================================================
class RegistrarClienteReq(BaseModel):
    nombre:      str
    apellido:    str
    empresa:     str = ""
    email:       str
    telefono:    str = ""
    ciudad:      str = "Bogotá"
    departamento: str = "Cundinamarca"
    nit_cc:      str = ""
    password:    str

class LoginReq(BaseModel):
    email:    str
    password: str

class CrearTicketReq(BaseModel):
    tipo_servicio: str
    titulo:        str
    descripcion:   str
    prioridad:     str = "MEDIA"
    equipo_marca:  str = ""
    equipo_modelo: str = ""
    equipo_serial: str = ""

class AsignarTecnicoReq(BaseModel):
    tecnico_id: str

class ActualizarTicketReq(BaseModel):
    estado:      str   = None
    diagnostico: str   = None
    solucion:    str   = None
    costo_final: float = None
    en_espera_motivo: str = None

class CalificarTicketReq(BaseModel):
    calificacion: int
    comentario:   str = ""

class CrearAlquilerReq(BaseModel):
    equipo_tipo:  str
    equipo_marca: str = ""
    equipo_modelo: str = ""
    fecha_inicio: str                   # ISO 8601
    fecha_fin:    str                   # ISO 8601
    costo_diario: float

class RegistrarPagoReq(BaseModel):
    ticket_id: str
    monto:     float
    metodo:    str

class CrearTecnicoReq(BaseModel):
    nombre:        str
    apellido:      str
    email:         str
    telefono:      str = ""
    password:      str
    rol:           str = "TECNICO"
    especialidades: str = ""


# ================================================================
# ENDPOINT 1 — REGISTRAR CLIENTE
# ❌ MÚLTIPLES VIOLACIONES: negocio + SQL + email + WhatsApp en controlador
# ================================================================
@app.post("/api/clientes/registrar", tags=["Clientes"])
def registrar_cliente(req: RegistrarClienteReq):
    db: Session = SessionLocal()
    try:
        # ❌ VIOLACIÓN L199: Validación de email (regla de dominio) en controlador HTTP
        patron_email = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        if not re.match(patron_email, req.email):
            raise HTTPException(status_code=400, detail="Formato de email inválido")

        # ❌ VIOLACIÓN L204: Reglas de complejidad de password (dominio) en controlador
        if len(req.password) < 8:
            raise HTTPException(400, "La contraseña debe tener mínimo 8 caracteres")
        if not any(c.isupper() for c in req.password):
            raise HTTPException(400, "La contraseña debe incluir al menos una mayúscula")
        if not any(c.isdigit() for c in req.password):
            raise HTTPException(400, "La contraseña debe incluir al menos un número")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in req.password):
            raise HTTPException(400, "La contraseña debe incluir al menos un símbolo especial")

        # ❌ VIOLACIÓN L213: Validación de nombre/apellido (dominio) en controlador
        if len(req.nombre.strip()) < 2:
            raise HTTPException(400, "El nombre debe tener al menos 2 caracteres")
        if len(req.apellido.strip()) < 2:
            raise HTTPException(400, "El apellido debe tener al menos 2 caracteres")

        # ❌ VIOLACIÓN L219: Validación de teléfono colombiano (dominio) en controlador
        if req.telefono:
            telefono_limpio = re.sub(r'\D', '', req.telefono)
            if len(telefono_limpio) not in [7, 10, 12]:
                raise HTTPException(400, "Teléfono inválido. Ingresa un número colombiano válido.")

        # ❌ VIOLACIÓN L225: SQL directo en controlador para verificar duplicados
        existente = db.query(ClienteORM).filter(
            ClienteORM.email == req.email.strip().lower()
        ).first()
        if existente:
            raise HTTPException(409, "Ya existe una cuenta con ese correo electrónico")

        # ❌ VIOLACIÓN L232: Lógica de hashing y salting en controlador HTTP
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.sha256(f"{req.password}{salt}".encode()).hexdigest()

        # ❌ VIOLACIÓN L236: Creación del ORM directamente en el controlador
        cliente = ClienteORM(
            nombre     = req.nombre.strip().title(),
            apellido   = req.apellido.strip().title(),
            empresa    = req.empresa.strip(),
            email      = req.email.strip().lower(),
            telefono   = req.telefono,
            ciudad     = req.ciudad,
            departamento = req.departamento,
            nit_cc     = req.nit_cc,
            password_hash = f"{salt}:{pwd_hash}",
            plan       = PlanClienteEnum.BASICO,
            activo     = True,
            verificado = False,
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)

        # ❌ VIOLACIÓN L253: Generación de código de cliente + token de verificación en controlador
        codigo_cliente = f"TSP-{datetime.utcnow().year}-{cliente.id[:8].upper()}"
        token_verif    = secrets.token_urlsafe(32)
        sesion_verif   = SesionORM(
            usuario_id = cliente.id,
            tipo       = "verificacion",
            token      = token_verif,
            expira_en  = datetime.utcnow() + timedelta(hours=48),
        )
        db.add(sesion_verif)
        db.commit()

        # ❌ VIOLACIÓN L264: Email de bienvenida SMTP acoplado al controlador
        _enviar_email(
            destinatario = req.email,
            asunto       = "¡Bienvenido a TechSupport Pro! Verifica tu cuenta",
            cuerpo       = (
                f"Hola {req.nombre},\n\n"
                f"Tu código de cliente es: {codigo_cliente}\n"
                f"Verifica tu cuenta: https://techsupportpro.com.co/verificar/{token_verif}\n\n"
                f"El enlace expira en 48 horas.\n\nEquipo TechSupport Pro"
            )
        )

        # ❌ VIOLACIÓN L276: WhatsApp Business acoplado al controlador
        if req.telefono:
            _enviar_whatsapp(
                req.telefono,
                f"¡Hola {req.nombre}! 👋 Bienvenido a TechSupport Pro.\n"
                f"Tu código de cliente: {codigo_cliente}\n"
                f"Para soporte técnico, escríbenos aquí mismo."
            )

        # ❌ VIOLACIÓN L284: Registro de auditoría con SQL en controlador
        db.add(AuditoriaORM(
            usuario_id = cliente.id, tipo = "cliente",
            accion     = "REGISTRO",
            detalle    = f"Cliente {req.email} registrado con plan BASICO"
        ))
        db.commit()

        # ❌ VIOLACIÓN L292: Webhook a CRM externo desde el controlador
        try:
            requests.post(WEBHOOK_CRM, json={
                "evento":      "cliente_registrado",
                "cliente_id":  cliente.id,
                "email":       cliente.email,
                "plan":        "BASICO",
                "ciudad":      req.ciudad,
                "timestamp":   datetime.utcnow().isoformat()
            }, timeout=3)
        except Exception:
            pass

        return {
            "id":            cliente.id,
            "codigo_cliente": codigo_cliente,
            "email":         cliente.email,
            "plan":          cliente.plan.value,
            "mensaje":       "Cuenta creada. Revisa tu email para verificar."
        }
    finally:
        db.close()


# ================================================================
# ENDPOINT 2 — VERIFICAR EMAIL
# ❌ VIOLACIONES: transición de estado + SQL en controlador
# ================================================================
@app.get("/api/clientes/verificar/{token}", tags=["Clientes"])
def verificar_email(token: str):
    db: Session = SessionLocal()
    try:
        # ❌ VIOLACIÓN L319: SQL para buscar token en controlador
        sesion = db.query(SesionORM).filter(
            SesionORM.token == token,
            SesionORM.tipo  == "verificacion"
        ).first()
        if not sesion:
            raise HTTPException(404, "Token de verificación no encontrado")

        # ❌ VIOLACIÓN L327: Regla de negocio (expiración de token) en controlador
        if sesion.expira_en < datetime.utcnow():
            raise HTTPException(400, "El token de verificación ha expirado. Solicita uno nuevo.")
        if not sesion.activa:
            raise HTTPException(400, "Token ya utilizado")

        # ❌ VIOLACIÓN L333: Transición de estado PENDIENTE→VERIFICADO en controlador
        cliente = db.query(ClienteORM).filter(ClienteORM.id == sesion.usuario_id).first()
        if not cliente:
            raise HTTPException(404, "Cliente no encontrado")
        cliente.verificado = True
        sesion.activa      = False
        db.commit()

        # ❌ VIOLACIÓN L341: Email de confirmación de verificación en controlador
        _enviar_email(
            cliente.email,
            "Cuenta verificada — TechSupport Pro",
            f"Hola {cliente.nombre}, tu cuenta fue verificada. Ya puedes crear tickets de soporte."
        )

        return {"mensaje": "Email verificado correctamente. Ya puedes iniciar sesión."}
    finally:
        db.close()


# ================================================================
# ENDPOINT 3 — LOGIN
# ❌ VIOLACIONES: seguridad + bloqueo + sesión en controlador
# ================================================================
@app.post("/api/clientes/login", tags=["Clientes"])
def login_cliente(req: LoginReq):
    db: Session = SessionLocal()
    try:
        # ❌ VIOLACIÓN L357: SQL directo en controlador de login
        cliente = db.query(ClienteORM).filter(
            ClienteORM.email == req.email.strip().lower()
        ).first()
        if not cliente:
            raise HTTPException(401, "Credenciales inválidas")

        # ❌ VIOLACIÓN L364: Regla de negocio (cuenta activa) en controlador
        if not cliente.activo:
            raise HTTPException(403, "Cuenta suspendida. Escríbenos a soporte@techsupportpro.com.co")

        # ❌ VIOLACIÓN L368: Regla de negocio (cuenta verificada) en controlador
        if not cliente.verificado:
            raise HTTPException(403, "Debes verificar tu email antes de iniciar sesión")

        # ❌ VIOLACIÓN L372: Regla de negocio (bloqueo por intentos) en controlador
        MAX_INTENTOS = 5
        if cliente.intentos_login >= MAX_INTENTOS:
            raise HTTPException(
                403,
                f"Cuenta bloqueada por {MAX_INTENTOS} intentos fallidos. "
                f"Contacta soporte: {WHATSAPP_PHONE}"
            )

        # ❌ VIOLACIÓN L381: Lógica de verificación de hash en controlador
        partes    = cliente.password_hash.split(":")
        hash_calc = hashlib.sha256(f"{req.password}{partes[0]}".encode()).hexdigest()
        if hash_calc != partes[1]:
            # ❌ VIOLACIÓN L386: Incremento de intentos + transición de estado en controlador
            cliente.intentos_login += 1
            if cliente.intentos_login >= MAX_INTENTOS:
                cliente.activo = False  # suspender automáticamente
                _enviar_email(
                    cliente.email,
                    "Cuenta bloqueada por seguridad — TechSupport Pro",
                    f"Hola {cliente.nombre}, tu cuenta fue bloqueada por {MAX_INTENTOS} intentos fallidos."
                )
            db.commit()
            raise HTTPException(401, "Credenciales inválidas")

        # ❌ VIOLACIÓN L397: Resetear intentos + último login en controlador
        cliente.intentos_login = 0
        cliente.ultimo_login   = datetime.utcnow()
        db.commit()

        # ❌ VIOLACIÓN L402: Creación de sesión con lógica en controlador
        token = secrets.token_urlsafe(48)
        sesion = SesionORM(
            usuario_id = cliente.id, tipo = "cliente",
            token      = token,
            expira_en  = datetime.utcnow() + timedelta(hours=12),
        )
        db.add(sesion)
        # ❌ VIOLACIÓN L410: Auditoría con SQL directo en controlador
        db.add(AuditoriaORM(
            usuario_id=cliente.id, tipo="cliente",
            accion="LOGIN", detalle="Login exitoso"
        ))
        db.commit()

        return {
            "token":      token,
            "cliente_id": cliente.id,
            "nombre":     f"{cliente.nombre} {cliente.apellido}",
            "plan":       cliente.plan.value,
            "expira_en":  (datetime.utcnow() + timedelta(hours=12)).isoformat()
        }
    finally:
        db.close()


# ================================================================
# ENDPOINT 4 — CREAR TICKET DE SERVICIO
# ❌ VIOLACIONES: reglas de negocio + asignación + email + WhatsApp
# ================================================================
@app.post("/api/tickets", tags=["Tickets"])
def crear_ticket(req: CrearTicketReq, authorization: str = Header(None)):
    db: Session = SessionLocal()
    try:
        # ❌ VIOLACIÓN L429: Autenticación inline en cada endpoint (duplicada)
        cliente_id = _auth_cliente(db, authorization)

        # ❌ VIOLACIÓN L432: Validación de enum (dominio) en controlador
        try:
            tipo = TipoServicioEnum(req.tipo_servicio.upper())
        except ValueError:
            raise HTTPException(400, f"Tipo de servicio inválido: {req.tipo_servicio}. "
                                     f"Válidos: {[e.value for e in TipoServicioEnum]}")

        try:
            prioridad = PrioridadEnum(req.prioridad.upper())
        except ValueError:
            raise HTTPException(400, f"Prioridad inválida: {req.prioridad}")

        # ❌ VIOLACIÓN L441: Regla de negocio (título mínimo) en controlador
        if len(req.titulo.strip()) < 10:
            raise HTTPException(400, "El título debe ser descriptivo (mínimo 10 caracteres)")
        if len(req.descripcion.strip()) < 20:
            raise HTTPException(400, "La descripción debe detallar el problema (mínimo 20 caracteres)")

        # ❌ VIOLACIÓN L447: Regla de negocio (límite tickets por plan) en controlador
        cliente = db.query(ClienteORM).filter(ClienteORM.id == cliente_id).first()
        estados_abiertos = [
            EstadoTicketEnum.NUEVO, EstadoTicketEnum.ASIGNADO,
            EstadoTicketEnum.DIAGNOSTICO, EstadoTicketEnum.EN_PROCESO,
            EstadoTicketEnum.EN_ESPERA
        ]
        tickets_abiertos = db.query(TicketORM).filter(
            TicketORM.cliente_id == cliente_id,
            TicketORM.estado.in_(estados_abiertos)
        ).count()

        # ❌ VIOLACIÓN L460: Lógica de límites por plan hardcoded en controlador
        limite_por_plan = {
            PlanClienteEnum.BASICO:      2,
            PlanClienteEnum.PROFESIONAL: 8,
            PlanClienteEnum.EMPRESARIAL: 50
        }
        limite = limite_por_plan.get(cliente.plan, 2)
        if tickets_abiertos >= limite:
            raise HTTPException(400,
                f"Plan {cliente.plan.value}: máximo {limite} tickets abiertos simultáneos. "
                f"Actualiza tu plan en techsupportpro.com.co/planes"
            )

        # ❌ VIOLACIÓN L470: Generación de número de ticket (dominio) en controlador
        año  = datetime.utcnow().year
        mes  = datetime.utcnow().month
        seq  = db.query(TicketORM).count() + 1
        numero_ticket = f"TSP-{año}{mes:02d}-{seq:05d}"

        # ❌ VIOLACIÓN L477: Tabla de costos base por tipo (dominio) en controlador
        costos_base = {
            TipoServicioEnum.SOPORTE_PRESENCIAL:   85_000,
            TipoServicioEnum.SOPORTE_REMOTO:       45_000,
            TipoServicioEnum.REPARACION_PC:       130_000,
            TipoServicioEnum.REPARACION_LAPTOP:   150_000,
            TipoServicioEnum.REPARACION_IMPRESORA:125_000,
            TipoServicioEnum.MANTENIMIENTO_PREV:  100_000,
            TipoServicioEnum.ALQUILER_EQUIPO:           0,  # se gestiona en endpoint propio
            TipoServicioEnum.DESARROLLO_SOFTWARE:       0,  # cotización
            TipoServicioEnum.CONSULTORIA_TI:       90_000,
        }
        costo_estimado = costos_base.get(tipo, 0)

        # ❌ VIOLACIÓN L491: Recargo por prioridad (regla de negocio) en controlador
        recargos = {
            PrioridadEnum.BAJA:    0.0,
            PrioridadEnum.MEDIA:   0.0,
            PrioridadEnum.ALTA:    0.35,
            PrioridadEnum.CRITICA: 0.70,
        }
        costo_estimado = round(costo_estimado * (1 + recargos[prioridad]))

        # ❌ VIOLACIÓN L500: Descuento por plan (regla de negocio) en controlador
        descuentos = {
            PlanClienteEnum.BASICO:      0.0,
            PlanClienteEnum.PROFESIONAL: 0.15,
            PlanClienteEnum.EMPRESARIAL: 0.25,
        }
        costo_estimado = round(costo_estimado * (1 - descuentos[cliente.plan]))

        # ❌ VIOLACIÓN L509: Creación del ORM en el controlador
        ticket = TicketORM(
            numero        = numero_ticket,
            cliente_id    = cliente_id,
            tipo_servicio = tipo,
            prioridad     = prioridad,
            titulo        = req.titulo.strip(),
            descripcion   = req.descripcion.strip(),
            equipo_marca  = req.equipo_marca,
            equipo_modelo = req.equipo_modelo,
            equipo_serial = req.equipo_serial,
            costo_estimado = costo_estimado,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        # ❌ VIOLACIÓN L524: Asignación automática de técnico (dominio) en controlador
        tecnico_asignado = None
        tecnicos_disp = db.query(TecnicoORM).filter(
            TecnicoORM.disponible  == True,
            TecnicoORM.activo      == True,
        ).order_by(TecnicoORM.tickets_activos.asc()).first()

        if tecnicos_disp:
            ticket.tecnico_id       = tecnicos_disp.id
            ticket.estado           = EstadoTicketEnum.ASIGNADO
            tecnicos_disp.tickets_activos += 1
            tecnico_asignado = tecnicos_disp
            db.commit()

        # ❌ VIOLACIÓN L537: Email de confirmación al cliente en controlador
        _enviar_email(
            cliente.email,
            f"Ticket {numero_ticket} recibido — TechSupport Pro",
            (
                f"Hola {cliente.nombre},\n\n"
                f"Recibimos tu solicitud de {tipo.value}.\n"
                f"Número de ticket: {numero_ticket}\n"
                f"Prioridad: {prioridad.value}\n"
                f"Costo estimado: ${costo_estimado:,.0f} COP\n"
                f"Técnico: {tecnico_asignado.nombre if tecnico_asignado else 'Asignando...'}\n\n"
                f"Seguimiento: techsupportpro.com.co/mis-tickets\n\nEquipo TechSupport Pro"
            )
        )

        # ❌ VIOLACIÓN L552: WhatsApp al técnico asignado en controlador
        if tecnico_asignado and tecnico_asignado.telefono:
            _enviar_whatsapp(
                tecnico_asignado.telefono,
                f"🔔 Nuevo ticket asignado: {numero_ticket}\n"
                f"Servicio: {tipo.value} | Prioridad: {prioridad.value}\n"
                f"Cliente: {cliente.nombre} {cliente.apellido}\n"
                f"Descripción: {req.descripcion[:120]}..."
            )

        # ❌ VIOLACIÓN L561: Auditoría SQL en controlador
        db.add(AuditoriaORM(
            usuario_id=cliente_id, tipo="cliente",
            accion="CREAR_TICKET",
            detalle=f"Ticket {numero_ticket} creado — {tipo.value}"
        ))
        db.commit()

        return {
            "id":             ticket.id,
            "numero":         numero_ticket,
            "estado":         ticket.estado.value,
            "costo_estimado": costo_estimado,
            "tecnico":        f"{tecnico_asignado.nombre}" if tecnico_asignado else "Pendiente de asignación",
            "mensaje":        "Ticket creado. Recibirás actualizaciones por email y WhatsApp."
        }
    finally:
        db.close()


# ================================================================
# ENDPOINT 5 — ACTUALIZAR TICKET (técnico)
# ❌ VIOLACIONES: máquina de estados + validaciones en controlador
# ================================================================
@app.put("/api/tickets/{ticket_id}", tags=["Tickets"])
def actualizar_ticket(ticket_id: str, req: ActualizarTicketReq,
                       authorization: str = Header(None)):
    db: Session = SessionLocal()
    try:
        # ❌ VIOLACIÓN L586: Segunda copia del bloque de autenticación (técnico)
        tecnico_id = _auth_tecnico(db, authorization)

        ticket = db.query(TicketORM).filter(TicketORM.id == ticket_id).first()
        if not ticket:
            raise HTTPException(404, "Ticket no encontrado")

        # ❌ VIOLACIÓN L593: Regla de autorización (técnico propietario) en controlador
        tecnico = db.query(TecnicoORM).filter(TecnicoORM.id == tecnico_id).first()
        if tecnico.rol not in [RolEnum.ADMIN, RolEnum.SUPERADMIN]:
            if ticket.tecnico_id != tecnico_id:
                raise HTTPException(403, "Solo puedes actualizar tickets asignados a ti")

        if req.estado:
            # ❌ VIOLACIÓN L601: Máquina de estados del dominio implementada en controlador
            transiciones = {
                EstadoTicketEnum.NUEVO:       [EstadoTicketEnum.ASIGNADO, EstadoTicketEnum.CANCELADO],
                EstadoTicketEnum.ASIGNADO:    [EstadoTicketEnum.DIAGNOSTICO, EstadoTicketEnum.CANCELADO],
                EstadoTicketEnum.DIAGNOSTICO: [EstadoTicketEnum.EN_PROCESO, EstadoTicketEnum.EN_ESPERA, EstadoTicketEnum.CANCELADO],
                EstadoTicketEnum.EN_PROCESO:  [EstadoTicketEnum.EN_ESPERA, EstadoTicketEnum.RESUELTO, EstadoTicketEnum.CANCELADO],
                EstadoTicketEnum.EN_ESPERA:   [EstadoTicketEnum.EN_PROCESO, EstadoTicketEnum.CANCELADO],
                EstadoTicketEnum.RESUELTO:    [EstadoTicketEnum.CERRADO],
                EstadoTicketEnum.CERRADO:     [],
                EstadoTicketEnum.CANCELADO:   [],
            }
            try:
                nuevo_estado = EstadoTicketEnum(req.estado.upper())
            except ValueError:
                raise HTTPException(400, f"Estado inválido: {req.estado}")

            # ❌ VIOLACIÓN L618: Validación de transición en controlador
            if nuevo_estado not in transiciones.get(ticket.estado, []):
                raise HTTPException(400,
                    f"Transición inválida: {ticket.estado.value} → {nuevo_estado.value}. "
                    f"Permitidas: {[e.value for e in transiciones.get(ticket.estado, [])]}")

            # ❌ VIOLACIÓN L625: Regla 'RESUELTO requiere diagnóstico' en controlador
            if nuevo_estado == EstadoTicketEnum.RESUELTO:
                if not req.diagnostico and not ticket.diagnostico:
                    raise HTTPException(400, "El diagnóstico es obligatorio al marcar como RESUELTO")
                if not req.solucion and not ticket.solucion:
                    raise HTTPException(400, "La solución es obligatoria al marcar como RESUELTO")
                ticket.resuelto_en = datetime.utcnow()
                # ❌ VIOLACIÓN L633: Cálculo de tiempo de resolución en controlador
                delta = ticket.resuelto_en - ticket.creado_en
                ticket.tiempo_resolucion_horas = round(delta.total_seconds() / 3600, 2)
                # ❌ VIOLACIÓN L637: Actualización de contador del técnico en controlador
                if tecnico.tickets_activos > 0:
                    tecnico.tickets_activos -= 1

            ticket.estado = nuevo_estado

        if req.diagnostico:    ticket.diagnostico = req.diagnostico
        if req.solucion:       ticket.solucion    = req.solucion
        if req.costo_final is not None:
            # ❌ VIOLACIÓN L645: Validación de costo (dominio) en controlador
            if req.costo_final < 0:
                raise HTTPException(400, "El costo final no puede ser negativo")
            ticket.costo_final = req.costo_final

        ticket.actualizado_en = datetime.utcnow()
        db.commit()

        # ❌ VIOLACIÓN L654: Notificación al cliente cuando se resuelve en controlador
        if req.estado and ticket.estado == EstadoTicketEnum.RESUELTO:
            cliente = db.query(ClienteORM).filter(ClienteORM.id == ticket.cliente_id).first()
            if cliente:
                _enviar_email(
                    cliente.email,
                    f"✅ Ticket {ticket.numero} resuelto — TechSupport Pro",
                    (
                        f"Hola {cliente.nombre},\n\n"
                        f"Tu ticket fue resuelto.\n"
                        f"Diagnóstico: {ticket.diagnostico}\n"
                        f"Solución: {ticket.solucion}\n"
                        f"Costo final: ${ticket.costo_final:,.0f} COP\n"
                        f"Tiempo de resolución: {ticket.tiempo_resolucion_horas:.1f} horas\n\n"
                        f"Por favor califica el servicio en: techsupportpro.com.co/calificar/{ticket.id}"
                    )
                )

        return {
            "id":     ticket.id,
            "numero": ticket.numero,
            "estado": ticket.estado.value,
            "costo_final": ticket.costo_final
        }
    finally:
        db.close()


# ================================================================
# ENDPOINT 6 — CALIFICAR TICKET
# ❌ VIOLACIONES: reglas de calificación en controlador
# ================================================================
@app.post("/api/tickets/{ticket_id}/calificar", tags=["Tickets"])
def calificar_ticket(ticket_id: str, req: CalificarTicketReq,
                      authorization: str = Header(None)):
    db: Session = SessionLocal()
    try:
        # ❌ VIOLACIÓN L685: Tercera copia del bloque de autenticación de cliente
        cliente_id = _auth_cliente(db, authorization)

        ticket = db.query(TicketORM).filter(TicketORM.id == ticket_id).first()
        if not ticket:
            raise HTTPException(404, "Ticket no encontrado")

        # ❌ VIOLACIÓN L692: Regla de negocio (solo el dueño puede calificar) en controlador
        if ticket.cliente_id != cliente_id:
            raise HTTPException(403, "Solo puedes calificar tus propios tickets")

        # ❌ VIOLACIÓN L697: Regla (solo tickets resueltos) en controlador
        if ticket.estado not in [EstadoTicketEnum.RESUELTO, EstadoTicketEnum.CERRADO]:
            raise HTTPException(400, "Solo puedes calificar tickets resueltos o cerrados")

        # ❌ VIOLACIÓN L702: Regla (no calificar dos veces) en controlador
        if ticket.calificacion is not None:
            raise HTTPException(400, "Este ticket ya fue calificado")

        # ❌ VIOLACIÓN L707: Validación de rango de calificación (dominio) en controlador
        if not 1 <= req.calificacion <= 5:
            raise HTTPException(400, "La calificación debe estar entre 1 y 5 estrellas")

        ticket.calificacion     = req.calificacion
        ticket.comentario_calif = req.comentario
        ticket.estado           = EstadoTicketEnum.CERRADO
        db.commit()

        # ❌ VIOLACIÓN L716: Recalcular calificación del técnico con SQL en controlador
        if ticket.tecnico_id:
            tickets_calif = db.query(TicketORM).filter(
                TicketORM.tecnico_id   == ticket.tecnico_id,
                TicketORM.calificacion != None
            ).all()
            if tickets_calif:
                promedio = sum(t.calificacion for t in tickets_calif) / len(tickets_calif)
                tecnico  = db.query(TecnicoORM).filter(TecnicoORM.id == ticket.tecnico_id).first()
                if tecnico:
                    tecnico.calificacion = round(promedio, 2)
                    db.commit()

        return {"mensaje": f"¡Gracias por tu calificación de {req.calificacion} estrellas!",
                "estado":  ticket.estado.value}
    finally:
        db.close()


# ================================================================
# ENDPOINT 7 — MIS TICKETS (cliente)
# ❌ VIOLACIONES: filtros SQL + métricas en controlador
# ================================================================
@app.get("/api/clientes/mis-tickets", tags=["Clientes"])
def mis_tickets(estado: str = None, tipo: str = None, authorization: str = Header(None)):
    db: Session = SessionLocal()
    try:
        # ❌ VIOLACIÓN L742: Cuarta copia de autenticación
        cliente_id = _auth_cliente(db, authorization)

        # ❌ VIOLACIÓN L745: Construcción dinámica de query SQL en controlador
        query = db.query(TicketORM).filter(TicketORM.cliente_id == cliente_id)
        if estado:
            try:
                query = query.filter(TicketORM.estado == EstadoTicketEnum(estado.upper()))
            except ValueError:
                raise HTTPException(400, f"Estado inválido: {estado}")
        if tipo:
            try:
                query = query.filter(TicketORM.tipo_servicio == TipoServicioEnum(tipo.upper()))
            except ValueError:
                raise HTTPException(400, f"Tipo inválido: {tipo}")

        tickets = query.order_by(TicketORM.creado_en.desc()).all()

        # ❌ VIOLACIÓN L759: Cálculo de métricas de negocio en controlador
        resueltos      = sum(1 for t in tickets if t.estado == EstadoTicketEnum.RESUELTO)
        cerrados       = sum(1 for t in tickets if t.estado == EstadoTicketEnum.CERRADO)
        gasto_total    = sum(t.costo_final or 0 for t in tickets)
        calif_promedio = (
            sum(t.calificacion for t in tickets if t.calificacion) /
            len([t for t in tickets if t.calificacion])
        ) if any(t.calificacion for t in tickets) else None

        return {
            "tickets": [{
                "id": t.id, "numero": t.numero,
                "tipo": t.tipo_servicio.value, "estado": t.estado.value,
                "titulo": t.titulo, "prioridad": t.prioridad.value,
                "costo_estimado": t.costo_estimado, "costo_final": t.costo_final,
                "creado_en": t.creado_en.isoformat()
            } for t in tickets],
            "resumen": {
                "total": len(tickets), "resueltos": resueltos + cerrados,
                "gasto_total_cop": gasto_total,
                "calificacion_promedio": calif_promedio
            }
        }
    finally:
        db.close()


# ================================================================
# ENDPOINT 8 — CREAR ALQUILER DE EQUIPO
# ❌ VIOLACIONES: reglas de negocio + cálculos + email en controlador
# ================================================================
@app.post("/api/alquileres", tags=["Alquileres"])
def crear_alquiler(req: CrearAlquilerReq, authorization: str = Header(None)):
    db: Session = SessionLocal()
    try:
        # ❌ VIOLACIÓN L830: Autenticación duplicada (séptima copia)
        cliente_id = _auth_cliente(db, authorization)

        # ❌ VIOLACIÓN L833: Validación de fechas (dominio) en controlador
        try:
            f_inicio = datetime.fromisoformat(req.fecha_inicio)
            f_fin    = datetime.fromisoformat(req.fecha_fin)
        except ValueError:
            raise HTTPException(400, "Formato de fecha inválido. Use ISO 8601 (YYYY-MM-DD)")

        if f_inicio < datetime.utcnow():
            raise HTTPException(400, "La fecha de inicio no puede ser en el pasado")

        if f_inicio >= f_fin:
            raise HTTPException(400, "La fecha de fin debe ser posterior a la de inicio")

        # ❌ VIOLACIÓN L843: Regla de negocio (mínimo 1 día) en controlador
        dias = (f_fin - f_inicio).days
        if dias < 1:
            raise HTTPException(400, "El alquiler mínimo es de 1 día")

        # ❌ VIOLACIÓN L848: Regla de negocio (máximo por plan) en controlador
        cliente = db.query(ClienteORM).filter(ClienteORM.id == cliente_id).first()
        max_dias_plan = {
            PlanClienteEnum.BASICO:      30,
            PlanClienteEnum.PROFESIONAL: 90,
            PlanClienteEnum.EMPRESARIAL: 365,
        }
        max_dias = max_dias_plan.get(cliente.plan, 30)
        if dias > max_dias:
            raise HTTPException(400,
                f"Plan {cliente.plan.value}: máximo {max_dias} días de alquiler. "
                f"Actualiza tu plan en techsupportpro.com.co/planes")

        # ❌ VIOLACIÓN L860: Regla de negocio (costo mínimo diario) en controlador
        if req.costo_diario < 20_000:
            raise HTTPException(400, "El costo diario mínimo de alquiler es $20,000 COP")

        # ❌ VIOLACIÓN L865: Validación de tipo de equipo (dominio) en controlador
        tipos_validos = ["laptop", "desktop", "impresora", "servidor", "tablet",
                         "monitor", "proyector", "switch", "router"]
        if req.equipo_tipo.lower() not in tipos_validos:
            raise HTTPException(400,
                f"Tipo de equipo inválido. Disponibles: {', '.join(tipos_validos)}")

        # ❌ VIOLACIÓN L873: Cálculo de costo total y depósito (dominio) en controlador
        costo_total = round(req.costo_diario * dias)

        # Descuento por cantidad de días (regla de negocio hardcoded en controlador)
        if dias >= 30:
            costo_total = round(costo_total * 0.85)   # 15% descuento mes completo
        elif dias >= 7:
            costo_total = round(costo_total * 0.92)   # 8% descuento semana completa

        # Descuento adicional por plan
        desc_plan = {
            PlanClienteEnum.BASICO:      0.0,
            PlanClienteEnum.PROFESIONAL: 0.10,
            PlanClienteEnum.EMPRESARIAL: 0.20,
        }
        costo_total = round(costo_total * (1 - desc_plan[cliente.plan]))
        deposito    = round(costo_total * 0.30)  # 30% de depósito

        # ❌ VIOLACIÓN L889: Verificar solapamiento de alquileres activos en controlador
        alquileres_activos = db.query(AlquilerEquipoORM).filter(
            AlquilerEquipoORM.cliente_id == cliente_id,
            AlquilerEquipoORM.estado     == "activo"
        ).count()
        if cliente.plan == PlanClienteEnum.BASICO and alquileres_activos >= 1:
            raise HTTPException(400, "Plan Básico: solo 1 alquiler activo simultáneo. "
                                      "Actualiza tu plan para alquilar más equipos.")

        # ❌ VIOLACIÓN L898: Creación del ORM en el controlador
        alquiler = AlquilerEquipoORM(
            cliente_id    = cliente_id,
            equipo_tipo   = req.equipo_tipo.lower(),
            equipo_marca  = req.equipo_marca,
            equipo_modelo = req.equipo_modelo,
            fecha_inicio  = f_inicio,
            fecha_fin     = f_fin,
            dias          = dias,
            costo_diario  = req.costo_diario,
            costo_total   = costo_total,
            deposito      = deposito,
            estado        = "activo"
        )
        db.add(alquiler)
        db.commit()
        db.refresh(alquiler)

        # ❌ VIOLACIÓN L914: Email de confirmación de alquiler en controlador
        _enviar_email(
            cliente.email,
            f"Alquiler confirmado — TechSupport Pro",
            (
                f"Hola {cliente.nombre},\n\n"
                f"Tu alquiler fue registrado exitosamente.\n\n"
                f"Equipo: {req.equipo_tipo} {req.equipo_marca} {req.equipo_modelo}\n"
                f"Desde: {req.fecha_inicio}  Hasta: {req.fecha_fin}  ({dias} días)\n"
                f"Costo total: ${costo_total:,.0f} COP\n"
                f"Depósito requerido: ${deposito:,.0f} COP\n\n"
                f"El equipo estará listo para entrega en la fecha de inicio.\n"
                f"Para coordinar, escríbenos al {WHATSAPP_PHONE}\n\n"
                f"TechSupport Pro"
            )
        )

        # ❌ VIOLACIÓN L931: WhatsApp al cliente en controlador
        if cliente.telefono:
            _enviar_whatsapp(
                cliente.telefono,
                f"📦 Alquiler confirmado!\n"
                f"Equipo: {req.equipo_tipo} · {dias} días\n"
                f"Total: ${costo_total:,.0f} COP · Depósito: ${deposito:,.0f} COP\n"
                f"Desde {req.fecha_inicio} hasta {req.fecha_fin}"
            )

        # ❌ VIOLACIÓN L940: Auditoría con SQL directo en controlador
        db.add(AuditoriaORM(
            usuario_id = cliente_id, tipo = "cliente",
            accion     = "CREAR_ALQUILER",
            detalle    = f"Alquiler {alquiler.id[:8]} — {req.equipo_tipo} por {dias} días"
        ))
        db.commit()

        return {
            "id":          alquiler.id,
            "equipo":      f"{req.equipo_tipo} {req.equipo_marca}".strip(),
            "dias":        dias,
            "costo_total": costo_total,
            "deposito":    deposito,
            "fecha_inicio": req.fecha_inicio,
            "fecha_fin":    req.fecha_fin,
            "mensaje":     f"Alquiler confirmado. Depósito de ${deposito:,.0f} COP requerido al retirar."
        }
    finally:
        db.close()


# ================================================================
# ENDPOINT 9 — REGISTRAR PAGO
# ❌ VIOLACIONES: pasarela de pagos + reglas en controlador
# ================================================================
@app.post("/api/pagos", tags=["Pagos"])
def registrar_pago(req: RegistrarPagoReq, authorization: str = Header(None)):
    db: Session = SessionLocal()
    try:
        # ❌ VIOLACIÓN L789: Quinta copia de autenticación
        cliente_id = _auth_cliente(db, authorization)

        # ❌ VIOLACIÓN L792: Validaciones de negocio en controlador
        if req.monto <= 0:
            raise HTTPException(400, "El monto debe ser mayor a cero")
        if req.monto < 10_000:
            raise HTTPException(400, "El monto mínimo de pago es $10,000 COP")
        if req.monto > 50_000_000:
            raise HTTPException(400, "El monto máximo por transacción es $50,000,000 COP")

        # ❌ VIOLACIÓN L799: Validación de método de pago (dominio) en controlador
        metodos_validos = ["efectivo", "nequi", "daviplata", "tarjeta_credito",
                           "tarjeta_debito", "transferencia_pse"]
        if req.metodo.lower() not in metodos_validos:
            raise HTTPException(400, f"Método inválido. Use: {', '.join(metodos_validos)}")

        # ❌ VIOLACIÓN L806: Integración con Wompi (pasarela Colombia) en controlador
        referencia = None
        if req.metodo in ["tarjeta_credito", "tarjeta_debito"]:
            try:
                resp = requests.post(
                    "https://sandbox.wompi.co/v1/transactions",
                    headers={"Authorization": f"Bearer {WOMPI_KEY}"},
                    json={
                        "amount_in_cents": int(req.monto * 100),
                        "currency":        "COP",
                        "reference":       f"TSP-{uuid4().hex[:8]}",
                    },
                    timeout=10
                )
                data = resp.json()
                referencia = data.get("data", {}).get("id")
                if not referencia:
                    raise HTTPException(502, "Error procesando pago con pasarela")
            except requests.Timeout:
                raise HTTPException(504, "Timeout conectando con la pasarela de pagos")

        pago = PagoORM(
            ticket_id  = req.ticket_id,
            cliente_id = cliente_id,
            monto      = req.monto,
            metodo     = req.metodo,
            referencia = referencia,
            estado     = "aprobado" if req.metodo == "efectivo" else "pendiente"
        )
        db.add(pago)
        db.commit()

        # ❌ VIOLACIÓN L830: Email de recibo de pago en controlador
        cliente = db.query(ClienteORM).filter(ClienteORM.id == cliente_id).first()
        _enviar_email(
            cliente.email,
            f"Recibo de pago #{pago.id[:8].upper()} — TechSupport Pro",
            f"Monto: ${req.monto:,.0f} COP\nMétodo: {req.metodo}\n"
            f"Estado: {pago.estado}\nReferencia: {referencia or 'N/A'}"
        )

        return {"id": pago.id, "monto": pago.monto,
                "metodo": pago.metodo, "estado": pago.estado,
                "referencia": referencia}
    finally:
        db.close()


# ================================================================
# ENDPOINT 10 — DASHBOARD ADMIN
# ❌ VIOLACIONES: múltiples queries + métricas complejas en controlador
# ================================================================
@app.get("/api/admin/dashboard", tags=["Admin"])
def dashboard_admin(authorization: str = Header(None)):
    db: Session = SessionLocal()
    try:
        # ❌ VIOLACIÓN L851: Sexta copia de autenticación (técnico/admin)
        tecnico_id = _auth_tecnico(db, authorization)
        tecnico    = db.query(TecnicoORM).filter(TecnicoORM.id == tecnico_id).first()
        if tecnico.rol not in [RolEnum.ADMIN, RolEnum.SUPERADMIN]:
            raise HTTPException(403, "Acceso solo para administradores")

        # ❌ VIOLACIÓN L857: Múltiples queries SQL + cálculos de negocio en controlador
        ahora       = datetime.utcnow()
        inicio_mes  = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        inicio_hoy  = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

        total_clientes    = db.query(ClienteORM).filter(ClienteORM.activo==True).count()
        clientes_mes      = db.query(ClienteORM).filter(ClienteORM.creado_en>=inicio_mes).count()
        total_tecnicos    = db.query(TecnicoORM).filter(TecnicoORM.activo==True).count()
        tickets_hoy       = db.query(TicketORM).filter(TicketORM.creado_en>=inicio_hoy).count()
        tickets_abiertos  = db.query(TicketORM).filter(
            TicketORM.estado.in_([EstadoTicketEnum.NUEVO, EstadoTicketEnum.ASIGNADO,
                                   EstadoTicketEnum.EN_PROCESO])
        ).count()
        tickets_criticos  = db.query(TicketORM).filter(
            TicketORM.prioridad == PrioridadEnum.CRITICA,
            TicketORM.estado.notin_([EstadoTicketEnum.CERRADO, EstadoTicketEnum.CANCELADO])
        ).count()

        # ❌ VIOLACIÓN L875: Cálculo de ingresos del mes (negocio) en controlador
        pagos_mes    = db.query(PagoORM).filter(
            PagoORM.creado_en>=inicio_mes, PagoORM.estado=="aprobado"
        ).all()
        ingresos_mes = sum(p.monto for p in pagos_mes)

        # ❌ VIOLACIÓN L882: Cálculo de tasa de resolución (negocio) en controlador
        todos = db.query(TicketORM).filter(TicketORM.creado_en>=inicio_mes).count()
        resueltos_mes = db.query(TicketORM).filter(
            TicketORM.creado_en>=inicio_mes,
            TicketORM.estado.in_([EstadoTicketEnum.RESUELTO, EstadoTicketEnum.CERRADO])
        ).count()
        tasa_resolucion = round(resueltos_mes / todos * 100, 1) if todos else 0

        # ❌ VIOLACIÓN L891: Tiempo promedio de resolución (negocio) en controlador
        tickets_con_tiempo = db.query(TicketORM).filter(
            TicketORM.tiempo_resolucion_horas != None
        ).all()
        tiempo_prom = (
            sum(t.tiempo_resolucion_horas for t in tickets_con_tiempo) / len(tickets_con_tiempo)
        ) if tickets_con_tiempo else 0

        return {
            "clientes":    {"total": total_clientes, "nuevos_mes": clientes_mes},
            "tecnicos":    {"activos": total_tecnicos},
            "tickets":     {
                "hoy": tickets_hoy, "abiertos": tickets_abiertos,
                "criticos_pendientes": tickets_criticos,
                "tasa_resolucion_pct": tasa_resolucion,
                "tiempo_prom_resolucion_h": round(tiempo_prom, 1)
            },
            "finanzas":    {"ingresos_mes_cop": ingresos_mes}
        }
    finally:
        db.close()


# ================================================================
# HELPERS — infraestructura y autenticación acopladas al módulo
# ================================================================
def _auth_cliente(db: Session, authorization: str) -> str:
    """❌ VIOLACIÓN L916: Lógica de auth duplicada — versión cliente"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token de autenticación requerido")
    token  = authorization.split(" ")[1]
    sesion = db.query(SesionORM).filter(
        SesionORM.token == token,
        SesionORM.tipo  == "cliente",
        SesionORM.activa == True
    ).first()
    if not sesion or sesion.expira_en < datetime.utcnow():
        raise HTTPException(401, "Sesión inválida o expirada. Inicia sesión de nuevo.")
    return sesion.usuario_id


def _auth_tecnico(db: Session, authorization: str) -> str:
    """❌ VIOLACIÓN L928: Lógica de auth duplicada — versión técnico (casi idéntica)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token de autenticación requerido")
    token  = authorization.split(" ")[1]
    sesion = db.query(SesionORM).filter(
        SesionORM.token == token,
        SesionORM.tipo  == "tecnico",
        SesionORM.activa == True
    ).first()
    if not sesion or sesion.expira_en < datetime.utcnow():
        raise HTTPException(401, "Sesión inválida o expirada. Inicia sesión de nuevo.")
    return sesion.usuario_id


def _enviar_email(destinatario: str, asunto: str, cuerpo: str) -> None:
    """
    ❌ VIOLACIÓN L941: Infraestructura SMTP con credenciales hardcoded en main.py.
    Imposible de testear sin servidor SMTP real.
    Imposible de reemplazar por SendGrid/SES sin tocar el módulo de negocio.
    """
    try:
        msg            = MIMEText(cuerpo, "plain", "utf-8")
        msg["Subject"] = asunto
        msg["From"]    = SMTP_USER
        msg["To"]      = destinatario
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    except Exception as e:
        # ❌ VIOLACIÓN L954: Error de infraestructura silenciado sin logging adecuado
        print(f"[ERROR EMAIL] {e}")


def _enviar_whatsapp(telefono: str, mensaje: str) -> None:
    """
    ❌ VIOLACIÓN L959: WhatsApp Business API con token hardcoded en main.py.
    Imposible de reemplazar o mockear en pruebas.
    """
    try:
        requests.post(
            "https://graph.facebook.com/v18.0/techsupportpro_phone_id/messages",
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type":  "application/json"
            },
            json={
                "messaging_product": "whatsapp",
                "to":   telefono,
                "type": "text",
                "text": {"body": mensaje}
            },
            timeout=4
        )
    except Exception:
        pass  # ❌ VIOLACIÓN L975: Error de infraestructura silenciado completamente
