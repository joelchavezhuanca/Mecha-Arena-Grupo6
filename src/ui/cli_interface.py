"""
CAPA 3 - INTERFAZ / CLI
Célula 3: Menú de consola interactivo de Mecha-Arena.

Conecta AppService con el usuario a través de un menú por números.
"""

from __future__ import annotations
import os
import sys
from typing import Optional

from src.domain.models import TipoComponente, RarezaComponente
from src.domain.exceptions import MechaArenaError
from src.services.app_service import AppService


# ─────────────────────────────────────────────
#  UTILIDADES DE CONSOLA
# ─────────────────────────────────────────────

ROJO    = "\033[91m"
VERDE   = "\033[92m"
AMARILLO= "\033[93m"
CYAN    = "\033[96m"
BOLD    = "\033[1m"
RESET   = "\033[0m"

BANNER = f"""
{BOLD}{CYAN}
 ███╗   ███╗███████╗ ██████╗██╗  ██╗ █████╗       █████╗ ██████╗ ███████╗███╗   ██╗ █████╗
 ████╗ ████║██╔════╝██╔════╝██║  ██║██╔══██╗     ██╔══██╗██╔══██╗██╔════╝████╗  ██║██╔══██╗
 ██╔████╔██║█████╗  ██║     ███████║███████║     ███████║██████╔╝█████╗  ██╔██╗ ██║███████║
 ██║╚██╔╝██║██╔══╝  ██║     ██╔══██║██╔══██║     ██╔══██║██╔══██╗██╔══╝  ██║╚██╗██║██╔══██║
 ██║ ╚═╝ ██║███████╗╚██████╗██║  ██║██║  ██║     ██║  ██║██║  ██║███████╗██║ ╚████║██║  ██║
 ╚═╝     ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝
{RESET}
{AMARILLO}          ⚙️  Simulador de Robots & Combate Táctico  ⚙️{RESET}
"""

def limpiar_pantalla() -> None:
    os.system("cls" if os.name == "nt" else "clear")

def separador(char: str = "─", largo: int = 60) -> str:
    return char * largo

def input_texto(prompt: str) -> str:
    return input(f"{CYAN}{prompt}{RESET}").strip()

def mostrar_error(msg: str) -> None:
    print(f"\n{ROJO}❌ Error: {msg}{RESET}")

def mostrar_ok(msg: str) -> None:
    print(f"\n{VERDE}✅ {msg}{RESET}")

def pausar() -> None:
    input(f"\n{AMARILLO}[Presiona Enter para continuar...]{RESET}")


# ─────────────────────────────────────────────
#  CLASE PRINCIPAL CLI
# ─────────────────────────────────────────────

