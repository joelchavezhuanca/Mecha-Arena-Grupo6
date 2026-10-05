"""
CAPA 2 - SERVICIOS Y PERSISTENCIA
Célula 2: Gestión de datos (JSON).

Responsabilidades:
  - Guardar y cargar pilotos en un archivo JSON.
  - Registrar el historial de combates.
  - Proveer el catálogo de componentes disponibles.
"""

from __future__ import annotations
import json
import os
from typing import List, Optional, Dict, Any

from src.domain.models import Piloto, Componente, TipoComponente, RarezaComponente, ResultadoCombate
from src.domain.exceptions import ArchivoCorruptoError, PilotoNoEncontradoError


# ─────────────────────────────────────────────
#  CATÁLOGO DE COMPONENTES PRE-DEFINIDOS
# ─────────────────────────────────────────────

CATALOGO_COMPONENTES: List[Dict[str, Any]] = [
    # CABEZAS
    {"nombre": "Visor Básico",          "tipo": "CABEZA",    "rareza": "COMUN",      "bonus_ataque": 5,  "bonus_defensa": 3,  "peso": 8.0},
    {"nombre": "Casco de Reconocimiento","tipo": "CABEZA",   "rareza": "RARO",       "bonus_ataque": 8,  "bonus_defensa": 5,  "peso": 9.0},
    {"nombre": "Visor Omega",           "tipo": "CABEZA",    "rareza": "EPICO",      "bonus_ataque": 12, "bonus_defensa": 8,  "peso": 10.0},
    {"nombre": "Corona Dragón",         "tipo": "CABEZA",    "rareza": "LEGENDARIO", "bonus_ataque": 20, "bonus_defensa": 15, "peso": 12.0},
    # TORSOS
    {"nombre": "Coraza Ligera",         "tipo": "TORSO",     "rareza": "COMUN",      "bonus_ataque": 2,  "bonus_defensa": 10, "peso": 20.0},
    {"nombre": "Torso Blindado",        "tipo": "TORSO",     "rareza": "RARO",       "bonus_ataque": 4,  "bonus_defensa": 18, "peso": 25.0},
    {"nombre": "Núcleo de Plasma",      "tipo": "TORSO",     "rareza": "EPICO",      "bonus_ataque": 8,  "bonus_defensa": 25, "peso": 28.0},
    {"nombre": "Reactor Celestial",     "tipo": "TORSO",     "rareza": "LEGENDARIO", "bonus_ataque": 15, "bonus_defensa": 40, "peso": 30.0},
    # BRAZOS IZQUIERDOS
    {"nombre": "Brazo Estándar Izq",    "tipo": "BRAZO_IZQ", "rareza": "COMUN",      "bonus_ataque": 6,  "bonus_defensa": 2,  "peso": 10.0},
    {"nombre": "Brazo Reforzado Izq",   "tipo": "BRAZO_IZQ", "rareza": "RARO",       "bonus_ataque": 10, "bonus_defensa": 4,  "peso": 12.0},
    {"nombre": "Garra Mecánica Izq",    "tipo": "BRAZO_IZQ", "rareza": "EPICO",      "bonus_ataque": 16, "bonus_defensa": 6,  "peso": 14.0},
    # BRAZOS DERECHOS
    {"nombre": "Brazo Estándar Der",    "tipo": "BRAZO_DER", "rareza": "COMUN",      "bonus_ataque": 6,  "bonus_defensa": 2,  "peso": 10.0},
    {"nombre": "Brazo Reforzado Der",   "tipo": "BRAZO_DER", "rareza": "RARO",       "bonus_ataque": 10, "bonus_defensa": 4,  "peso": 12.0},
    {"nombre": "Lanzador de Cohetes",   "tipo": "BRAZO_DER", "rareza": "EPICO",      "bonus_ataque": 20, "bonus_defensa": 3,  "peso": 15.0},
    # PIERNAS
    {"nombre": "Piernas Básicas",       "tipo": "PIERNAS",   "rareza": "COMUN",      "bonus_ataque": 2,  "bonus_defensa": 4,  "peso": 15.0},
    {"nombre": "Piernas Turbo",         "tipo": "PIERNAS",   "rareza": "RARO",       "bonus_ataque": 3,  "bonus_defensa": 6,  "peso": 14.0},
    {"nombre": "Propulsores Cuánticos", "tipo": "PIERNAS",   "rareza": "LEGENDARIO", "bonus_ataque": 5,  "bonus_defensa": 10, "peso": 12.0},
    # ARMAS
    {"nombre": "Cañón Básico",          "tipo": "ARMA",      "rareza": "COMUN",      "bonus_ataque": 12, "bonus_defensa": 0,  "peso": 8.0},
    {"nombre": "Espada de Plasma",      "tipo": "ARMA",      "rareza": "RARO",       "bonus_ataque": 20, "bonus_defensa": 2,  "peso": 6.0},
    {"nombre": "Rifle de Antimateria",  "tipo": "ARMA",      "rareza": "EPICO",      "bonus_ataque": 30, "bonus_defensa": 1,  "peso": 9.0},
    {"nombre": "Hacha del Apocalipsis", "tipo": "ARMA",      "rareza": "LEGENDARIO", "bonus_ataque": 50, "bonus_defensa": 5,  "peso": 12.0},
]


