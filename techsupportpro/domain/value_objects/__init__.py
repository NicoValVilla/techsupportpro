"""
Value Objects del dominio TechSupport Pro.
Objetos inmutables que encapsulan validaciones y reglas de formato.
Sin dependencias de infraestructura.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import datetime, date


# ================================================================
# EMAIL
# ================================================================
@dataclass(frozen=True)
class Email:
    """
    Value Object que garantiza un email válido.
    La validación que estaba en el controlador ahora vive aquí.
    """
    valor: str

    def __post_init__(self):
        patron = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        if not self.valor or not re.match(patron, self.valor.strip()):
            raise ValueError(f"Email inválido: '{self.valor}'")
        # normalizar a minúsculas mediante object.__setattr__ (frozen dataclass)
        object.__setattr__(self, 'valor', self.valor.strip().lower())

    def __str__(self) -> str:
        return self.valor

    def dominio(self) -> str:
        return self.valor.split('@')[1]


# ================================================================
# PASSWORD
# ================================================================
@dataclass(frozen=True)
class PasswordPlana:
    """
    Value Object para la contraseña en texto plano antes de hashear.
    Encapsula las reglas de complejidad que estaban en el controlador.
    """
    valor: str

    _MINIMO_CARACTERES = 8

    def __post_init__(self):
        if len(self.valor) < self._MINIMO_CARACTERES:
            raise ValueError(
                f"La contraseña debe tener mínimo {self._MINIMO_CARACTERES} caracteres"
            )
        if not any(c.isupper() for c in self.valor):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not any(c.isdigit() for c in self.valor):
            raise ValueError("La contraseña debe contener al menos un número")

    def __repr__(self) -> str:
        return "PasswordPlana(***)"


@dataclass(frozen=True)
class PasswordHash:
    """
    Value Object que representa un hash almacenable (salt:hash).
    Encapsula el formato interno del hash — nunca expone la lógica de hashing.
    """
    valor: str   # formato "salt:sha256hash"

    def __post_init__(self):
        partes = self.valor.split(':')
        if len(partes) != 2 or not partes[0] or not partes[1]:
            raise ValueError("Formato de hash inválido (esperado: salt:hash)")

    @property
    def salt(self) -> str:
        return self.valor.split(':')[0]

    @property
    def hash(self) -> str:
        return self.valor.split(':')[1]

    def __str__(self) -> str:
        return self.valor


# ================================================================
# COP — MONEDA COLOMBIANA
# ================================================================
@dataclass(frozen=True)
class COP:
    """
    Value Object para valores monetarios en Pesos Colombianos.
    Previene errores de comparación con floats y encapsula formateo.
    """
    centavos: int  # almacenamos en centavos para evitar flotantes

    _MINIMO_PAGO = 500_000   # 5.000 COP en centavos

    def __post_init__(self):
        if self.centavos < 0:
            raise ValueError("Un valor monetario no puede ser negativo")

    @classmethod
    def de_pesos(cls, pesos: float) -> COP:
        """Crea un COP desde pesos (puede ser float como 45000.0)."""
        if pesos < 0:
            raise ValueError("El monto no puede ser negativo")
        return cls(centavos=round(pesos * 100))

    @classmethod
    def cero(cls) -> COP:
        return cls(centavos=0)

    @property
    def pesos(self) -> float:
        return self.centavos / 100

    def mas(self, otro: COP) -> COP:
        return COP(self.centavos + otro.centavos)

    def multiplicar(self, factor: float) -> COP:
        return COP(round(self.centavos * factor))

    def es_cero(self) -> bool:
        return self.centavos == 0

    def __add__(self, otro: COP) -> COP:
        return self.mas(otro)

    def __gt__(self, otro: COP) -> bool:
        return self.centavos > otro.centavos

    def __ge__(self, otro: COP) -> bool:
        return self.centavos >= otro.centavos

    def __str__(self) -> str:
        return f"${self.pesos:,.0f} COP"

    def __repr__(self) -> str:
        return f"COP({self.pesos:,.0f})"


# ================================================================
# PERIODO — RANGO DE FECHAS PARA ALQUILER
# ================================================================
@dataclass(frozen=True)
class Periodo:
    """
    Value Object para períodos de alquiler.
    Encapsula las reglas de fechas que estaban dispersas en el controlador.
    """
    inicio: datetime
    fin: datetime

    _MINIMO_DIAS = 1

    def __post_init__(self):
        if self.inicio >= self.fin:
            raise ValueError("La fecha de fin debe ser posterior a la de inicio")
        if self.dias < self._MINIMO_DIAS:
            raise ValueError(f"El período mínimo es de {self._MINIMO_DIAS} día(s)")

    @classmethod
    def de_strings(cls, inicio_iso: str, fin_iso: str) -> Periodo:
        """Construye un Periodo desde strings ISO 8601."""
        try:
            inicio = datetime.fromisoformat(inicio_iso)
            fin    = datetime.fromisoformat(fin_iso)
        except ValueError as e:
            raise ValueError(f"Formato de fecha inválido. Use ISO 8601 (YYYY-MM-DD): {e}")
        return cls(inicio=inicio, fin=fin)

    @classmethod
    def de_hoy_a(cls, dias: int) -> Periodo:
        from datetime import timedelta
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return cls(inicio=hoy, fin=hoy + timedelta(days=dias))

    @property
    def dias(self) -> int:
        return (self.fin - self.inicio).days

    def __str__(self) -> str:
        return (
            f"{self.inicio.strftime('%Y-%m-%d')} → "
            f"{self.fin.strftime('%Y-%m-%d')} ({self.dias} días)"
        )


# ================================================================
# NOMBRE
# ================================================================
@dataclass(frozen=True)
class NombrePersona:
    """Value Object para nombres — mínimo 2 caracteres, normaliza capitalización."""
    valor: str

    def __post_init__(self):
        limpio = self.valor.strip()
        if len(limpio) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        if not all(c.isalpha() or c in " '-." for c in limpio):
            raise ValueError("El nombre contiene caracteres inválidos")
        object.__setattr__(self, 'valor', limpio.title())

    def __str__(self) -> str:
        return self.valor


# ================================================================
# TELEFONO COLOMBIANO
# ================================================================
@dataclass(frozen=True)
class TelefonoColombia:
    """Value Object para teléfonos colombianos (fijo o celular)."""
    valor: str

    def __post_init__(self):
        limpio = re.sub(r'[\s\-\(\)\+]', '', self.valor)
        # Formatos válidos: 573XXXXXXXXX, 3XXXXXXXXX, 60XXXXXXXX
        if not re.match(r'^(57)?[36]\d{9}$', limpio):
            raise ValueError(
                f"Teléfono colombiano inválido: '{self.valor}'. "
                "Use formato: 3001234567 o +573001234567"
            )
        object.__setattr__(self, 'valor', limpio if limpio.startswith('57') else f'57{limpio}')

    def __str__(self) -> str:
        return f"+{self.valor}"

    @property
    def sin_pais(self) -> str:
        return self.valor[2:] if self.valor.startswith('57') else self.valor