class CLIInterface:
    """Controlador principal del menú de consola."""

    def __init__(self) -> None:
        self._service = AppService()

    # ── Punto de entrada ─────────────────────

    def ejecutar(self) -> None:
        limpiar_pantalla()
        print(BANNER)
        pausar()
        while True:
            self._menu_principal()

    # ── Menús ────────────────────────────────

    def _menu_principal(self) -> None:
        limpiar_pantalla()
        print(f"{BOLD}{CYAN}╔══════════════════════════╗")
        print(f"║    🤖 MENÚ PRINCIPAL    ║")
        print(f"╚══════════════════════════╝{RESET}")
        print(f"  {AMARILLO}1.{RESET} 👤 Gestión de Pilotos")
        print(f"  {AMARILLO}2.{RESET} ⚙️  Ensamblaje de Mecha")
        print(f"  {AMARILLO}3.{RESET} ⚔️  Combate 1 vs 1")
        print(f"  {AMARILLO}4.{RESET} 🏆 Torneo")
        print(f"  {AMARILLO}5.{RESET} 📊 Clasificación & Historial")
        print(f"  {AMARILLO}0.{RESET} 🚪 Salir")
        print(separador())

        opcion = input_texto("Elige una opción: ")
        match opcion:
            case "1": self._menu_pilotos()
            case "2": self._menu_ensamblaje()
            case "3": self._menu_combate()
            case "4": self._menu_torneo()
            case "5": self._menu_clasificacion()
            case "0": self._salir()
            case _:   mostrar_error("Opción no válida.")

    # ───── Gestión de Pilotos ────────────────

    def _menu_pilotos(self) -> None:
        while True:
            limpiar_pantalla()
            print(f"{BOLD}👤 GESTIÓN DE PILOTOS{RESET}")
            print(separador())
            print(f"  {AMARILLO}1.{RESET} Registrar nuevo piloto")
            print(f"  {AMARILLO}2.{RESET} Ver todos los pilotos")
            print(f"  {AMARILLO}3.{RESET} Eliminar piloto")
            print(f"  {AMARILLO}0.{RESET} Volver")

            opcion = input_texto("Elige: ")
            match opcion:
                case "1": self._registrar_piloto()
                case "2": self._listar_pilotos()
                case "3": self._eliminar_piloto()
                case "0": return
                case _:   mostrar_error("Opción inválida.")

    def _registrar_piloto(self) -> None:
        nombre = input_texto("Nombre del piloto: ")
        try:
            piloto = self._service.registrar_piloto(nombre)
            mostrar_ok(f"Piloto '{piloto.nombre}' registrado correctamente.")
        except MechaArenaError as e:
            mostrar_error(str(e))
        pausar()

    def _listar_pilotos(self) -> None:
        pilotos = self._service.obtener_pilotos()
        limpiar_pantalla()
        print(f"{BOLD}📋 LISTA DE PILOTOS ({len(pilotos)}){RESET}")
        print(separador())
        if not pilotos:
            print("  (sin pilotos registrados)")
        for p in pilotos:
            mecha_info = (
                f"{p.mecha.nombre} | ATK {p.mecha.ataque_total} "
                f"DEF {p.mecha.defensa_total} VEL {p.mecha.velocidad}"
                if p.mecha else "Sin mecha"
            )
            listo = "✅" if (p.mecha and p.mecha.esta_listo_para_combate()) else "⚠️ "
            print(
                f"  {listo} {BOLD}{p.nombre}{RESET}"
                f" | V:{p.victorias} D:{p.derrotas} "
                f"| Mecha: {mecha_info}"
            )
        pausar()

    def _eliminar_piloto(self) -> None:
        nombre = input_texto("Nombre del piloto a eliminar: ")
        try:
            self._service.eliminar_piloto(nombre)
            mostrar_ok(f"Piloto '{nombre}' eliminado.")
        except MechaArenaError as e:
            mostrar_error(str(e))
        pausar()

    # ───── Ensamblaje ────────────────────────

    def _menu_ensamblaje(self) -> None:
        while True:
            limpiar_pantalla()
            print(f"{BOLD}⚙️  ENSAMBLAJE DE MECHA{RESET}")
            print(separador())
            print(f"  {AMARILLO}1.{RESET} Crear nuevo Mecha para un piloto")
            print(f"  {AMARILLO}2.{RESET} Ver catálogo de componentes")
            print(f"  {AMARILLO}3.{RESET} Instalar componente")
            print(f"  {AMARILLO}4.{RESET} Remover componente")
            print(f"  {AMARILLO}5.{RESET} Ver estado del Mecha")
            print(f"  {AMARILLO}0.{RESET} Volver")

            opcion = input_texto("Elige: ")
            match opcion:
                case "1": self._crear_mecha()
                case "2": self._mostrar_catalogo()
                case "3": self._instalar_componente()
                case "4": self._remover_componente()
                case "5": self._ver_mecha()
                case "0": return
                case _:   mostrar_error("Opción inválida.")

    def _crear_mecha(self) -> None:
        nombre_piloto = input_texto("Nombre del piloto: ")
        nombre_mecha  = input_texto("Nombre para el Mecha: ")
        try:
            mecha = self._service.crear_mecha_para_piloto(nombre_piloto, nombre_mecha)
            mostrar_ok(f"Mecha '{mecha.nombre}' creado y asignado a '{nombre_piloto}'.")
        except MechaArenaError as e:
            mostrar_error(str(e))
        pausar()

    def _mostrar_catalogo(self) -> None:
        limpiar_pantalla()
        catalogo = self._service.obtener_catalogo()
        print(f"{BOLD}🛒 CATÁLOGO DE COMPONENTES{RESET}")
        print(separador())

        tipo_actual = None
        for c in sorted(catalogo, key=lambda x: x.tipo.value):
            if c.tipo != tipo_actual:
                tipo_actual = c.tipo
                print(f"\n  {BOLD}{CYAN}{c.tipo.value.upper()}{RESET}")
            rareza_color = {
                RarezaComponente.COMUN:      "",
                RarezaComponente.RARO:       VERDE,
                RarezaComponente.EPICO:      AMARILLO,
                RarezaComponente.LEGENDARIO: ROJO,
            }.get(c.rareza, "")
            print(
                f"    • {rareza_color}{c.nombre}{RESET} "
                f"[{c.rareza.value}] "
                f"ATK+{c.bonus_ataque} DEF+{c.bonus_defensa} "
                f"Peso:{c.peso}kg"
            )
        pausar()

    def _instalar_componente(self) -> None:
        nombre_piloto    = input_texto("Nombre del piloto: ")
        nombre_componente = input_texto("Nombre exacto del componente: ")
        try:
            comp = self._service.instalar_componente(nombre_piloto, nombre_componente)
            mostrar_ok(
                f"'{comp.nombre}' instalado en el Mecha de '{nombre_piloto}'."
            )
        except MechaArenaError as e:
            mostrar_error(str(e))
        pausar()

    def _remover_componente(self) -> None:
        nombre_piloto = input_texto("Nombre del piloto: ")
        print("Tipos disponibles:")
        for i, t in enumerate(TipoComponente, 1):
            print(f"  {i}. {t.value}")
        idx = input_texto("Número de tipo a remover: ")
        tipos = list(TipoComponente)
        try:
            tipo = tipos[int(idx) - 1]
            removido = self._service.remover_componente(nombre_piloto, tipo)
            if removido:
                mostrar_ok(f"'{removido.nombre}' removido del Mecha.")
            else:
                mostrar_error("No se encontró componente de ese tipo.")
        except (ValueError, IndexError):
            mostrar_error("Número de tipo inválido.")
        except MechaArenaError as e:
            mostrar_error(str(e))
        pausar()

    def _ver_mecha(self) -> None:
        nombre_piloto = input_texto("Nombre del piloto: ")
        try:
            piloto = self._service.obtener_piloto(nombre_piloto)
            limpiar_pantalla()
            if piloto.mecha is None:
                print("  El piloto no tiene Mecha asignado.")
            else:
                m = piloto.mecha
                listo = "✅ Listo para combate" if m.esta_listo_para_combate() else "⚠️  Incompleto"
                print(f"\n{BOLD}🤖 Mecha: {m.nombre}{RESET}  [{listo}]")
                print(separador())
                print(f"  HP   : {m.hp_actual}/{m.hp_max}")
                print(f"  ATK  : {m.ataque_total}   DEF: {m.defensa_total}   VEL: {m.velocidad}")
                print(f"  Poder: {m.poder_total}")
                print(f"\n  {'Componentes instalados':}")
                for c in m.componentes:
                    print(f"    • {c.tipo.value}: {c.nombre} [{c.rareza.value}]"
                          f" ATK+{c.bonus_ataque} DEF+{c.bonus_defensa}")
                if not m.componentes:
                    print("    (ninguno)")
        except MechaArenaError as e:
            mostrar_error(str(e))
        pausar()

    # ───── Combate ───────────────────────────

    def _menu_combate(self) -> None:
        limpiar_pantalla()
        print(f"{BOLD}⚔️  COMBATE 1 vs 1{RESET}")
        print(separador())
        p1 = input_texto("Nombre del Piloto 1: ")
        p2 = input_texto("Nombre del Piloto 2: ")
        try:
            resultado = self._service.iniciar_combate(p1, p2)
            limpiar_pantalla()
            for linea in resultado.log_batalla:
                print(linea)
            print(f"\n{BOLD}{AMARILLO}{resultado.resumen()}{RESET}")
        except MechaArenaError as e:
            mostrar_error(str(e))
        pausar()

    # ───── Torneo ────────────────────────────

    def _menu_torneo(self) -> None:
        limpiar_pantalla()
        print(f"{BOLD}🏆 TORNEO ROUND-ROBIN{RESET}")
        print(separador())
        pilotos = self._service.obtener_pilotos()
        listos = [p.nombre for p in pilotos if p.mecha and p.mecha.esta_listo_para_combate()]

        if len(listos) < 2:
            mostrar_error("Se necesitan al menos 2 pilotos con mechas listos.")
            pausar()
            return

        print("Pilotos disponibles para el torneo:")
        for i, nombre in enumerate(listos, 1):
            print(f"  {i}. {nombre}")

        raw = input_texto("\nIngresa los números separados por comas (o Enter para todos): ")
        if raw.strip():
            try:
                indices = [int(x.strip()) - 1 for x in raw.split(",")]
                seleccionados = [listos[i] for i in indices]
            except (ValueError, IndexError):
                mostrar_error("Selección inválida.")
                pausar()
                return
        else:
            seleccionados = listos

        try:
            resultados = self._service.iniciar_torneo(seleccionados)
            limpiar_pantalla()
            print(f"{BOLD}🏆 RESULTADOS DEL TORNEO{RESET}")
            print(separador())
            for r in resultados:
                print(f"  {r.resumen()}")
            print(f"\n{BOLD}📊 CLASIFICACIÓN FINAL:{RESET}")
            self._mostrar_tabla_clasificacion()
        except MechaArenaError as e:
            mostrar_error(str(e))
        pausar()

    # ───── Clasificación & Historial ─────────

    def _menu_clasificacion(self) -> None:
        while True:
            limpiar_pantalla()
            print(f"{BOLD}📊 ESTADÍSTICAS{RESET}")
            print(separador())
            print(f"  {AMARILLO}1.{RESET} Clasificación de pilotos")
            print(f"  {AMARILLO}2.{RESET} Historial de combates")
            print(f"  {AMARILLO}0.{RESET} Volver")
            opcion = input_texto("Elige: ")
            match opcion:
                case "1": self._mostrar_tabla_clasificacion(); pausar()
                case "2": self._mostrar_historial(); pausar()
                case "0": return
                case _:   mostrar_error("Opción inválida.")

    def _mostrar_tabla_clasificacion(self) -> None:
        clasificacion = self._service.obtener_clasificacion()
        print(f"\n{'#':>3}  {'Piloto':<20} {'V':>4} {'D':>4} {'Ratio':>6}")
        print(separador("─", 42))
        for pos, (nombre, v, d, ratio) in enumerate(clasificacion, 1):
            medalla = "🥇" if pos == 1 else ("🥈" if pos == 2 else ("🥉" if pos == 3 else f"{pos: >2}."))
            print(f"  {medalla}  {nombre:<20} {v:>4} {d:>4} {ratio:>6.0%}")

    def _mostrar_historial(self) -> None:
        historial = self._service.obtener_historial()
        limpiar_pantalla()
        print(f"{BOLD}📜 HISTORIAL DE COMBATES ({len(historial)}){RESET}")
        print(separador())
        if not historial:
            print("  (sin combates registrados)")
        for i, r in enumerate(historial, 1):
            print(f"  {i:>3}. {r.resumen()}")

    # ───── Salida ────────────────────────────

    def _salir(self) -> None:
        limpiar_pantalla()
        print(f"\n{CYAN}{BOLD}¡Hasta la próxima batalla, piloto! 🤖💥{RESET}\n")
        sys.exit(0)
