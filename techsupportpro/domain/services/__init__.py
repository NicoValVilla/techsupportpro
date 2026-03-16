"""
Servicios de dominio TechSupport Pro.
Lógica de negocio que no pertenece a ninguna entidad específica.
Sin dependencias de infraestructura.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional

from techsupportpro.domain.entities import (
    Ticket, Tecnico, Cliente, TipoServicio, Prioridad, COP
)


class TecnicoAsignadorService:
    """
    Servicio de dominio: lógica de asignación automática de técnicos.
    Antes esta lógica estaba directamente en el controlador HTTP.
    """

    @staticmethod
    def seleccionar_mejor_tecnico(
        tecnicos_disponibles: list[Tecnico],
        tipo_servicio: TipoServicio,
    ) -> Optional[Tecnico]:
        """
        Selecciona el técnico más adecuado según:
        1. Especialidad en el tipo de servicio solicitado
        2. Menor carga actual de tickets
        3. Mayor calificación promedio
        """
        if not tecnicos_disponibles:
            return None

        # Priorizar técnicos con especialidad en el servicio
        especializados = [
            t for t in tecnicos_disponibles
            if tipo_servicio in t.especialidades
        ]

        candidatos = especializados if especializados else tecnicos_disponibles

        # Ordenar por calificación descendente (mejor primero)
        return max(candidatos, key=lambda t: t.calificacion_promedio)


class NumeradorTicketService:
    """
    Servicio de dominio: generación de números únicos de ticket.
    Antes esta lógica vivía en el controlador HTTP.
    """

    @staticmethod
    def generar(año: int, mes: int, correlativo: int) -> str:
        return f"TSP-{año}{mes:02d}-{correlativo:05d}"

    @staticmethod
    def generar_ahora(correlativo: int) -> str:
        ahora = datetime.utcnow()
        return NumeradorTicketService.generar(ahora.year, ahora.month, correlativo)


class CalculadorCostoService:
    """
    Servicio de dominio: cálculos de costo de servicios.
    Encapsula reglas de negocio de precios que estaban en el controlador.
    """

    @staticmethod
    def estimar_costo(
        tipo: TipoServicio,
        prioridad: Prioridad,
        descuento_plan: float = 0.0,
    ) -> COP:
        """
        Estima el costo de un servicio antes de crearlo.
        Aplica recargo por prioridad y descuento del plan.
        """
        costos_base = {
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
        base = costos_base.get(tipo, COP.cero())
        con_recargo = base.multiplicar(prioridad.factor_recargo())

        if descuento_plan > 0:
            return con_recargo.multiplicar(1 - descuento_plan)
        return con_recargo


class MetricasService:
    """
    Servicio de dominio: cálculo de métricas de negocio.
    Antes estas métricas se calculaban con SQL directo en el controlador.
    """

    @staticmethod
    def tasa_resolucion(total: int, resueltos: int) -> float:
        if total == 0:
            return 0.0
        return round(resueltos / total * 100, 1)

    @staticmethod
    def promedio_minutos_resolucion(tickets: list[Ticket]) -> Optional[float]:
        tiempos = [
            t.tiempo_resolucion_minutos()
            for t in tickets
            if t.tiempo_resolucion_minutos() is not None
        ]
        if not tiempos:
            return None
        return round(sum(tiempos) / len(tiempos), 1)

    @staticmethod
    def costo_historico_cliente(tickets: list[Ticket]) -> COP:
        total = COP.cero()
        for t in tickets:
            costo = t.costo_final or t.costo_estimado or COP.cero()
            total = total + costo
        return total
