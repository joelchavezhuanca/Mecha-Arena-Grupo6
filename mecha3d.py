"""
MECHA-ARENA 3D - Combate táctico de robots (Ursina / Panda3D).

Rehace en 3D real el juego de pelea 2D. Dos robots se enfrentan en un
ring con cámara en tercera persona sobre el hombro.

Controles:
    Flechas (o WASD)          Moverse (izq/der) y bloquear (abajo)
    Espacio / Flecha arriba   Saltar
    Z                         Ataque rapido
    X                         Golpe fuerte
    C                         Especial (proyectil, gasta energia)
    A                         Dash
    Q                         Salir
    R                         Reiniciar partida (tras ver el resultado)

Ejecutar:
    py mecha3d.py
"""

from __future__ import annotations

import math
import random
import sys

from ursina import *


# ======================================================================
# Utilidades
# ======================================================================
def clampi(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


# ======================================================================
# Campos y presets de robot
# ======================================================================
ARENA_HALF = 10.0          # limite lateral (x en [-10, 10])
JUMP_FUERZA = 8.0
GRAVEDAD = -22.0


def tecla_presa(*nombres):
    """True si cualquiera de los nombres de tecla está pulsado."""
    try:
        return any(held_keys.get(n) for n in nombres)
    except Exception:
        return False

PRESETS = [
    # nombre, color_principal, color_sec, hp, atk_rapido, atk_fuerte, espl
    ("Acero Azul",   color.rgb(70, 140, 255), color.rgb(40, 80, 160),
     100, 8, 18, 12),
    ("Cromo Rojo",   color.rgb(255, 90, 70),  color.rgb(170, 40, 40),
     90,  10, 20, 14),
    ("Titanio Oro",  color.rgb(250, 205, 90), color.rgb(150, 110, 30),
     115, 6, 22, 16),
]

# ======================================================================
# Particulas y proyectiles
# ======================================================================
PARTICULAS: list[Entity] = []


def chispa(centro, color_, n=14, velocidad=6.0):
    for _ in range(n):
        p = Entity(model="cube", color=color_, collider=None,
                   scale=random.uniform(0.08, 0.22),
                   position=centro + Vec3(random.uniform(-0.4, 0.4),
                                          random.uniform(-0.3, 0.6),
                                          random.uniform(-0.4, 0.4)))
        p.vel = Vec3(random.uniform(-1, 1) * velocidad,
                     random.uniform(0.5, 2.0) * velocidad,
                     random.uniform(-1, 1) * velocidad)
        p.life = random.uniform(0.25, 0.6)
        p.rot = Vec3(random.random() * 360, random.random() * 360, 0)
        PARTICULAS.append(p)


PROYECTILES: list[Entity] = []


# ======================================================================
# Robot (modelo de bloques)
# ======================================================================
class Robot:
    """Un luchador construido con piezas de bloques (3D real)."""

    def __init__(self, x: float, preset: int, es_ia: bool) -> None:
        nombre, c_main, c_sec, hp, a1, a2, es = PRESETS[preset]
        self.es_ia = es_ia
        self.nombre = nombre
        self.hp_max = hp
        self.hp = hp
        self.energia_max = 100.0
        self.energia = 60.0
        self.ataque_rapido = a1
        self.ataque_fuerte = a2
        self.especial = es

        self.raiz = Entity(position=Vec3(x, 0, 0))
        self.color_main = c_main
        self.color_sec = c_sec
        self._construir_cuerpo()

        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.grounded = True
        self.block = False
        self.invencible = 0.0
        self.hitstop = 0.0
        self.estado = "idle"          # idle/walk/block/attack/stun/ko
        self.atk_tipo = None
        self.atk_t = 0.0
        self.atk_duracion = 0.0
        self.atk_golpe = False
        self.goleado = False
        self.dash_t = 0.0

    # ----- construcción de la figura de bloques -----
    def _pieza(self, parent, size, pos, color_):
        p = Entity(parent=parent, model="cube", color=color_,
                   collider=None, scale=size, position=pos)
        return p

    def _construir_cuerpo(self) -> None:
        base = self.raiz
        s = 1.0
        self.torso = self._pieza(base, (0.9 * s, 1.2 * s, 0.6 * s),
                                 (0, 1.6 * s, 0), self.color_main)
        self.cabeza = self._pieza(base, (0.55 * s, 0.55 * s, 0.5 * s),
                                  (0, 2.55 * s, 0), self.color_sec)
        self.frente = self._pieza(self.cabeza,
                                  (0.34 * s, 0.14 * s, 0.06 * s),
                                  (0, 0.1 * s, 0.34 * s), color.dark_gray)
        self.brazo_iz = self._pieza(base, (0.28 * s, 0.9 * s, 0.3 * s),
                                    (-0.62 * s, 1.85 * s, 0), self.color_sec)
        self.brazo_de = self._pieza(base, (0.28 * s, 0.9 * s, 0.3 * s),
                                    (0.62 * s, 1.85 * s, 0), self.color_sec)
        self.pierna_iz = self._pieza(base, (0.34 * s, 0.8 * s, 0.34 * s),
                                     (-0.28 * s, 0.4 * s, 0), self.color_main)
        self.pierna_de = self._pieza(base, (0.34 * s, 0.8 * s, 0.34 * s),
                                     (0.28 * s, 0.4 * s, 0), self.color_main)
        self.omo = self._pieza(base, (0.34, 0.2, 0.2),
                               (0.62 * s, 2.3 * s, 0), color.dark_gray)

    # ----- atributos -----
    @property
    def x(self):
        return self.raiz.x

    @x.setter
    def x(self, valor):
        self.raiz.x = valor

    @property
    def y(self):
        return self.raiz.y

    @y.setter
    def y(self, valor):
        self.raiz.y = valor

    # ----- acciones -----
    def puede_actuar(self) -> bool:
        return (self.estado not in ("stun", "ko")
                and self.hitstop <= 0 and not self.goleado)

    def mover(self, direccion: int) -> None:
        if self.puede_actuar() and self.estado != "attack":
            self.vx = 3.6 * direccion
            self.facing = direccion

    def saltar(self) -> None:
        if self.puede_actuar() and self.grounded:
            self.vy = JUMP_FUERZA
            self.grounded = False

    def iniciar_bloqueo(self, activo: bool) -> None:
        if activo:
            if self.puede_actuar() and self.grounded:
                self.block = True
                self.vx = 0.0
        else:
            self.block = False

    def dash(self) -> None:
        if self.puede_actuar() and self.grounded and self.dash_t <= 0:
            self.dash_t = 0.18
            self.vx = 9.0 * self.facing
            self.invencible = max(self.invencible, 0.18)
            chispa(self.raiz.position + Vec3(0, 1.2, 0),
                   self.color_main, n=8, velocidad=4)

    def atacar(self, tipo: str) -> None:
        if not self.puede_actuar() or self.estado == "attack":
            return
        costo = {"rapido": 8, "fuerte": 22, "especial": 40}[tipo]
        if self.energia >= costo:
            self.energia -= costo
            self.estado = "attack"
            self.atk_tipo = tipo
            self.atk_t = 0.0
            self.atk_golpe = False
            self.vx = 0.0
            self.atk_duracion = {"rapido": 0.28, "fuerte": 0.5,
                                 "especial": 0.45}[tipo]

    # ----- daño -----
    def recibir_danio(self, raw: int, push: float) -> int:
        """Aplica daño (con bloqueo y golpes ya resueltos) y retorno."""

        if self.invencible > 0 or self.goleado:
            return 0
        if self.block:
            danio = max(1, int(raw * 0.17))
            self.hp = max(0, self.hp - danio)
            self.vx = push * 0.5
            chispa(self.raiz.position + Vec3(0, 1.5, 0), color.blue,
                   n=8, velocidad=3)
        else:
            danio = raw
            self.hp = max(0, self.hp - danio)
            self.estado = "stun"
            self.atk_t = 0.0
            self.vx = push
            self.invencible = 0.35
            chispa(self.raiz.position + Vec3(0, 1.6, 0), color.orange,
                   n=18, velocidad=7)
            if self.hp <= 0:
                self.goleado = True
                self.estado = "ko"
        return danio

    # ----- actualizacion -----
    def update(self, dt: float) -> None:
        if self.hitstop > 0:
            self.hitstop -= dt
            return

        self.energia = min(self.energia_max,
                           self.energia + 2.4 * dt)
        self.invencible = max(0.0, self.invencible - dt)
        self.dash_t = max(0.0, self.dash_t - dt)

        if self.estado == "attack":
            self.atk_t += dt
            if self.atk_t >= self.atk_duracion:
                self.estado = "idle"
                self.atk_t = 0.0

        if self.estado == "stun":
            self.atk_t += dt
            if self.atk_t >= 0.4:
                self.estado = "idle"
                self.atk_t = 0.0

        # fisica
        if self.grounded:
            self.vy = 0.0
        else:
            self.vy += GRAVEDAD * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.y <= 0:
            self.y = 0
            self.grounded = True

        # limites de la arena
        if self.x < -ARENA_HALF:
            self.x = -ARENA_HALF
            self.vx = 0
        if self.x > ARENA_HALF:
            self.x = ARENA_HALF
            self.vx = 0

        # friccion
        if self.estado != "attack" and self.dash_t <= 0 and not self.block:
            self.vx = lerp(self.vx, 0.0, 0.12)

        # animacion del cuerpo
        self._animar()

    def _animar(self) -> None:
        s = 1.0
        # marcha
        if self.estado == "attack":
            prog = self.atk_t / max(self.atk_duracion, 0.001)
            self.estado_movimiento_ataque(prog)
        else:
            self.brazo_de.position = (0.62 * s, 1.85 * s, 0)
            self.brazo_de.rotation_x = 0
            self.omo.rotation_x = 0
            andar = abs(self.vx) if self.block == False else 0
            ang = math.sin(time.time() * 9) * (0.5 if andar > 1 else 0)
            self.pierna_iz.rotation_x = ang * 30
            self.pierna_de.rotation_x = -ang * 30
            self.brazo_iz.rotation_x = -ang * 20
            self.brazo_de.rotation_x = ang * 20

        if self.block:
            self._pose_bloqueo()
        if not self.grounded:
            self.pierna_iz.rotation_x = 25
            self.pierna_de.rotation_x = -25

        # orientacion
        self.raiz.rotation_y = (180 if self.facing > 0 else 0)

        # KO tumbado
        if self.estado == "ko":
            self.raiz.rotation_z = 85 * (1 if self.facing > 0 else -1)
            self.raiz.y = 0.1

    def _pose_bloqueo(self) -> None:
        self.brazo_iz.rotation_x = -70
        self.brazo_de.rotation_x = -70
        self.pierna_iz.rotation_x = 0
        self.pierna_de.rotation_x = 0

    def estado_movimiento_ataque(self, prog: float) -> None:
        """Estira el brazo hacia adelante en la fase activa del golpe."""
        lunge = math.sin(min(prog, 1.0) * math.pi)
        extension = lunge * (0.35 if self.atk_tipo != "fuerte" else 0.55)
        self.brazo_de.rotation_x = -lunge * 90
        self.brazo_de.position = (0.62 * 1.0 + extension, 1.85, 0)
        self.omo.rotation_x = -lunge * 40

    # ----- dibujado manual de golpe (para HUD no aplica) -----
    def brazo_punta(self) -> Vec3:
        """Posición mundial del puño (para proyectiles / rangos)."""
        bx = self.brazo_de.world_position
        return Vec3(bx.x, bx.y, bx.z)


# ======================================================================
# ARENA 3D
# ======================================================================
def construir_arena() -> None:
    piso = Entity(model="plane", scale=(ARENA_HALF * 2 + 6, 40), texture=None,
                  collider=None, color=color.rgb(18, 28, 48),
                  position=(0, 0, 0), rotation=(90, 0, 0))
    red = Entity(model="plane", scale=(ARENA_HALF * 2 + 4, 26), texture=None,
                 collider=None, color=color.rgb(26, 40, 68),
                 position=(0, 0.05, 0), rotation=(90, 0, 0))
    rejilla = Entity(model="cube", scale=(ARENA_HALF * 2, 0.3, 14),
                     collider=None, color=color.rgb(35, 55, 92),
                     position=(0, 0.15, 0))
    # lineas de luz del ring
    for i in range(-int(ARENA_HALF), int(ARENA_HALF) + 1, 4):
        Entity(model="cube", scale=(0.08, 0.02, 12), texture=None,
               collider=None, color=color.rgb(70, 120, 200),
               position=(float(i), 0.18, 0))
    # plataforma elevada central
    Entity(model="cube", scale=(6, 0.5, 6), texture=None,
           collider=None, color=color.rgb(45, 70, 110),
           position=(0, 0.6, 0))
    # torretas de luz
    for x in (-ARENA_HALF, ARENA_HALF):
        Entity(model="cube", scale=(0.5, 3.4, 0.5), texture=None,
               collider=None, color=color.rgb(90, 150, 220),
               position=(x, 1.7, -4))
        Entity(model="cube", scale=(1.2, 0.4, 1.2), texture=None,
               collider=None, color=color.rgb(60, 110, 180),
               position=(x, 0.2, -4))
        Entity(model="sphere", scale=0.8, texture=None, collider=None,
               color=color.white, position=(x, 3.5, -4))


# ======================================================================
# CONTROLADOR DE IA
# ======================================================================
class IA:
    def __init__(self) -> None:
        self.think = 0.4
        self.meta = 0.0
        self.dist = 0.0

    def update(self, ai: Robot, jugador: Robot, dt: float) -> None:
        self.think -= dt
        if self.think > 0:
            return

        d = ai.x - jugador.x
        ad = abs(d)
        self.meta = 1 if d > 0.3 else (-1 if d < -0.3 else 0)

        if ad > 4.5:
            accion = random.choice(("avanzar", "avanzar", "dash"))
            if accion == "dash":
                ai.dash()
        elif ad < 2.2 and ad > 1.2:
            accion = random.choices(
                ("rapido", "fuerte", "especial", "bloquear"),
                weights=(6, 3, 2, 2))[0]
            if accion == "rapido":
                ai.atacar("rapido")
            elif accion == "fuerte":
                ai.atacar("fuerte")
            elif accion == "especial":
                ai.atacar("especial")
            else:
                ai.iniciar_bloqueo(True)
        elif ad <= 1.2:
            accion = random.choices(
                ("rapido", "fuerte", "bloquear", "salto"),
                weights=(6, 3, 3, 1))[0]
            if accion in ("rapido", "fuerte"):
                ai.atacar(accion)
            elif accion == "bloquear":
                ai.iniciar_bloqueo(True)
            else:
                ai.saltar()
                ai.vx = 2.5 * self.meta
        else:
            accion = random.choices(("avanzar", "bloquear"),
                                    weights=(8, 2))[0]
            if accion == "bloquear":
                ai.iniciar_bloqueo(True)

        if accion != "bloquear":
            ai.iniciar_bloqueo(False)
        if ai.estado != "attack" and accion != "bloquear":
            ai.mover(self.meta)
        self.think = random.uniform(0.6, 1.2)


# ======================================================================
# JUEGO (estado global manejado por update() e input() de Ursina)
# ======================================================================
juego = None


class FightingGame:
    def __init__(self) -> None:
        self.presets_jugador = 0
        self.ia = IA()
        self.time_scale = 1.0
        self.shake = 0.0
        self.ronda = 1
        self.p_ganadas = 0
        self.i_ganadas = 0
        self.MAX_RONDAS = 3
        self.ganar_hasta = 2
        self.fase = "intro"
        self.fase_t = 2.0
        self.mensaje_texto = Text("", scale=2.4, color=color.gold,
                                  position=(0, 0.3), origin=(0, 0))
        self._crear_hud()
        self._nueva_ronda()
        construir_arena()

    # ---------- HUD ----------
    def _crear_hud(self) -> None:
        # nombres
        self.nombre_p = Text("JUGADOR", scale=1.5, color=color.white,
                             position=(-0.32, 0.42), parent=camera.ui)
        self.nombre_i = Text("CPU", scale=1.5, color=color.white,
                             position=(0.32, 0.42), parent=camera.ui)
        # fondo de las barras
        self.hp_fondo_p = Entity(parent=camera.ui, model="quad",
                                 collider=None, color=color.black,
                                 scale=(0.3, 0.05), position=(-0.32, 0.37))
        self.hp_fondo_i = Entity(parent=camera.ui, model="quad",
                                 collider=None, color=color.black,
                                 scale=(0.3, 0.05), position=(0.32, 0.37))
        # relleno
        self.hp_p = Entity(parent=camera.ui, model="quad", collider=None,
                           color=color.rgb(80, 220, 120),
                           scale=(0.29, 0.042), position=(-0.32, 0.37))
        self.hp_i = Entity(parent=camera.ui, model="quad", collider=None,
                           color=color.rgb(240, 90, 90),
                           scale=(0.29, 0.042), position=(0.32, 0.37))
        # energia
        self.en_p = Entity(parent=camera.ui, model="quad", collider=None,
                           color=color.rgb(80, 150, 255),
                           scale=(0.22, 0.02), position=(-0.32, 0.33))
        self.en_i = Entity(parent=camera.ui, model="quad", collider=None,
                           color=color.rgb(80, 150, 255),
                           scale=(0.22, 0.02), position=(0.32, 0.33))
        self.txt_marcador = Text("0 - 0", scale=1.6, color=color.white,
                                 position=(0, 0.44), origin=(0, 0))
        self.txt_ronda = Text("RONDA 1", scale=1.2, color=color.lime,
                              position=(0, 0.34), origin=(0, 0))

    def _nueva_ronda(self) -> None:
        luchador = getattr(self, "player", None)
        if luchador is not None:
            try:
                destroy(self.player.raiz)
                destroy(self.ai.raiz)
            except Exception:
                pass
        p_idx = self.presets_jugador
        i_idx = random.choice([i for i in range(len(PRESETS))
                               if i != p_idx])
        self.player = Robot(-4.0, p_idx, es_ia=False)
        self.player.facing = 1
        self.ai = Robot(4.0, i_idx, es_ia=True)
        self.ai.facing = -1
        self.nombre_p.text = self.player.nombre
        self.nombre_i.text = self.ai.nombre
        self.player.hp = self.player.hp_max
        self.ai.hp = self.ai.hp_max
        self.player.energia = 60
        self.ai.energia = 60
        self.time_scale = 1.0
        self.fase = "intro"
        self.fase_t = 1.6

    def _resetear_combate(self) -> None:
        self.ronda += 1
        self._nueva_ronda()
        self.txt_ronda.text = f"RONDA {self.ronda}"

    def _fin_partida(self) -> None:
        self.fase = "fin"
        if self.p_ganadas >= self.ganar_hasta:
            self.mensaje_texto.text = "VICTORIA"
            self.mensaje_texto.color = color.gold
            chispa(self.player.raiz.position, color.gold, n=30, velocidad=5)
        else:
            self.mensaje_texto.text = "DERROTA"
            self.mensaje_texto.color = color.rgb(255, 80, 80)
        self.mensaje_texto.scale = 3.0
        self.revancha_hint = Text("Pulsa R para revancha · Q para salir",
                                  scale=1.1, color=color.white,
                                  position=(0, 0.12), origin=(0, 0))

    # ---------- entrada ----------
    def input(self, key: str) -> None:
        if key == "q":
            application.quit()
        if self.fase == "fin":
            if key == "r":
                self.p_ganadas = 0
                self.i_ganadas = 0
                self.ronda = 1
                self._resetear_combate()
                try:
                    destroy(self.revancha_hint)
                except Exception:
                    pass
                self.txt_ronda.text = "RONDA 1"
                self.mensaje_texto.text = ""
                self.mensaje_texto.scale = 2.4
            return
        if key in ("space", "up arrow", "arrow up"):
            self.player.saltar()
        elif key == "z":
            self.player.atacar("rapido")
        elif key == "x":
            self.player.atacar("fuerte")
        elif key == "c":
            self.player.atacar("especial")
        elif key == "a":
            self.player.dash()

    def _jugador_input_continuo(self) -> None:
        izq = tecla_presa("left arrow", "arrow left", "a")
        der = tecla_presa("right arrow", "arrow right", "d")
        abajo = tecla_presa("down arrow", "arrow down", "s")
        if izq and not der:
            self.player.mover(-1)
        elif der and not izq:
            self.player.mover(1)
        else:
            if self.player.estado != "attack":
                self.player.vx = lerp(self.player.vx, 0.0, 0.12)
        self.player.iniciar_bloqueo(abajo)
        if abajo:
            self.player.vx = 0.0

    # ---------- combate ----------
    def _proyectiles(self) -> None:
        for pr in list(PROYECTILES):
            pr.x += pr.dir * 14 * time.dt
            pr.life -= time.dt
            objetivo = self.ai if pr.dueño is self.player else self.player
            if (abs(pr.x - objetivo.x) < 1.1
                    and abs(pr.y - objetivo.y) < 1.6
                    and 0 < time.time() - pr.nac < 2.0):
                objetivo.recibir_danio(pr.danio, pr.dir * 4.0)
                chispa(pr.position, color.cyan, n=14, velocidad=5)
                destroy(pr)
                PROYECTILES.remove(pr)
            elif pr.life <= 0 or abs(pr.x) > ARENA_HALF + 2:
                destroy(pr)
                PROYECTILES.remove(pr)

    def _golpes(self) -> None:
        """Resuelve el contacto de ataques cuerpo a cuerpo."""
        for atacante, defensor in ((self.player, self.ai),
                                   (self.ai, self.player)):
            if atacante.estado != "attack" or atacante.atk_golpe:
                continue
            ventana = (0.15, 0.55)
            prog = atacante.atk_t / max(atacante.atk_duracion, 0.001)
            if not (ventana[0] <= prog <= ventana[1]):
                continue
            d = abs(atacante.x - defensor.x)
            alcance = 1.6 if atacante.atk_tipo in ("rapido", "fuerte") \
                else 3.2
            if d > alcance or abs(atacante.y - defensor.y) > 1.6:
                continue
            if atacante.atk_tipo == "rapido":
                danio = atacante.ataque_rapido
            elif atacante.atk_tipo == "fuerte":
                danio = atacante.ataque_fuerte
            else:
                continue  # el especial viaja como proyectil
            push = 3.0 if atacante.atk_tipo == "fuerte" else 1.8
            atacante.atk_golpe = True
            self.time_scale = 0.35
            self.shake = 0.25
            defensor.recibir_danio(danio, push * atacante.facing)

    def _lanzar_especial(self, robot: Robot) -> None:
        pr = Entity(model="sphere", scale=0.55, texture=None,
                    collider=None,
                    color=(color.cyan if not robot.es_ia else color.orange),
                    position=robot.raiz.position + Vec3(0, 1.4, 0))
        pr.dir = robot.facing
        pr.dueño = robot
        pr.danio = robot.especial
        pr.life = 2.0
        pr.nac = time.time()
        PROYECTILES.append(pr)
        chispa(pr.position, color.cyan, n=10, velocidad=4)

    # ---------- flujo ----------
    def update(self, dt: float) -> None:
        dt = dt * self.time_scale
        self.shake = max(0.0, self.shake - dt)

        # particulas siempre
        for p in list(PARTICULAS):
            p.position += p.vel * dt
            p.vel.y += GRAVEDAD * 0.4 * dt
            p.rotation += p.rot * dt
            p.life -= dt
            if p.life <= 0:
                destroy(p)
                PARTICULAS.remove(p)
        self._proyectiles()

        if self.fase == "intro":
            self.fase_t -= dt
            if self.fase_t <= 0:
                self.fase = "pelea"
            return
        if self.fase in ("ko", "fin"):
            self.fase_t -= dt
            if self.fase == "ko" and self.fase_t <= 0:
                if self.p_ganadas >= self.ganar_hasta or \
                        self.i_ganadas >= self.ganar_hasta:
                    self._fin_partida()
                else:
                    self._resetear_combate()
            return

        # --- pelea ---
        self._jugador_input_continuo()

        self.ia.update(self.ai, self.player, dt)

        # especiales lanzados
        if self.player.estado == "attack" and self.player.atk_tipo == \
                "especial" and not hasattr(self, "_especial_p"):
            self._lanzar_especial(self.player)
            self._especial_p = True
        if self.player.estado != "attack" or self.player.atk_tipo != "especial":
            self._especial_p = False
        if self.ai.estado == "attack" and self.ai.atk_tipo == "especial" \
                and not hasattr(self, "_especial_i"):
            self._lanzar_especial(self.ai)
            self._especial_i = True
        if self.ai.estado != "attack" or self.ai.atk_tipo != "especial":
            self._especial_i = False

        self._golpes()

        self.player.update(dt)
        self.ai.update(dt)

        # victorias de ronda
        if self.fase == "pelea" and (self.player.hp <= 0 or self.ai.hp <= 0):
            self.fase = "ko"
            self.fase_t = 1.8
            self.time_scale = 0.35
            self.shake = 0.4
            if self.ai.hp <= 0:
                self.p_ganadas += 1
                self.mensaje_texto.text = "K.O. JUGADOR"
            else:
                self.i_ganadas += 1
                self.mensaje_texto.text = "K.O. CPU"

        self._hud()

    def _hud(self) -> None:
        self.hp_p.scale_x = 0.29 * (self.player.hp / self.player.hp_max)
        self.hp_i.scale_x = 0.29 * (self.ai.hp / self.ai.hp_max)
        self.en_p.scale_x = 0.22 * (self.player.energia / 100.0)
        self.en_i.scale_x = 0.22 * (self.ai.energia / 100.0)
        self.txt_marcador.text = f"{self.p_ganadas} - {self.i_ganadas}"
        if self.fase != "fin":
            self.txt_ronda.text = f"RONDA {max(1, self.ronda)}"

    def camera_update(self) -> None:
        medio = (self.player.x + self.ai.x) * 0.5
        medio_x = clampi(medio * 0.55, -3, 3)
        suav = lerp(camera.x, medio_x, min(1, time.dt * 3))
        if self.shake > 0:
            suav += random.uniform(-0.12, 0.12) * self.shake * 3
        camera.position = Vec3(suav, 8.5, -13)
        camera.rotation = (32, 0, 0)


# ======================================================================
# Integración con Ursina
# ======================================================================
def update():
    if juego:
        juego.update(time.dt)
        juego.camera_update()


def input(key):
    if juego:
        juego.input(key)


def main() -> None:
    global juego
    app = Ursina(borderless=False, title="Mecha-Arena 3D",
                 size=(1280, 720), development_mode=False)
    window.exit_button.visible = False
    mouse.visible = False
    window.color = color.rgb(10, 14, 26)
    Sky(color=color.rgb(10, 14, 26))
    DirectionalLight(y=10, z=6, rotation=(45, -30, 0))
    AmbientLight(color=color.rgb(120, 140, 170))
    juego = FightingGame()
    app.run()


if __name__ == "__main__":
    main()