class DataManager:
    """
    Gestiona la persistencia de datos en formato JSON.

    Archivos gestionados:
        - pilotos.json     : Lista de pilotos y sus mechas.
        - historial.json   : Historial de combates.
    """

    RUTA_PILOTOS: str = "pilotos.json"
    RUTA_HISTORIAL: str = "historial.json"

    # ── Pilotos ──────────────────────────────

    def guardar_pilotos(self, pilotos: List[Piloto]) -> None:
        """Serializa y guarda la lista de pilotos en JSON."""
        datos = [p.to_dict() for p in pilotos]
        try:
            with open(self.RUTA_PILOTOS, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise ArchivoCorruptoError(self.RUTA_PILOTOS) from e

    def cargar_pilotos(self) -> List[Piloto]:
        """Carga la lista de pilotos desde JSON. Retorna lista vacía si no existe."""
        if not os.path.exists(self.RUTA_PILOTOS):
            return []
        try:
            with open(self.RUTA_PILOTOS, "r", encoding="utf-8") as f:
                datos = json.load(f)
            return [Piloto.from_dict(d) for d in datos]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ArchivoCorruptoError(self.RUTA_PILOTOS) from e

    # ── Historial de combates ─────────────────

    def guardar_resultado(self, resultado: ResultadoCombate) -> None:
        """Agrega un resultado de combate al historial JSON."""
        historial = self._cargar_historial_raw()
        historial.append({
            "ganador":    resultado.ganador,
            "perdedor":   resultado.perdedor,
            "rondas":     resultado.rondas,
            "log":        resultado.log_batalla,
        })
        try:
            with open(self.RUTA_HISTORIAL, "w", encoding="utf-8") as f:
                json.dump(historial, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise ArchivoCorruptoError(self.RUTA_HISTORIAL) from e

    def cargar_historial(self) -> List[ResultadoCombate]:
        """Carga el historial de combates desde JSON."""
        datos = self._cargar_historial_raw()
        return [
            ResultadoCombate(
                ganador=d["ganador"],
                perdedor=d["perdedor"],
                rondas=d["rondas"],
                log_batalla=d.get("log", []),
            )
            for d in datos
        ]

    def _cargar_historial_raw(self) -> List[dict]:
        if not os.path.exists(self.RUTA_HISTORIAL):
            return []
        try:
            with open(self.RUTA_HISTORIAL, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return []

    # ── Catálogo de componentes ───────────────

    def obtener_catalogo(self) -> List[Componente]:
        """Devuelve la lista de componentes disponibles en el juego."""
        return [Componente.from_dict(d) for d in CATALOGO_COMPONENTES]
