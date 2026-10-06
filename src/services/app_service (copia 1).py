"""
CAPA 2 - SERVICIOS Y LÓGICA DE NEGOCIO
Célula 2: Casos de uso de Mecha-Arena.

Responsabilidades:
  - Registro y consulta de pilotos.
  - Ensamblaje de mechas.
  - Motor de combate por turnos.
  - Gestión de torneos.
"""

from __future__ import annotations
import random
from typing import List, Optional, Tuple

from src.domain.models import (
    Piloto, Mecha, Componente, ResultadoCombate,
    TipoComponente, RarezaComponente,
)
from src.domain.exceptions import (
    PilotoNoEncontradoError,
    MechaIncompleroError,
    CombateInvalidoError,
    ComponenteNoValidoError,
    NombreInvalidoError,
)
from src.services.data_manager import DataManager


class AppService:
    """
    Fachada de lógica de negocio que conecta la capa de dominio
    con la persistencia y la interfaz de usuario.
    """

    def __init__(self) -> None:
        self._data_manager = DataManager()
        self._pilotos: List[Piloto] = self._data_manager.cargar_pilotos()

    # ─────────────────────────────────────────
    #  GESTIÓN DE PILOTOS
    # ─────────────────────────────────────────

    def registrar_piloto(self, nombre: str) -> Piloto:
        """
        Crea y registra un nuevo piloto.
        Lanza NombreInvalidoError si el nombre ya existe.
        """
        nombre = nombre.strip()
        if self._buscar_piloto(nombre) is not None:
            raise NombreInvalidoError(f"Ya existe un piloto llamado '{nombre}'.")
        piloto = Piloto(nombre)
        self._pilotos.append(piloto)
        self._guardar()
        return piloto

    def obtener_pilotos(self) -> List[Piloto]:
        """Retorna la lista de todos los pilotos registrados."""
        return list(self._pilotos)

    def obtener_piloto(self, nombre: str) -> Piloto:
        """Busca un piloto por nombre. Lanza PilotoNoEncontradoError si no existe."""
        piloto = self._buscar_piloto(nombre)
        if piloto is None:
            raise PilotoNoEncontradoError(nombre)
        return piloto

    def eliminar_piloto(self, nombre: str) -> None:
        """Elimina un piloto del registro."""
        piloto = self.obtener_piloto(nombre)
        self._pilotos.remove(piloto)
        self._guardar()

    # ─────────────────────────────────────────
    #  ENSAMBLAJE DE MECHAS
    # ─────────────────────────────────────────

    def crear_mecha_para_piloto(self, nombre_piloto: str, nombre_mecha: str) -> Mecha:
        """Crea un nuevo Mecha vacío y lo asigna al piloto."""
        piloto = self.obtener_piloto(nombre_piloto)
        mecha = Mecha(nombre_mecha)
        piloto.asignar_mecha(mecha)
        self._guardar()
        return mecha

    def instalar_componente(
        self, nombre_piloto: str, nombre_componente: str
    ) -> Componente:
        """
        Busca el componente en el catálogo y lo instala en el mecha del piloto.
        """
        piloto = self.obtener_piloto(nombre_piloto)
        if piloto.mecha is None:
            raise MechaIncompleroError("El piloto no tiene un Mecha asignado.")

        catalogo = self._data_manager.obtener_catalogo()
        componente = next(
            (c for c in catalogo if c.nombre.lower() == nombre_componente.lower()),
            None,
        )
        if componente is None:
            raise ComponenteNoValidoError(
                f"Componente '{nombre_componente}' no existe en el catálogo."
            )

        piloto.mecha.instalar_componente(componente)
        self._guardar()
        return componente

    def remover_componente(
        self, nombre_piloto: str, tipo: TipoComponente
    ) -> Optional[Componente]:
        """Remueve un componente del mecha del piloto."""
        piloto = self.obtener_piloto(nombre_piloto)
        if piloto.mecha is None:
            raise MechaIncompleroError("El piloto no tiene un Mecha asignado.")
        removido = piloto.mecha.remover_componente(tipo)
        self._guardar()
        return removido

    def obtener_catalogo(self) -> List[Componente]:
        """Devuelve el catálogo completo de componentes."""
        return self._data_manager.obtener_catalogo()

    # ─────────────────────────────────────────
    #  MOTOR DE COMBATE
    # ─────────────────────────────────────────

    def iniciar_combate(
        self, nombre_piloto_1: str, nombre_piloto_2: str
    ) -> ResultadoCombate:
        """
        Ejecuta un combate por turnos entre dos pilotos.

        Reglas:
          - Cada ronda: el atacante inflige ataque_total + variación aleatoria.
          - La defensa del receptor reduce el daño (lógica en Mecha.recibir_dano).
          - La velocidad determina quién ataca primero en cada ronda.
          - El combate termina cuando un mecha llega a 0 HP o pasan 20 rondas.
        """
        p1 = self.obtener_piloto(nombre_piloto_1)
        p2 = self.obtener_piloto(nombre_piloto_2)

        self._validar_para_combate(p1)
        self._validar_para_combate(p2)

        if nombre_piloto_1 == nombre_piloto_2:
            raise CombateInvalidoError("Un piloto no puede combatir contra sí mismo.")

        m1: Mecha = p1.mecha  # type: ignore[assignment]
        m2: Mecha = p2.mecha  # type: ignore[assignment]

        # Restaurar HP antes del combate
        m1.restaurar_hp()
        m2.restaurar_hp()

        log: List[str] = []
        ronda = 0
        MAX_RONDAS = 20

        log.append(f"⚔️  COMBATE: {p1.nombre} [{m1.nombre}] VS {p2.nombre} [{m2.nombre}]")
        log.append(f"   ATK {m1.ataque_total} | DEF {m1.defensa_total} | VEL {m1.velocidad}  vs  "
                   f"ATK {m2.ataque_total} | DEF {m2.defensa_total} | VEL {m2.velocidad}")
        log.append("─" * 60)

        while m1.esta_vivo and m2.esta_vivo and ronda < MAX_RONDAS:
            ronda += 1
            log.append(f"\n  Ronda {ronda}:")

            # Determinar orden por velocidad (empate: aleatorio)
            if m1.velocidad > m2.velocidad or (
                m1.velocidad == m2.velocidad and random.random() > 0.5
            ):
                atacante, defensor, pa, pd = m1, m2, p1, p2
            else:
                atacante, defensor, pa, pd = m2, m1, p2, p1

            # Turno 1: primer atacante
            dano_real = self._calcular_y_aplicar_dano(atacante, defensor)
            log.append(
                f"    {pa.nombre} ataca → {dano_real} daño | "
                f"HP {pd.nombre}: {defensor.hp_actual}/{defensor.hp_max}"
            )

            if not defensor.esta_vivo:
                break

            # Turno 2: contraataque
            dano_real2 = self._calcular_y_aplicar_dano(defensor, atacante)
            log.append(
                f"    {pd.nombre} contraataca → {dano_real2} daño | "
                f"HP {pa.nombre}: {atacante.hp_actual}/{atacante.hp_max}"
            )

        # Determinar ganador
        if m1.esta_vivo and not m2.esta_vivo:
            ganador, perdedor = p1, p2
        elif m2.esta_vivo and not m1.esta_vivo:
            ganador, perdedor = p2, p1
        else:
            # Empate por rondas: gana el de mayor HP actual
            ganador, perdedor = (p1, p2) if m1.hp_actual >= m2.hp_actual else (p2, p1)
            log.append("\n  ⏱️  Límite de rondas alcanzado — gana quien tenga más HP.")

        log.append(f"\n🏆 ¡{ganador.nombre} gana el combate en {ronda} ronda(s)!")

        ganador.registrar_victoria()
        perdedor.registrar_derrota()

        resultado = ResultadoCombate(
            ganador=ganador.nombre,
            perdedor=perdedor.nombre,
            rondas=ronda,
            log_batalla=log,
        )

        self._data_manager.guardar_resultado(resultado)
        self._guardar()
        return resultado

    # ─────────────────────────────────────────
    #  TORNEO (Round-Robin)
    # ─────────────────────────────────────────

    def iniciar_torneo(self, nombres_pilotos: List[str]) -> List[ResultadoCombate]:
        """
        Ejecuta un torneo round-robin entre los pilotos indicados.
        Cada par combate una vez.
        """
        if len(nombres_pilotos) < 2:
            raise CombateInvalidoError("Se necesitan al menos 2 pilotos para un torneo.")

        resultados: List[ResultadoCombate] = []
        pilotos = nombres_pilotos[:]

        for i in range(len(pilotos)):
            for j in range(i + 1, len(pilotos)):
                resultado = self.iniciar_combate(pilotos[i], pilotos[j])
                resultados.append(resultado)

        return resultados

    def obtener_clasificacion(self) -> List[Tuple[str, int, int, float]]:
        """
        Retorna la clasificación de pilotos ordenada por victorias.
        Cada elemento: (nombre, victorias, derrotas, ratio)
        """
        clasificacion = [
            (p.nombre, p.victorias, p.derrotas, p.ratio_victoria)
            for p in self._pilotos
        ]
        return sorted(clasificacion, key=lambda x: (-x[1], x[3]))

    # ─────────────────────────────────────────
    #  HISTORIAL
    # ─────────────────────────────────────────

    def obtener_historial(self) -> List[ResultadoCombate]:
        return self._data_manager.cargar_historial()

    # ─────────────────────────────────────────
    #  MÉTODOS PRIVADOS
    # ─────────────────────────────────────────

    def _buscar_piloto(self, nombre: str) -> Optional[Piloto]:
        nombre_lower = nombre.lower()
        return next(
            (p for p in self._pilotos if p.nombre.lower() == nombre_lower), None
        )

    def _validar_para_combate(self, piloto: Piloto) -> None:
        if piloto.mecha is None:
            raise MechaIncompleroError(f"{piloto.nombre} no tiene Mecha asignado.")
        if not piloto.mecha.esta_listo_para_combate():
            raise MechaIncompleroError(
                f"El Mecha de {piloto.nombre} necesita al menos Torso y Arma."
            )

    @staticmethod
    def _calcular_y_aplicar_dano(atacante: Mecha, defensor: Mecha) -> int:
        """Calcula el daño con variación aleatoria ±20% y lo aplica al defensor."""
        base = atacante.ataque_total
        variacion = random.uniform(0.80, 1.20)
        dano_bruto = int(base * variacion)
        return defensor.recibir_dano(dano_bruto)

    def _guardar(self) -> None:
        self._data_manager.guardar_pilotos(self._pilotos)
