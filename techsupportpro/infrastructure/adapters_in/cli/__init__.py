"""
Adaptador de Entrada — CLI con Click.

Segundo canal de entrada (exigido por la guía Fase 4).
Demuestra evolución: el dominio no cambia, solo se agrega este adaptador.

Comandos disponibles:
  python cli.py registrar   — registrar cliente
  python cli.py login       — autenticar y guardar token
  python cli.py tickets     — listar mis tickets
  python cli.py crear       — crear ticket
  python cli.py alquileres  — listar mis alquileres
  python cli.py dashboard   — dashboard admin
  python cli.py cargar-csv  — carga masiva de clientes desde CSV
"""
from __future__ import annotations
import os, json, csv, sys
from pathlib import Path


TOKEN_FILE = Path.home() / ".tsp_token"


def _guardar_token(token: str) -> None:
    TOKEN_FILE.write_text(token)


def _leer_token() -> str:
    if not TOKEN_FILE.exists():
        print("No hay sesión activa. Ejecuta: python cli.py login")
        sys.exit(1)
    return TOKEN_FILE.read_text().strip()


def crear_cli(contenedor):
    """
    Fábrica del CLI.
    Recibe el Contenedor ya ensamblado — no sabe cómo se construyó.

    Uso en cli.py:
        from techsupportpro.config import Contenedor
        from techsupportpro.infrastructure.adapters_in.cli import crear_cli
        cli = crear_cli(Contenedor.crear())
        cli()
    """
    import click
    from techsupportpro.application.dtos import (
        RegistrarClienteDTO, LoginDTO, CrearTicketDTO,
        CrearAlquilerDTO, ProcesarPagoDTO,
    )

    @click.group()
    def cli():
        """TechSupport Pro — Interfaz de Línea de Comandos"""
        pass

    # ── Registro ────────────────────────────────────────────────────────────
    @cli.command()
    @click.option("--nombre",   prompt="Nombre completo")
    @click.option("--email",    prompt="Email")
    @click.option("--password", prompt="Contraseña", hide_input=True,
                  confirmation_prompt=True)
    @click.option("--empresa",  default="", prompt="Empresa (opcional)")
    def registrar(nombre, email, password, empresa):
        """Registra un nuevo cliente."""
        try:
            r = contenedor.registrar_cliente.ejecutar(
                RegistrarClienteDTO(nombre=nombre, email=email,
                                    password=password, empresa=empresa)
            )
            click.secho(f"\n✅ Registro exitoso!", fg="green")
            click.echo(f"   Código: {r.codigo_cliente}")
            click.echo(f"   Plan:   {r.plan}")
        except Exception as e:
            click.secho(f"\n❌ Error: {e}", fg="red")
            sys.exit(1)

    # ── Login ───────────────────────────────────────────────────────────────
    @cli.command()
    @click.option("--email",    prompt="Email")
    @click.option("--password", prompt="Contraseña", hide_input=True)
    def login(email, password):
        """Inicia sesión y guarda el token localmente."""
        try:
            r = contenedor.login_cliente.ejecutar(LoginDTO(email, password))
            _guardar_token(r.token)
            click.secho(f"\n✅ Bienvenido! Plan: {r.plan}", fg="green")
            click.echo(f"   Token guardado en {TOKEN_FILE}")
        except Exception as e:
            click.secho(f"\n❌ Credenciales inválidas: {e}", fg="red")
            sys.exit(1)

    # ── Mis tickets ─────────────────────────────────────────────────────────
    @cli.command()
    @click.option("--estado", default=None, help="Filtrar por estado (NUEVO, RESUELTO…)")
    def tickets(estado):
        """Lista tus tickets de soporte."""
        try:
            token = _leer_token()
            r = contenedor.mis_tickets.ejecutar(token, estado)
            click.echo(f"\n{'─'*60}")
            click.echo(f"  Tickets: {r.total} total | {r.abiertos} abiertos | {r.resueltos} resueltos")
            click.echo(f"{'─'*60}")
            for t in r.tickets:
                color = "yellow" if t["estado"] in ("NUEVO","ASIGNADO") else \
                        "green"  if t["estado"] == "RESUELTO" else "white"
                click.secho(f"  [{t['numero']}] {t['titulo']}", fg=color)
                click.echo(f"     Estado: {t['estado']} | Tipo: {t['tipo_servicio']}")
            click.echo()
        except Exception as e:
            click.secho(f"❌ {e}", fg="red")

    # ── Crear ticket ─────────────────────────────────────────────────────────
    @cli.command("crear")
    @click.option("--tipo",        prompt="Tipo de servicio",
                  type=click.Choice(["SOPORTE_REMOTO","VISITA_PRESENCIAL",
                                     "REPARACION_PC","REPARACION_IMPRESORA",
                                     "INSTALACION_RED"], case_sensitive=False))
    @click.option("--titulo",      prompt="Título del problema")
    @click.option("--descripcion", prompt="Descripción detallada")
    @click.option("--prioridad",   default="MEDIA",
                  type=click.Choice(["BAJA","MEDIA","ALTA","CRITICA"]))
    def crear_ticket(tipo, titulo, descripcion, prioridad):
        """Crea un nuevo ticket de soporte."""
        try:
            token = _leer_token()
            r = contenedor.crear_ticket.ejecutar(
                token,
                CrearTicketDTO(tipo_servicio=tipo.upper(), titulo=titulo,
                               descripcion=descripcion, prioridad=prioridad.upper())
            )
            click.secho(f"\n✅ Ticket creado: {r.numero}", fg="green")
            click.echo(f"   Estado: {r.estado}")
            click.echo(f"   Costo estimado: ${r.costo_estimado:,.0f} COP")
        except Exception as e:
            click.secho(f"\n❌ Error: {e}", fg="red")

    # ── Mis alquileres ──────────────────────────────────────────────────────
    @cli.command()
    def alquileres():
        """Lista tus alquileres de equipos."""
        try:
            token = _leer_token()
            info = contenedor._tokens.verificar_token(token)
            if not info:
                click.secho("❌ Token inválido", fg="red"); return
            items = contenedor._alquileres.listar_por_cliente(info["usuario_id"])
            click.echo(f"\n  Alquileres: {len(items)}")
            click.echo(f"{'─'*60}")
            for a in items:
                click.echo(f"  {a.equipo_tipo.upper()} — {a.periodo.dias} días")
                click.echo(f"     {a.periodo.inicio.strftime('%Y-%m-%d')} → "
                           f"{a.periodo.fin.strftime('%Y-%m-%d')}")
                click.echo(f"     Total: ${a.costo_total.pesos:,.0f} COP | Estado: {a.estado.value}")
        except Exception as e:
            click.secho(f"❌ {e}", fg="red")

    # ── Dashboard admin ──────────────────────────────────────────────────────
    @cli.command()
    def dashboard():
        """Muestra el dashboard de administración (solo técnicos/admins)."""
        try:
            token = _leer_token()
            r = contenedor.dashboard_admin.ejecutar(token)
            import dataclasses
            d = dataclasses.asdict(r)
            click.echo(f"\n{'═'*60}")
            click.secho("  DASHBOARD TechSupport Pro", fg="cyan", bold=True)
            click.echo(f"{'═'*60}")
            click.echo(f"  Tickets total:     {d['tickets_total']}")
            click.echo(f"  Tickets nuevos:    {d['tickets_nuevos']}")
            click.echo(f"  Tasa resolución:   {d['tasa_resolucion']:.1f}%")
            click.echo(f"  Clientes activos:  {d['clientes_activos']}")
            click.echo(f"  Técnicos activos:  {d['tecnicos_activos']}")
            click.echo(f"  Ingresos (30d):  ${d['ingresos_mes']:,.0f} COP")
            click.echo(f"{'═'*60}\n")
        except Exception as e:
            click.secho(f"❌ {e}", fg="red")

    # ── Carga masiva CSV ─────────────────────────────────────────────────────
    @cli.command("cargar-csv")
    @click.argument("archivo", type=click.Path(exists=True))
    @click.option("--password-default", default="TechPro2026!",
                  help="Contraseña para todos los clientes nuevos")
    def cargar_csv(archivo, password_default):
        """
        Carga masiva de clientes desde un archivo CSV.

        Formato del CSV:
            nombre,email,empresa,ciudad
            Juan Pérez,juan@empresa.com,Empresa SAS,Bogotá

        Segundo canal de entrada exigido por la guía.
        Demuestra evolución: el caso de uso RegistrarCliente no cambió.
        """
        exitosos, fallidos, errores = 0, 0, []
        with open(archivo, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for fila in reader:
                try:
                    contenedor.registrar_cliente.ejecutar(RegistrarClienteDTO(
                        nombre=fila.get("nombre", ""),
                        email=fila.get("email", ""),
                        password=password_default,
                        empresa=fila.get("empresa", ""),
                        ciudad=fila.get("ciudad", "Bogotá"),
                    ))
                    exitosos += 1
                    click.echo(f"  ✅ {fila.get('email','?')}")
                except Exception as e:
                    fallidos += 1
                    errores.append(f"{fila.get('email','?')}: {e}")
                    click.secho(f"  ⚠️  {fila.get('email','?')} — {e}", fg="yellow")

        click.echo(f"\n{'─'*50}")
        click.secho(f"  Registrados: {exitosos} | Fallidos: {fallidos}", fg="green")
        if errores:
            click.echo("\n  Errores detallados:")
            for err in errores:
                click.echo(f"    · {err}")

    return cli
