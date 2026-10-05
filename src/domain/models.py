"""
CAPA 1 - DOMINIO POO
Célula 1: Modelos principales del dominio Mecha-Arena.

Contiene las clases base que representan las entidades del simulador:
  - Componente (pieza de un mecha)
  - Mecha       (robot ensamblado por el usuario)
  - Piloto      (usuario que pilota el mecha)
  - ResultadoCombate (resultado de una batalla)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from src.domain.exceptions import (
    ComponenteNoValidoError,
    PuntosDeVidaInvalidosError,
    NombreInvalidoError,
    MechaIncompleroError,
)


# ─────────────────────────────────────────────
#  ENUMERACIONES
# ─────────────────────────────────────────────

class TipoComponente(Enum):
    """Categorías de piezas que se pueden instalar en un mecha."""
    CABEZA = "Cabeza"
    TORSO = "Torso"
    BRAZO_IZQ = "Brazo Izquierdo"
    BRAZO_DER = "Brazo Derecho"
    PIERNAS = "Piernas"
    ARMA = "Arma"


class RarezaComponente(Enum):
    """Rareza de cada componente (afecta estadísticas base)."""
    COMUN = "Común"
    RARO = "Raro"
    EPICO = "Épico"
    LEGENDARIO = "Legendario"


# ─────────────────────────────────────────────
#  ENTIDAD: Componente
# ─────────────────────────────────────────────

class Componente:
    """
    Representa una pieza individual que forma parte de un Mecha.

    Atributos encapsulados:
        _nombre      -- Nombre descriptivo de la pieza.
        _tipo        -- Categoría (TipoComponente).
        _rareza      -- Rareza (RarezaComponente).
        _bonus_ataque -- Puntos de ataque que aporta.
        _bonus_defensa-- Puntos de defensa que aporta.
        _peso        -- Peso de la pieza (afecta velocidad).
    """

    # Multiplicadores de rareza sobre las estadísticas base
    _MULT_RAREZA: dict = {
        RarezaComponente.COMUN:      1.0,
        RarezaComponente.RARO:       1.25,
        RarezaComponente.EPICO:      1.60,
        RarezaComponente.LEGENDARIO: 2.00,
    }

    def __init__(
        self,
        nombre: str,
        tipo: TipoComponente,
        rareza: RarezaComponente,
        bonus_ataque: int,
        bonus_defensa: int,
        peso: float,
    ) -> None:
        self.nombre = nombre          # usa setter con validación
        self.tipo = tipo
        self.rareza = rareza
        self._bonus_ataque = bonus_ataque
        self._bonus_defensa = bonus_defensa
        self._peso = peso

    # ── Propiedades ──────────────────────────

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        if not valor or not valor.strip():
            raise NombreInvalidoError("El nombre del componente no puede estar vacío.")
        self._nombre = valor.strip()

    @property
    def tipo(self) -> TipoComponente:
        return self._tipo

    @tipo.setter
    def tipo(self, valor: TipoComponente) -> None:
        if not isinstance(valor, TipoComponente):
            raise ComponenteNoValidoError(f"Tipo de componente inválido: {valor}")
        self._tipo = valor

    @property
    def rareza(self) -> RarezaComponente:
        return self._rareza

    @rareza.setter
    def rareza(self, valor: RarezaComponente) -> None:
        if not isinstance(valor, RarezaComponente):
            raise ComponenteNoValidoError(f"Rareza inválida: {valor}")
        self._rareza = valor

    @property
    def bonus_ataque(self) -> int:
        """Bonus de ataque final aplicando multiplicador de rareza."""
        mult = self._MULT_RAREZA[self._rareza]
        return int(self._bonus_ataque * mult)

    @property
    def bonus_defensa(self) -> int:
        """Bonus de defensa final aplicando multiplicador de rareza."""
        mult = self._MULT_RAREZA[self._rareza]
        return int(self._bonus_defensa * mult)

    @property
    def peso(self) -> float:
        return self._peso

    # ── Representación ───────────────────────

    def __repr__(self) -> str:
        return (
            f"Componente({self._nombre!r}, tipo={self._tipo.value}, "
            f"rareza={self._rareza.value}, atk={self.bonus_ataque}, "
            f"def={self.bonus_defensa}, peso={self._peso}kg)"
        )

    def to_dict(self) -> dict:
        """Serializa el componente a diccionario (para persistencia JSON)."""
        return {
            "nombre": self._nombre,
            "tipo": self._tipo.name,
            "rareza": self._rareza.name,
            "bonus_ataque": self._bonus_ataque,
            "bonus_defensa": self._bonus_defensa,
            "peso": self._peso,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Componente":
        """Deserializa un diccionario a instancia Componente."""
        return cls(
            nombre=data["nombre"],
            tipo=TipoComponente[data["tipo"]],
            rareza=RarezaComponente[data["rareza"]],
            bonus_ataque=data["bonus_ataque"],
            bonus_defensa=data["bonus_defensa"],
            peso=data["peso"],
        )


# ─────────────────────────────────────────────
#  ENTIDAD: Mecha
# ─────────────────────────────────────────────

class Mecha:
    """
    Robot táctico ensamblado con componentes por el piloto.

    Reglas de dominio:
        - Solo un componente por TipoComponente (excepto ARMA: hasta 2).
        - Necesita al menos TORSO + ARMA para considerarse 'listo para combate'.
        - Los puntos de vida (hp) deben ser > 0.
    """

    HP_BASE = 100
    VELOCIDAD_BASE = 50

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre                       # usa setter
        self._hp_max: int = self.HP_BASE
        self._hp_actual: int = self.HP_BASE
        self._componentes: List[Componente] = []

    # ── Propiedades ──────────────────────────

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        if not valor or not valor.strip():
            raise NombreInvalidoError("El nombre del Mecha no puede estar vacío.")
        self._nombre = valor.strip()

    @property
    def hp_actual(self) -> int:
        return self._hp_actual

    @property
    def hp_max(self) -> int:
        return self._hp_max

    @property
    def esta_vivo(self) -> bool:
        return self._hp_actual > 0

    @property
    def componentes(self) -> List[Componente]:
        return list(self._componentes)

    # ── Estadísticas calculadas ──────────────

    @property
    def ataque_total(self) -> int:
        """Suma de bonuses de ataque de todos los componentes."""
        return sum(c.bonus_ataque for c in self._componentes)

    @property
    def defensa_total(self) -> int:
        """Suma de bonuses de defensa de todos los componentes."""
        return sum(c.bonus_defensa for c in self._componentes)

    @property
    def velocidad(self) -> int:
        """Velocidad base reducida por el peso total de los componentes."""
        peso_total = sum(c.peso for c in self._componentes)
        penalizacion = int(peso_total * 0.5)
        return max(1, self.VELOCIDAD_BASE - penalizacion)

    @property
    def poder_total(self) -> int:
        """Métrica de poder general usada en torneos."""
        return self.ataque_total + self.defensa_total + self.velocidad

    # ── Gestión de componentes ───────────────

    def instalar_componente(self, componente: Componente) -> None:
        """
        Instala un componente en el mecha.
        Regla: máximo 2 armas, 1 por cada otro tipo.
        """
        if not isinstance(componente, Componente):
            raise ComponenteNoValidoError("Solo se pueden instalar instancias de Componente.")

        tipo = componente.tipo
        existentes = [c for c in self._componentes if c.tipo == tipo]

        if tipo == TipoComponente.ARMA and len(existentes) >= 2:
            raise ComponenteNoValidoError("Un mecha solo puede llevar hasta 2 armas.")
        elif tipo != TipoComponente.ARMA and len(existentes) >= 1:
            raise ComponenteNoValidoError(
                f"Ya existe un componente de tipo '{tipo.value}'. Retíralo antes de instalar otro."
            )

        self._componentes.append(componente)
        # Actualizar HP máximo: cada componente de torso suma bonus de defensa al HP
        if tipo == TipoComponente.TORSO:
            self._hp_max = self.HP_BASE + componente.bonus_defensa
            self._hp_actual = self._hp_max

    def remover_componente(self, tipo: TipoComponente) -> Optional[Componente]:
        """Remueve el primer componente del tipo indicado y lo retorna."""
        for i, c in enumerate(self._componentes):
            if c.tipo == tipo:
                return self._componentes.pop(i)
        return None

    def esta_listo_para_combate(self) -> bool:
        """Verifica que el mecha tenga al menos Torso y un Arma."""
        tipos = {c.tipo for c in self._componentes}
        return TipoComponente.TORSO in tipos and TipoComponente.ARMA in tipos

    def recibir_dano(self, cantidad: int) -> int:
        """
        Aplica daño descontando la defensa.
        Retorna el daño real recibido.
        """
        dano_reducido = max(1, cantidad - self.defensa_total)
        self._hp_actual = max(0, self._hp_actual - dano_reducido)
        return dano_reducido

    def restaurar_hp(self) -> None:
        """Restaura el HP al máximo (entre combates)."""
        self._hp_actual = self._hp_max

    # ── Representación ───────────────────────

    def __repr__(self) -> str:
        return (
            f"Mecha({self._nombre!r}, HP={self._hp_actual}/{self._hp_max}, "
            f"ATK={self.ataque_total}, DEF={self.defensa_total}, "
            f"VEL={self.velocidad}, Piezas={len(self._componentes)})"
        )

    def to_dict(self) -> dict:
        return {
            "nombre": self._nombre,
            "componentes": [c.to_dict() for c in self._componentes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Mecha":
        mecha = cls(nombre=data["nombre"])
        for cd in data.get("componentes", []):
            mecha.instalar_componente(Componente.from_dict(cd))
        return mecha


# ─────────────────────────────────────────────
#  ENTIDAD: Piloto
# ─────────────────────────────────────────────

class Piloto:
    """
    Usuario que pilota un mecha en la arena.

    Atributos:
        _nombre        -- Nombre del piloto (único).
        _mecha         -- Mecha actualmente asignado (puede ser None).
        _victorias     -- Contador de victorias en torneos.
        _derrotas      -- Contador de derrotas en torneos.
    """

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self._mecha: Optional[Mecha] = None
        self._victorias: int = 0
        self._derrotas: int = 0

    # ── Propiedades ──────────────────────────

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        if not valor or not valor.strip():
            raise NombreInvalidoError("El nombre del piloto no puede estar vacío.")
        self._nombre = valor.strip()

    @property
    def mecha(self) -> Optional[Mecha]:
        return self._mecha

    @property
    def victorias(self) -> int:
        return self._victorias

    @property
    def derrotas(self) -> int:
        return self._derrotas

    @property
    def ratio_victoria(self) -> float:
        total = self._victorias + self._derrotas
        return round(self._victorias / total, 2) if total > 0 else 0.0

    # ── Métodos de dominio ───────────────────

    def asignar_mecha(self, mecha: Mecha) -> None:
        if not isinstance(mecha, Mecha):
            raise ComponenteNoValidoError("Solo se puede asignar un objeto Mecha al piloto.")
        self._mecha = mecha

    def registrar_victoria(self) -> None:
        self._victorias += 1

    def registrar_derrota(self) -> None:
        self._derrotas += 1

    def __repr__(self) -> str:
        mecha_info = self._mecha.nombre if self._mecha else "Sin Mecha"
        return (
            f"Piloto({self._nombre!r}, Mecha={mecha_info}, "
            f"V={self._victorias}, D={self._derrotas})"
        )

    def to_dict(self) -> dict:
        return {
            "nombre": self._nombre,
            "victorias": self._victorias,
            "derrotas": self._derrotas,
            "mecha": self._mecha.to_dict() if self._mecha else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Piloto":
        piloto = cls(nombre=data["nombre"])
        piloto._victorias = data.get("victorias", 0)
        piloto._derrotas = data.get("derrotas", 0)
        if data.get("mecha"):
            piloto._mecha = Mecha.from_dict(data["mecha"])
        return piloto


# ─────────────────────────────────────────────
#  VALUE OBJECT: ResultadoCombate
# ─────────────────────────────────────────────

@dataclass
class ResultadoCombate:
    """
    Registro inmutable del resultado de un combate entre dos mechas.
    """
    ganador: str
    perdedor: str
    rondas: int
    log_batalla: List[str] = field(default_factory=list)

    def resumen(self) -> str:
        return (
            f"🏆 Ganador: {self.ganador} | "
            f"❌ Perdedor: {self.perdedor} | "
            f"Rondas: {self.rondas}"
        )
