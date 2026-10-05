"""
TESTS UNITARIOS - Capa Dominio
Pruebas para: Componente, Mecha, Piloto, Excepciones.

Ejecutar con:  python -m pytest tests/test_domain.py -v
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from src.domain.models import (
    Componente, Mecha, Piloto, ResultadoCombate,
    TipoComponente, RarezaComponente,
)
from src.domain.exceptions import (
    ComponenteNoValidoError,
    NombreInvalidoError,
    MechaIncompleroError,
)


# ─────────────────────────────────────────────
#  FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def componente_torso():
    return Componente(
        nombre="Torso Test",
        tipo=TipoComponente.TORSO,
        rareza=RarezaComponente.COMUN,
        bonus_ataque=2,
        bonus_defensa=10,
        peso=20.0,
    )

@pytest.fixture
def componente_arma():
    return Componente(
        nombre="Cañón Test",
        tipo=TipoComponente.ARMA,
        rareza=RarezaComponente.RARO,
        bonus_ataque=20,
        bonus_defensa=0,
        peso=8.0,
    )

@pytest.fixture
def mecha_base():
    return Mecha("IronBot")

@pytest.fixture
def piloto_base():
    return Piloto("Alice")


# ─────────────────────────────────────────────
#  TESTS: Componente
# ─────────────────────────────────────────────

class TestComponente:

    def test_nombre_valido(self):
        c = Componente("Visor", TipoComponente.CABEZA, RarezaComponente.COMUN, 5, 3, 8.0)
        assert c.nombre == "Visor"

    def test_nombre_vacio_lanza_excepcion(self):
        with pytest.raises(NombreInvalidoError):
            Componente("", TipoComponente.CABEZA, RarezaComponente.COMUN, 5, 3, 8.0)

    def test_rareza_multiplica_bonus(self):
        c_comun = Componente("A", TipoComponente.ARMA, RarezaComponente.COMUN, 10, 0, 5.0)
        c_leg   = Componente("B", TipoComponente.ARMA, RarezaComponente.LEGENDARIO, 10, 0, 5.0)
        assert c_leg.bonus_ataque == int(10 * 2.0)
        assert c_comun.bonus_ataque == int(10 * 1.0)

    def test_serializacion_roundtrip(self, componente_torso):
        d = componente_torso.to_dict()
        restaurado = Componente.from_dict(d)
        assert restaurado.nombre == componente_torso.nombre
        assert restaurado.tipo == componente_torso.tipo
        assert restaurado.rareza == componente_torso.rareza

    def test_tipo_invalido_lanza_excepcion(self):
        with pytest.raises(ComponenteNoValidoError):
            c = Componente("X", TipoComponente.ARMA, RarezaComponente.COMUN, 5, 0, 2.0)
            c.tipo = "INVALIDO"  # type: ignore


# ─────────────────────────────────────────────
#  TESTS: Mecha
# ─────────────────────────────────────────────

class TestMecha:

    def test_mecha_vacio_no_listo_para_combate(self, mecha_base):
        assert not mecha_base.esta_listo_para_combate()

    def test_instalar_torso_y_arma_listo(
        self, mecha_base, componente_torso, componente_arma
    ):
        mecha_base.instalar_componente(componente_torso)
        mecha_base.instalar_componente(componente_arma)
        assert mecha_base.esta_listo_para_combate()

    def test_no_duplicar_torso(self, mecha_base, componente_torso):
        mecha_base.instalar_componente(componente_torso)
        torso2 = Componente(
            "Otro Torso", TipoComponente.TORSO, RarezaComponente.COMUN, 2, 10, 20.0
        )
        with pytest.raises(ComponenteNoValidoError):
            mecha_base.instalar_componente(torso2)

    def test_maximo_dos_armas(self, mecha_base):
        for nombre in ["Arma1", "Arma2"]:
            mecha_base.instalar_componente(
                Componente(nombre, TipoComponente.ARMA, RarezaComponente.COMUN, 10, 0, 5.0)
            )
        with pytest.raises(ComponenteNoValidoError):
            mecha_base.instalar_componente(
                Componente("Arma3", TipoComponente.ARMA, RarezaComponente.COMUN, 10, 0, 5.0)
            )

    def test_ataque_total_suma_componentes(
        self, mecha_base, componente_torso, componente_arma
    ):
        mecha_base.instalar_componente(componente_torso)
        mecha_base.instalar_componente(componente_arma)
        assert mecha_base.ataque_total == componente_torso.bonus_ataque + componente_arma.bonus_ataque

    def test_recibir_dano_reduce_hp(self, mecha_base, componente_torso):
        mecha_base.instalar_componente(componente_torso)
        hp_antes = mecha_base.hp_actual
        mecha_base.recibir_dano(30)
        assert mecha_base.hp_actual < hp_antes

    def test_restaurar_hp(self, mecha_base, componente_torso):
        mecha_base.instalar_componente(componente_torso)
        mecha_base.recibir_dano(50)
        mecha_base.restaurar_hp()
        assert mecha_base.hp_actual == mecha_base.hp_max

    def test_mecha_muere_cuando_hp_llega_a_cero(self, mecha_base):
        mecha_base.recibir_dano(99999)
        assert not mecha_base.esta_vivo

    def test_serializacion_roundtrip(self, mecha_base, componente_torso, componente_arma):
        mecha_base.instalar_componente(componente_torso)
        mecha_base.instalar_componente(componente_arma)
        d = mecha_base.to_dict()
        restaurado = Mecha.from_dict(d)
        assert restaurado.nombre == mecha_base.nombre
        assert len(restaurado.componentes) == 2


# ─────────────────────────────────────────────
#  TESTS: Piloto
# ─────────────────────────────────────────────

class TestPiloto:

    def test_piloto_creado_sin_mecha(self, piloto_base):
        assert piloto_base.mecha is None

    def test_asignar_mecha(self, piloto_base, mecha_base):
        piloto_base.asignar_mecha(mecha_base)
        assert piloto_base.mecha is mecha_base

    def test_nombre_vacio_lanza_excepcion(self):
        with pytest.raises(NombreInvalidoError):
            Piloto("   ")

    def test_victorias_y_derrotas(self, piloto_base):
        piloto_base.registrar_victoria()
        piloto_base.registrar_victoria()
        piloto_base.registrar_derrota()
        assert piloto_base.victorias == 2
        assert piloto_base.derrotas == 1
        assert piloto_base.ratio_victoria == round(2 / 3, 2)

    def test_ratio_sin_combates(self, piloto_base):
        assert piloto_base.ratio_victoria == 0.0

    def test_serializacion_roundtrip(self, piloto_base, mecha_base, componente_torso):
        mecha_base.instalar_componente(componente_torso)
        piloto_base.asignar_mecha(mecha_base)
        piloto_base.registrar_victoria()
        d = piloto_base.to_dict()
        restaurado = Piloto.from_dict(d)
        assert restaurado.nombre == piloto_base.nombre
        assert restaurado.victorias == 1
        assert restaurado.mecha is not None


# ─────────────────────────────────────────────
#  TESTS: ResultadoCombate
# ─────────────────────────────────────────────

class TestResultadoCombate:

    def test_resumen_contiene_ganador_y_perdedor(self):
        r = ResultadoCombate(ganador="Alice", perdedor="Bob", rondas=5)
        resumen = r.resumen()
        assert "Alice" in resumen
        assert "Bob" in resumen
        assert "5" in resumen

    def test_log_por_defecto_vacio(self):
        r = ResultadoCombate(ganador="X", perdedor="Y", rondas=1)
        assert r.log_batalla == []
