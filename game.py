"""
MECHA-ARENA v5.0 — Real Fighter + Character Select
══════════════════════════════════════════════════
CONTROLES EN PELEA:
  ← →        Moverse
  ↑ / SPACE  Saltar
  ↓          Bloquear (83% reducción de daño)
  Z          Ataque rápido
  X          Golpe fuerte
  C          Especial ⚡ (requiere energía)
  A          Dash
══════════════════════════════════════════════════
Ejecutar: py game.py
"""
from __future__ import annotations
import sys, os, math, random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

os.environ["PYTHONUTF8"] = "1"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

ROOT   = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from src.domain.exceptions import MechaArenaError
from src.services.app_service import AppService

W, H   = 1280, 720
FPS    = 60
ASSETS = os.path.join(ROOT, "assets")
AI_NAME = "NEMESIS-X"

GROUND_Y  = 510
GRAVITY   = 0.65
JUMP_VY   = -16.0
WALK_SPD  = 5.0
DASH_SPD  = 16.0
DASH_DUR  = 0.22
PUSH_DIST = 145

C = {
    "bg":     (5, 8, 18),
    "text":   (210, 230, 255),
    "dim":    (100, 130, 160),
    "gold":   (255, 210, 0),
    "green":  (0, 220, 100),
    "red":    (220, 40, 40),
    "white":  (255, 255, 255),
    "border": (0, 200, 255),
    "orange": (255, 140, 0),
}


# ─────────────────────────────────────────────
#  ROSTER DE PERSONAJES
# ─────────────────────────────────────────────

@dataclass
class CharDef:
    name:    str
    sprite:  str          # filename in assets/
    color:   tuple        # accent color (R,G,B)
    atk:     int          # base attack
    dfn:     int          # base defense
    hp:      int          # base HP
    spd:     float        # speed multiplier
    desc:    str          # short description
    arch:    str          # archetype label
    bg_white:bool = False # True → remove white bg, False → remove dark bg

CHARACTERS: List[CharDef] = [
    CharDef("GUARDIAN",  "char_guardian.jpg",  (0,  200,255), 50, 25,200, 1.00,
            "Espada de plasma + Escudo",   "BALANCEADO",  bg_white=False),
    CharDef("BERSERKER", "char_berserker.jpg", (255, 70, 20), 80, 16,180, 1.15,
            "Hacha de fuego | Alto ATK",   "AGRESIVO",    bg_white=False),
    CharDef("TITAN",     "char_titan.jpg",     (30, 210, 60), 62, 34,300, 0.70,
            "Martillo devastador | Tank",  "TANQUE",      bg_white=False),
    CharDef("SPECTER",   "char_specter.jpg",   (190, 60,255), 58, 19,160, 1.60,
            "Katanas duales | Ultra rápido","VELOCIDAD",  bg_white=True),
    CharDef("SENTINEL",  "char_sentinel.jpg",  (255,200,  0), 43, 40,260, 0.75,
            "Cañón de plasma | Armadura",  "DEFENSOR",    bg_white=True),
    CharDef("PHANTOM",   "char_phantom.jpg",   (120,220,255), 55, 22,180, 1.35,
            "Alas de energía | Sigilo",    "ÁGIL",        bg_white=False),
]


# ─────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────

def lerp(a, b, t): return a + (b - a) * min(1, max(0, t))
def pulse(t, spd=2, lo=0.5, hi=1.0):
    return lo + (hi - lo) * (0.5 + 0.5 * math.sin(t * spd))

def load_img(name, size):
    img = pygame.image.load(os.path.join(ASSETS, name)).convert()
    return pygame.transform.smoothscale(img, size)

def load_sprite(name: str, size: tuple, bg_white: bool = False) -> pygame.Surface:
    """Carga el sprite con transparencia alfa nativa o fallback."""
    # 1. Si existe la versión PNG transparente, cargar directamente con convert_alpha()
    png_name = os.path.splitext(name)[0] + ".png"
    png_path = os.path.join(ASSETS, png_name)
    if os.path.exists(png_path):
        raw = pygame.image.load(png_path).convert_alpha()
        return pygame.transform.smoothscale(raw, size)

    direct_path = os.path.join(ASSETS, name)
    if name.lower().endswith(".png") and os.path.exists(direct_path):
        raw = pygame.image.load(direct_path).convert_alpha()
        return pygame.transform.smoothscale(raw, size)

    # 2. Fallback para JPG
    raw = load_img(name, size)
    result = pygame.Surface(size, pygame.SRCALPHA)
    result.blit(raw, (0, 0))
    try:
        px = pygame.surfarray.pixels3d(result)
        aa = pygame.surfarray.pixels_alpha(result)
        r = px[:, :, 0].astype('int32')
        g = px[:, :, 1].astype('int32')
        b = px[:, :, 2].astype('int32')
        brightness = r + g + b
        if bg_white:
            mask = brightness > 230 * 3
        else:
            mask = brightness < 60 * 3
        aa[mask] = 0
        del px, aa
    except Exception:
        result.set_colorkey((0, 0, 0) if not bg_white else (255, 255, 255))
    return result

def draw_panel(surf, rect, color=(15, 22, 40), alpha=210,
               border=(0, 200, 255), bw=2, radius=10):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=radius)
    surf.blit(s, rect.topleft)
    if bw:
        pygame.draw.rect(surf, border, rect, bw, border_radius=radius)

def draw_text(surf, txt, font, col, center=None, topleft=None, shadow=True):
    if shadow:
        sh = font.render(txt, True, (0, 0, 0))
        r  = sh.get_rect()
        if center:  r.center  = (center[0] + 2,  center[1] + 2)
        if topleft: r.topleft = (topleft[0] + 2, topleft[1] + 2)
        surf.blit(sh, r)
    img = font.render(txt, True, col)
    r   = img.get_rect()
    if center:  r.center  = center
    if topleft: r.topleft = topleft
    surf.blit(img, r)
    return r

def draw_hp(surf, x, y, w, h, cur, mx):
    ratio = max(0, cur / mx) if mx else 0
    pygame.draw.rect(surf, (40, 40, 40), (x, y, w, h), border_radius=4)
    col = (30, 210, 80) if ratio > .5 else ((230, 180, 0) if ratio > .25 else (210, 30, 30))
    if ratio > 0:
        pygame.draw.rect(surf, col, (x, y, int(w * ratio), h), border_radius=4)
    pygame.draw.rect(surf, (160, 160, 160), (x, y, w, h), 1, border_radius=4)

def draw_energy(surf, x, y, w, h, en):
    pygame.draw.rect(surf, (20, 10, 50), (x, y, w, h), border_radius=3)
    if en > 0:
        pygame.draw.rect(surf, (170, 50, 255), (x, y, int(w * en / 100), h), border_radius=3)
    pygame.draw.rect(surf, (140, 40, 220), (x, y, w, h), 1, border_radius=3)

def draw_stat_bar(surf, x, y, w, h, val, max_val, col):
    ratio = min(1, val / max_val)
    pygame.draw.rect(surf, (30, 30, 50), (x, y, w, h), border_radius=3)
    if ratio > 0:
        pygame.draw.rect(surf, col, (x, y, int(w * ratio), h), border_radius=3)
    pygame.draw.rect(surf, (80, 80, 120), (x, y, w, h), 1, border_radius=3)


# ─────────────────────────────────────────────
#  FX
# ─────────────────────────────────────────────

class Particle:
    def __init__(self, x, y, col, vx=None, vy=None, life=None, size=None):
        self.x, self.y = float(x), float(y)
        self.col = col
        self.vx = vx if vx is not None else random.uniform(-5, 5)
        self.vy = vy if vy is not None else random.uniform(-7, -1)
        self.life = life or random.uniform(0.35, 0.9)
        self.ml = self.life
        self.size = size or random.randint(3, 7)

    def update(self, dt):
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vy += 0.25 * dt * 60
        self.life -= dt

    @property
    def alive(self): return self.life > 0

    def draw(self, surf):
        a = int(255 * max(0, self.life / self.ml))
        r = max(1, int(self.size * self.life / self.ml))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.col, a), (r, r), r)
        surf.blit(s, (int(self.x) - r, int(self.y) - r))


class FX(list):
    def emit(self, x, y, col, n=12, **kw):
        for _ in range(n): self.append(Particle(x, y, col, **kw))

    def update(self, dt):
        self[:] = [p for p in self if p.alive]
        for p in self: p.update(dt)

    def draw(self, surf):
        for p in self: p.draw(surf)


class HitNumber:
    def __init__(self, x, y, text, col, big=False):
        self.x, self.y = float(x), float(y)
        self.text = text; self.col = col; self.big = big
        self.life = 1.4; self.ml = 1.4; self.vy = -2.0

    def update(self, dt):
        self.y += self.vy * dt * 60
        self.vy += 0.05 * dt * 60
        self.life -= dt

    @property
    def alive(self): return self.life > 0

    def draw(self, surf, f_big, f_norm):
        a = int(255 * max(0, self.life / self.ml))
        img = (f_big if self.big else f_norm).render(self.text, True, self.col)
        img.set_alpha(a)
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


class Projectile:
    def __init__(self, x, y, direction, damage, col):
        self.x, self.y = float(x), float(y)
        self.vx = direction * 14.0
        self.damage = damage; self.col = col
        self.alive = True; self.t = 0.0; self.r = 26

    def update(self, dt):
        self.x += self.vx * dt * 60
        self.t += dt
        if self.x < -80 or self.x > W + 80: self.alive = False

    def draw(self, surf):
        cr = self.r + int(6 * math.sin(self.t * 25))
        for sz, a in [(cr * 2, 50), (cr, 110), (cr // 2, 220)]:
            s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.col, a), (sz, sz), sz)
            surf.blit(s, (int(self.x) - sz, int(self.y) - sz))


# ─────────────────────────────────────────────
#  BOTÓN
# ─────────────────────────────────────────────

class Button:
    def __init__(self, rect, text, font, bc=(20, 35, 65),
                 hc=(0, 150, 220), tc=None, bdc=None, r=10):
        self.rect = pygame.Rect(rect)
        self.text = text; self.font = font
        self.bc = bc; self.hc = hc
        self.tc = tc or C["text"]
        self.bdc = bdc or C["border"]
        self.r = r; self.hov = False; self.sc = 1.0

    def update(self, mp, dt):
        self.hov = self.rect.collidepoint(mp)
        self.sc  = lerp(self.sc, 1.06 if self.hov else 1.0, 0.15)

    def draw(self, surf):
        sw = int(self.rect.w * self.sc); sh = int(self.rect.h * self.sc)
        rx = self.rect.centerx - sw // 2; ry = self.rect.centery - sh // 2
        r  = pygame.Rect(rx, ry, sw, sh)
        draw_panel(surf, r, color=self.hc if self.hov else self.bc,
                   alpha=240, border=self.bdc if self.hov else (40, 70, 120),
                   bw=3 if self.hov else 1, radius=self.r)
        draw_text(surf, self.text, self.font, self.tc, center=r.center)

    def is_clicked(self, ev):
        return (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                and self.rect.collidepoint(ev.pos))


# ─────────────────────────────────────────────
#  ESTADO BASE
# ─────────────────────────────────────────────

class State:
    def __init__(self, game): self.game = game
    def on_enter(self): pass
    def handle(self, ev): pass
    def update(self, dt): pass
    def draw(self, surf): pass


# ─────────────────────────────────────────────
#  MENÚ PRINCIPAL
# ─────────────────────────────────────────────

class MenuState(State):
    def __init__(self, game):
        super().__init__(game)
        self.bg  = load_img("menu_bg.jpg", (W, H))
        self.ov  = pygame.Surface((W, H), pygame.SRCALPHA)
        self.ov.fill((0, 0, 0, 150))
        self.t   = 0.0; self.fx = FX()
        self.stars = [(random.randint(0, W), random.randint(0, H),
                       random.uniform(0.3, 2.0)) for _ in range(160)]
        bw, bh = 340, 62; cx = W // 2 - bw // 2
        self.btns = [
            Button((cx, H // 2 + 10,  bw, bh), "⚔  JUGAR",        game.F.md,
                   bc=(20, 50, 120), hc=(0, 120, 230)),
            Button((cx, H // 2 + 84,  bw, bh), "🏆  CLASIFICACIÓN", game.F.md),
            Button((cx, H // 2 + 158, bw, bh), "🚪  SALIR",         game.F.md,
                   bc=(60, 15, 15), hc=(160, 25, 25)),
        ]
        # Cargar previews de personajes pequeños para el fondo
        self._load_char_previews()

    def _load_char_previews(self):
        self.previews = []
        for cd in CHARACTERS:
            try:
                img = load_sprite(cd.sprite, (90, 130), cd.bg_white)
                self.previews.append((img, cd.color))
            except Exception:
                self.previews.append((None, cd.color))

    def handle(self, ev):
        if self.btns[0].is_clicked(ev): self.game.push(NameState(self.game))
        if self.btns[1].is_clicked(ev): self.game.push(LeaderState(self.game))
        if self.btns[2].is_clicked(ev): pygame.quit(); sys.exit()

    def update(self, dt):
        self.t += dt
        for b in self.btns: b.update(pygame.mouse.get_pos(), dt)
        if random.random() < 0.2:
            self.fx.emit(random.randint(80, W - 80), H + 5,
                         random.choice([CHARACTERS[0].color, C["gold"], (180, 60, 255)]),
                         n=1, vy=random.uniform(-1.8, -0.3),
                         vx=random.uniform(-0.3, 0.3), life=5.0, size=2)
        self.fx.update(dt)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0)); surf.blit(self.ov, (0, 0))
        # Estrellitas
        for sx, sy, br in self.stars:
            a = int(pulse(self.t + sx * .01, spd=br) * 180)
            r = 1 + (br > 1.2)
            s = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 255, a), (r, r), r)
            surf.blit(s, (sx, sy))
        # Personajes decorativos en el fondo
        for i, (img, col) in enumerate(self.previews):
            if img is None: continue
            x = 80 + i * 195
            y = H - 150 + int(math.sin(self.t * 1.2 + i * 0.8) * 8)
            glow_r = 60
            gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*col, 25), (glow_r, glow_r), glow_r)
            surf.blit(gs, (x + 45 - glow_r, y + 65 - glow_r))
            img_a = img.copy(); img_a.set_alpha(140)
            surf.blit(img_a, (x, y))
        self.fx.draw(surf)
        # Título
        ty = H // 2 - 175
        for off in [20, 12, 5]:
            gl = self.game.F.title.render("MECHA  ARENA", True,
                                          (0, int(150 * off / 20), int(255 * off / 20)))
            gl.set_alpha(30); surf.blit(gl, gl.get_rect(center=(W // 2 + off, ty + off)))
        draw_text(surf, "MECHA  ARENA", self.game.F.title, (0, 200, 255), center=(W // 2, ty))
        a = int(pulse(self.t, 1.5, 100, 255))
        sb = self.game.F.sm.render("⚙  SIMULADOR DE ROBOTS & COMBATE TÁCTICO  ⚙", True, C["gold"])
        sb.set_alpha(a); surf.blit(sb, sb.get_rect(center=(W // 2, ty + 78)))
        for b in self.btns: b.draw(surf)
        vr = self.game.F.xs.render("v5.0 — Character Select + Real Fighter", True, C["dim"])
        surf.blit(vr, (12, H - 26))


# ─────────────────────────────────────────────
#  INGRESO DE NOMBRE
# ─────────────────────────────────────────────

class NameState(State):
    def __init__(self, game):
        super().__init__(game)
        self.bg  = load_img("menu_bg.jpg", (W, H))
        self.ov  = pygame.Surface((W, H), pygame.SRCALPHA); self.ov.fill((0, 0, 0, 165))
        self.name = ""; self.err = ""; self.t = 0.0
        self.btn_ok   = Button((W // 2 - 155, H // 2 + 70, 310, 58), "CONFIRMAR →", game.F.md)
        self.btn_back = Button((W // 2 - 155, H // 2 + 140, 310, 46), "← VOLVER", game.F.sm,
                               hc=(90, 20, 20))

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_BACKSPACE: self.name = self.name[:-1]; self.err = ""
            elif ev.key == pygame.K_RETURN:  self._confirm()
            elif ev.key == pygame.K_ESCAPE:  self.game.pop()
            elif len(self.name) < 16 and ev.unicode.isprintable():
                self.name += ev.unicode; self.err = ""
        if self.btn_ok.is_clicked(ev):   self._confirm()
        if self.btn_back.is_clicked(ev): self.game.pop()

    def _confirm(self):
        n = self.name.strip()
        if not n: self.err = "¡El nombre no puede estar vacío!"; return
        self.game.player_name = n
        try:
            if n not in [p.nombre for p in self.game.svc.obtener_pilotos()]:
                self.game.svc.registrar_piloto(n)
        except Exception: pass
        self.game.push(CharSelectState(self.game))

    def update(self, dt):
        self.t += dt
        mp = pygame.mouse.get_pos()
        self.btn_ok.update(mp, dt); self.btn_back.update(mp, dt)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0)); surf.blit(self.ov, (0, 0))
        draw_text(surf, "INGRESA TU NOMBRE DE PILOTO",
                  self.game.F.lg, (0, 200, 255), center=(W // 2, H // 2 - 130))
        box = pygame.Rect(W // 2 - 250, H // 2 - 32, 500, 58)
        bc  = C["border"] if self.t % 1 < 0.6 else C["gold"]
        draw_panel(surf, box, (8, 18, 48), 220, bc, 2)
        draw_text(surf, self.name + ("|" if self.t % 1 < 0.5 else " "),
                  self.game.F.md, C["white"], topleft=(box.x + 14, box.y + 14))
        if self.err:
            draw_text(surf, self.err, self.game.F.sm, C["red"], center=(W // 2, H // 2 + 40))
        self.btn_ok.draw(surf); self.btn_back.draw(surf)


# ─────────────────────────────────────────────
#  SELECCIÓN DE PERSONAJE ★★★
# ─────────────────────────────────────────────

class CharSelectState(State):
    CARD_W, CARD_H = 175, 210
    COLS = 3

    def __init__(self, game):
        super().__init__(game)
        self.bg   = load_img("menu_bg.jpg", (W, H))
        self.ov   = pygame.Surface((W, H), pygame.SRCALPHA); self.ov.fill((0, 0, 0, 160))
        self.t    = 0.0
        self.sel  = 0                                    # índice seleccionado
        self.ai_sel = random.randint(0, len(CHARACTERS) - 1)
        self.fx   = FX()

        # Cargar sprites grandes para preview
        self.sprites_lg : List[pygame.Surface] = []
        for cd in CHARACTERS:
            try:
                img = load_sprite(cd.sprite, (260, 360), cd.bg_white)
            except Exception:
                img = pygame.Surface((260, 360), pygame.SRCALPHA)
            self.sprites_lg.append(img)

        # Cargar sprites pequeños para las tarjetas
        self.sprites_sm : List[pygame.Surface] = []
        for cd in CHARACTERS:
            try:
                img = load_sprite(cd.sprite, (120, 160), cd.bg_white)
            except Exception:
                img = pygame.Surface((120, 160), pygame.SRCALPHA)
            self.sprites_sm.append(img)

        self._build_cards()
        self.btn_fight = Button(
            (W // 2 - 175, H - 72, 350, 56),
            "⚔  ¡A COMBATIR!", game.F.md,
            bc=(100, 15, 15), hc=(200, 25, 25))
        self.btn_back = Button(
            (24, H - 68, 160, 44), "← VOLVER", game.F.sm, hc=(60, 15, 15))

    def _build_cards(self):
        """Calcular rectángulos de cada tarjeta en la cuadrícula."""
        self.cards: List[pygame.Rect] = []
        n = len(CHARACTERS)
        cols = self.COLS
        rows = (n + cols - 1) // cols
        grid_w = cols * self.CARD_W + (cols - 1) * 12
        grid_h = rows * self.CARD_H + (rows - 1) * 12
        ox = W // 2 - grid_w // 2 + 120   # desplazado a la derecha (panel preview a izquierda)
        oy = H // 2 - grid_h // 2 + 20
        for i in range(n):
            row, col = divmod(i, cols)
            x = ox + col * (self.CARD_W + 12)
            y = oy + row * (self.CARD_H + 12)
            self.cards.append(pygame.Rect(x, y, self.CARD_W, self.CARD_H))

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_LEFT:   self.sel = (self.sel - 1) % len(CHARACTERS)
            if ev.key == pygame.K_RIGHT:  self.sel = (self.sel + 1) % len(CHARACTERS)
            if ev.key == pygame.K_UP:     self.sel = (self.sel - self.COLS) % len(CHARACTERS)
            if ev.key == pygame.K_DOWN:   self.sel = (self.sel + self.COLS) % len(CHARACTERS)
            if ev.key in (pygame.K_RETURN, pygame.K_z): self._confirm()
            if ev.key == pygame.K_ESCAPE: self.game.pop()
        for i, rect in enumerate(self.cards):
            if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                    and rect.collidepoint(ev.pos)):
                if self.sel == i:
                    self._confirm()
                else:
                    self.sel = i
        if self.btn_fight.is_clicked(ev): self._confirm()
        if self.btn_back.is_clicked(ev): self.game.pop()

    def _confirm(self):
        self.game.player_char = CHARACTERS[self.sel]
        # IA elige random (distinto al jugador)
        choices = [i for i in range(len(CHARACTERS)) if i != self.sel]
        self.game.ai_char = CHARACTERS[random.choice(choices)]
        self.game.push(FightingState(self.game))

    def update(self, dt):
        self.t += dt
        mp = pygame.mouse.get_pos()
        self.btn_fight.update(mp, dt)
        self.btn_back.update(mp, dt)
        # Hover highlight
        for i, rect in enumerate(self.cards):
            if rect.collidepoint(mp) and i != self.sel:
                pass  # hover handled in draw
        # Partículas del personaje seleccionado
        cd = CHARACTERS[self.sel]
        if random.random() < 0.15:
            self.fx.emit(160, 400, cd.color, n=1,
                         vy=random.uniform(-2, -0.5), vx=random.uniform(-1, 1),
                         life=1.2, size=4)
        self.fx.update(dt)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0)); surf.blit(self.ov, (0, 0))

        cd = CHARACTERS[self.sel]

        # ── Panel izquierdo: preview grande ──
        draw_panel(surf, pygame.Rect(8, 8, 310, H - 16),
                   border=cd.color, radius=14)
        draw_text(surf, cd.name, self.game.F.lg, cd.color, center=(163, 40))
        draw_text(surf, f"[{cd.arch}]", self.game.F.sm, cd.color, center=(163, 68))

        # Glow detrás del sprite
        glow_r = 130 + int(20 * math.sin(self.t * 2))
        gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*cd.color, 18), (glow_r, glow_r), glow_r)
        surf.blit(gs, (163 - glow_r, 250 - glow_r))

        # Sprite grande
        img = self.sprites_lg[self.sel]
        bob = int(math.sin(self.t * 2) * 8)
        surf.blit(img, (163 - img.get_width() // 2, 85 + bob))

        self.fx.draw(surf)

        # Stats
        stats = [
            ("ATK", cd.atk, 90, C["red"]),
            ("DEF", cd.dfn, 50, (0, 200, 255)),
            ("HP",  cd.hp // 3, 100, (0, 220, 80)),
            ("VEL", int(cd.spd * 50), 80, C["gold"]),
        ]
        sy = 490
        for lbl, val, mx, col in stats:
            draw_text(surf, lbl, self.game.F.sm, C["dim"], topleft=(18, sy))
            draw_stat_bar(surf, 70, sy + 4, 220, 14, val, mx, col)
            draw_text(surf, str(val), self.game.F.xs, col, topleft=(298, sy))
            sy += 32

        draw_text(surf, cd.desc, self.game.F.xs, C["text"], center=(163, 648))

        # ── Título ──────────────────────────
        draw_text(surf, "ELIGE TU LUCHADOR", self.game.F.lg, C["gold"],
                  center=(W // 2 + 120, 28))

        # ── Tarjetas de personajes ───────────
        mp = pygame.mouse.get_pos()
        for i, (rect, spr) in enumerate(zip(self.cards, self.sprites_sm)):
            ch   = CHARACTERS[i]
            sel  = (i == self.sel)
            hov  = rect.collidepoint(mp)
            bc   = ch.color if sel else ((50, 70, 120) if hov else (20, 30, 55))
            bw   = 3 if sel else (2 if hov else 1)
            draw_panel(surf, rect, color=bc, alpha=200,
                       border=ch.color if sel else (60, 90, 140), bw=bw, radius=10)

            # Sprite pequeño centrado en la tarjeta
            sx = rect.centerx - spr.get_width() // 2
            sy = rect.y + 8
            surf.blit(spr, (sx, sy))

            # Nombre
            draw_text(surf, ch.name, self.game.F.xs, ch.color if sel else C["text"],
                      center=(rect.centerx, rect.bottom - 26))
            draw_text(surf, ch.arch, self.game.F.xs, C["dim"] if not sel else C["gold"],
                      center=(rect.centerx, rect.bottom - 10))

            # Borde de selección animado
            if sel:
                aw = int(1 + 2 * abs(math.sin(self.t * 4)))
                pygame.draw.rect(surf, ch.color, rect, aw, border_radius=10)

        # ── IA preview (esquina) ─────────────
        ai_cd = CHARACTERS[self.ai_sel]
        draw_panel(surf, pygame.Rect(W - 200, H - 150, 190, 140),
                   border=ai_cd.color, radius=10)
        draw_text(surf, "RIVAL (IA)", self.game.F.xs, C["dim"], center=(W - 105, H - 138))
        ai_img = self.sprites_sm[self.ai_sel]
        surf.blit(ai_img, (W - 165, H - 130))
        draw_text(surf, ai_cd.name, self.game.F.sm, ai_cd.color, center=(W - 105, H - 30))
        # Dado de azar animado
        a_t = int(pulse(self.t, 3, 80, 255))
        rd  = self.game.F.xs.render("?? aleatorio ??", True, C["dim"])
        rd.set_alpha(a_t); surf.blit(rd, rd.get_rect(center=(W - 105, H - 15)))

        self.btn_fight.draw(surf)
        self.btn_back.draw(surf)
        draw_text(surf, "← → ↑ ↓ para navegar  |  ENTER / Z para seleccionar",
                  self.game.F.xs, C["dim"], center=(W // 2 + 120, H - 78))


# ─────────────────────────────────────────────
#  FIGHTER STATE MACHINE
# ─────────────────────────────────────────────

class FS(Enum):
    IDLE   = auto()
    WALKL  = auto()
    WALKR  = auto()
    JUMP   = auto()
    ATTACK = auto()
    HEAVY  = auto()
    SPECIAL= auto()
    BLOCK  = auto()
    HIT    = auto()
    DASH   = auto()
    KO     = auto()

ATK_DATA = {
    FS.ATTACK:  dict(a_start=0.13, a_end=0.22, total=0.37, mult=0.30, rng=155, erg=8,  cost=0),
    FS.HEAVY:   dict(a_start=0.23, a_end=0.38, total=0.65, mult=0.62, rng=168, erg=15, cost=0),
    FS.SPECIAL: dict(a_start=0.15, a_end=0.55, total=0.85, mult=1.10, rng=600, erg=0,  cost=100),
}


class Fighter:
    SW, SH = 210, 300

    def __init__(self, x: float, char: CharDef, flip=False):
        self.x, self.y  = float(x), float(GROUND_Y)
        self.vx = self.vy = 0.0
        self.char    = char
        self.color   = char.color
        self.name    = char.name
        self.facing  = 1 if not flip else -1
        self.flip    = flip
        self.on_ground = True
        self.state   = FS.IDLE
        self.timer   = 0.0
        self.t       = 0.0
        self.atk     = char.atk
        self.dfn     = char.dfn
        self.hp_max  = char.hp
        self.hp      = char.hp
        self.spd     = char.spd
        self.energy  = 0.0
        self.combo   = 0
        self.combo_t = 0.0
        self.flash   = 0.0
        self.img_base: Optional[pygame.Surface] = None
        self.sprites: dict = {}
        self._hit_this_swing = False
        self._proj_spawned   = False

    def set_image(self, surf: pygame.Surface):
        self.img_base = surf
        self.sprites[FS.IDLE] = surf

    def set_action_sprite(self, state: FS, surf: pygame.Surface):
        self.sprites[state] = surf

    def _can_act(self):
        return self.state in (FS.IDLE, FS.WALKL, FS.WALKR, FS.JUMP)

    def jump(self):
        if self.on_ground and self._can_act():
            self.vy = JUMP_VY; self.on_ground = False

    def move_left(self):
        if self.state in (FS.IDLE, FS.WALKL, FS.WALKR, FS.JUMP):
            self.vx = -WALK_SPD * self.spd
            if self.on_ground: self.state = FS.WALKL

    def move_right(self):
        if self.state in (FS.IDLE, FS.WALKL, FS.WALKR, FS.JUMP):
            self.vx = WALK_SPD * self.spd
            if self.on_ground: self.state = FS.WALKR

    def block(self):
        if self.on_ground and self.state in (FS.IDLE, FS.WALKL, FS.WALKR, FS.BLOCK):
            self.state = FS.BLOCK; self.vx = 0

    def unblock(self):
        if self.state == FS.BLOCK:
            self.state = FS.IDLE

    def dash(self):
        if self._can_act() and self.on_ground:
            self.vx = DASH_SPD * self.facing * self.spd
            self.state = FS.DASH; self.timer = DASH_DUR

    def do_attack(self, kind: FS) -> bool:
        if kind not in ATK_DATA: return False
        d = ATK_DATA[kind]
        if d["cost"] > 0 and self.energy < d["cost"]: return False
        if not self._can_act(): return False
        if d["cost"] > 0: self.energy = max(0, self.energy - d["cost"])
        self.state = kind; self.timer = d["total"]
        self._hit_this_swing = False; self._proj_spawned = False
        return True

    def hitbox_active(self) -> bool:
        if self.state not in ATK_DATA: return False
        d = ATK_DATA[self.state]
        elapsed = d["total"] - self.timer
        return d["a_start"] <= elapsed <= d["a_end"]

    def hitbox_rect(self):
        if not self.hitbox_active(): return None
        if self.state == FS.SPECIAL: return None
        rng = ATK_DATA[self.state]["rng"]
        cx  = self.x + self.facing * (self.SW // 2 + 20)
        y   = int(self.y) - self.SH + 50
        if self.facing == 1:
            return pygame.Rect(int(cx), y, rng, self.SH - 50)
        else:
            return pygame.Rect(int(cx - rng), y, rng, self.SH - 50)

    def can_spawn_projectile(self) -> bool:
        if self.state != FS.SPECIAL: return False
        d = ATK_DATA[FS.SPECIAL]
        elapsed = d["total"] - self.timer
        return abs(elapsed - d["a_start"]) < 0.04

    def take_damage(self, raw: int, push_dir: int) -> int:
        if self.state == FS.KO: return 0
        actual = max(1, int(raw * (1 - min(0.5, self.dfn / 200))))
        if self.state == FS.BLOCK:
            actual = max(1, actual // 6)
            self.vx = push_dir * 3
        else:
            self.vx = push_dir * 4
            self.state = FS.HIT; self.timer = 0.30
        self.hp = max(0, self.hp - actual)
        self.flash = 1.0
        self.flash_col = (255, 80, 80) if self.state != FS.BLOCK else (100, 150, 255)
        if self.hp <= 0: self.state = FS.KO; self.timer = 999
        return actual

    def update(self, dt, lw, rw):
        self.t     += dt
        self.timer  = max(0, self.timer - dt)
        self.flash  = max(0, self.flash - dt * 6)
        if self.combo_t > 0: self.combo_t -= dt
        else: self.combo = 0
        self.energy = min(100, self.energy + 4 * dt)

        if not self.on_ground: self.vy += GRAVITY * dt * 60
        if self.state in (FS.IDLE, FS.HIT, FS.ATTACK, FS.HEAVY, FS.SPECIAL, FS.BLOCK, FS.KO):
            self.vx *= 0.80
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        if self.y >= GROUND_Y:
            self.y = GROUND_Y; self.vy = 0; self.on_ground = True
        self.x = max(lw, min(rw, self.x))
        if self.timer <= 0 and self.state not in (
                FS.IDLE, FS.WALKL, FS.WALKR, FS.JUMP, FS.BLOCK, FS.KO):
            self.state = FS.IDLE
        if self.on_ground and self.state in (FS.WALKL, FS.WALKR) and abs(self.vx) < 0.5:
            self.state = FS.IDLE
        if not self.on_ground and self.state not in (FS.JUMP, FS.ATTACK, FS.HEAVY,
                                                      FS.SPECIAL, FS.KO):
            self.state = FS.JUMP

    def draw(self, surf):
        img_to_use = self.sprites.get(self.state, self.img_base)
        if img_to_use is None:
            img_to_use = self.img_base
        if img_to_use is None: return
        img = img_to_use.copy()

        should_flip = (self.facing == -1) != self.flip
        if should_flip: img = pygame.transform.flip(img, True, False)

        ox = oy = 0
        if self.state == FS.IDLE:
            oy = int(math.sin(self.t * 2.0) * 5)
        elif self.state in (FS.WALKL, FS.WALKR):
            oy = int(abs(math.sin(self.t * 8)) * 7)
            ox = self.facing * int(math.sin(self.t * 8) * 5)
        elif self.state in (FS.ATTACK, FS.HEAVY):
            # Movimiento dinámico de estocada / golpe hacia adelante
            if self.hitbox_active():
                ox = self.facing * 32
                img = pygame.transform.smoothscale(img, (int(self.SW * 1.06), self.SH))
            else:
                ox = self.facing * 14
        elif self.state == FS.SPECIAL and self.hitbox_active():
            sx = 1.0 + 0.08 * math.sin(self.t * 30)
            img = pygame.transform.smoothscale(img, (int(self.SW * sx), int(self.SH * sx)))
        elif self.state == FS.HIT:
            ox = int(math.sin(self.t * 40) * 8)
            oy = -6
        elif self.state == FS.BLOCK:
            img = pygame.transform.smoothscale(img, (int(self.SW * 0.95), int(self.SH * 0.95)))
            tint = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            tint.fill((0, 180, 255, 50))
            img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        elif self.state == FS.KO:
            img = pygame.transform.rotate(img, -75)
            oy = 45

        if self.flash > 0:
            fl = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            fl.fill((*self.flash_col, int(self.flash * 180)))
            img.blit(fl, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # Glow aura
        gr = 80 + int(20 * math.sin(self.t * 3))
        gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*self.color, 28), (gr, gr), gr)
        surf.blit(gs, (int(self.x) - gr + ox, int(self.y) - self.SH // 2 + oy - gr // 2))

        surf.blit(img, (int(self.x) - img.get_width() // 2 + ox,
                        int(self.y) - img.get_height() + oy))

    def draw_shadow(self, surf):
        sx, sy = int(self.x), int(self.y) + 5
        s = pygame.Surface((160, 26), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 70), s.get_rect())
        surf.blit(s, (sx - 80, sy - 13))


# ─────────────────────────────────────────────
#  IA
# ─────────────────────────────────────────────

class AIController:
    def __init__(self):
        self.react_t = 0.0
        self.aggro   = random.uniform(0.55, 0.88)

    def update(self, ai, player, dt, projectiles):
        if ai.state == FS.KO or ai.state in ATK_DATA: return 0, False, False, None
        self.react_t -= dt
        dist    = player.x - ai.x
        abs_d   = abs(dist)
        toward  = 1 if dist > 0 else -1
        hp_r    = ai.hp / ai.hp_max

        for p in projectiles:
            if p.alive and abs(p.x - ai.x) < 320 and (p.x - ai.x) * p.vx < 0:
                if random.random() < 0.65:
                    return 0, True, False, None

        if hp_r < 0.22 and abs_d < 220 and random.random() < 0.45:
            return 0, False, True, None

        if self.react_t > 0:
            return (WALK_SPD * toward if abs_d > 220 else 0), False, False, None
        self.react_t = random.uniform(0.10, 0.30) / self.aggro

        if abs_d > 430:
            return (0 if random.random() < 0.35 else WALK_SPD * toward), \
                   False, False, (FS.DASH if random.random() < 0.35 else None)
        if abs_d > 200:
            return WALK_SPD * toward, False, False, \
                   (FS.SPECIAL if ai.energy >= 100 and random.random() < 0.25 else None)

        r = random.random()
        if r < 0.40: return 0, False, False, FS.ATTACK
        if r < 0.65: return 0, False, False, FS.HEAVY
        if r < 0.75 and ai.energy >= 100: return 0, False, False, FS.SPECIAL
        if r < 0.85: return 0, False, True,  None
        return 0, True, False, FS.ATTACK


# ─────────────────────────────────────────────
#  FASE DE PELEA
# ─────────────────────────────────────────────

class FP(Enum):
    INTRO    = auto()
    FIGHT    = auto()
    KO_SLOW  = auto()
    ROUND_END= auto()
    MATCH_END= auto()


class FightingState(State):
    MAX_ROUNDS = 3
    ROUND_TIME = 90.0

    def __init__(self, game):
        super().__init__(game)
        self.bg    = load_img("arena_bg.jpg", (W, H))
        pc = game.player_char
        ac = game.ai_char

        # Sprites con fondo transparente y poses por acción
        def setup_fighter_sprites(fighter: Fighter, cd: CharDef):
            base_img = load_sprite(cd.sprite, (Fighter.SW, Fighter.SH), cd.bg_white)
            fighter.set_image(base_img)
            if cd.name == "GUARDIAN":
                try:
                    atk_img = load_sprite("char_guardian_atk.jpg", (Fighter.SW, Fighter.SH), cd.bg_white)
                    blk_img = load_sprite("char_guardian_blk.jpg", (Fighter.SW, Fighter.SH), cd.bg_white)
                    hit_img = load_sprite("char_guardian_hit.jpg", (Fighter.SW, Fighter.SH), cd.bg_white)
                    fighter.set_action_sprite(FS.ATTACK, atk_img)
                    fighter.set_action_sprite(FS.HEAVY, atk_img)
                    fighter.set_action_sprite(FS.SPECIAL, atk_img)
                    fighter.set_action_sprite(FS.BLOCK, blk_img)
                    fighter.set_action_sprite(FS.HIT, hit_img)
                except Exception:
                    pass

        self.player = Fighter(220,  pc, flip=False)
        setup_fighter_sprites(self.player, pc)
        self.ai     = Fighter(1060, ac, flip=True)
        setup_fighter_sprites(self.ai, ac)
        self.player.facing =  1
        self.ai.facing     = -1

        self.ai_ctrl   = AIController()
        self.projectiles: List[Projectile] = []
        self.fx        = FX()
        self.hit_nums  : List[HitNumber]   = []
        self.shake     = 0.0
        self.t         = 0.0

        self.phase       = FP.INTRO
        self.phase_timer = 2.5
        self.round_num   = 1
        self.round_timer = self.ROUND_TIME
        self.p_wins      = 0
        self.ai_wins     = 0
        self.slow_f      = 1.0
        self.round_result_txt = ""
        self.btn_menu = Button((W // 2 - 150, H - 64, 300, 48),
                               "← MENÚ PRINCIPAL", game.F.sm)

        # Menú de Pausa
        self.paused = False
        cx = W // 2 - 150
        self.btn_resume  = Button((cx, H // 2 - 40, 300, 48), "▶  CONTINUAR", game.F.sm,
                                  bc=(20, 50, 110), hc=(0, 140, 230))
        self.btn_restart = Button((cx, H // 2 + 18, 300, 48), "🔄  REINICIAR PELEA", game.F.sm,
                                  bc=(25, 45, 80), hc=(0, 120, 200))
        self.btn_quit    = Button((cx, H // 2 + 76, 300, 48), "🚪  VOLVER AL MENÚ", game.F.sm,
                                  bc=(60, 15, 15), hc=(160, 25, 25))

    # ── Colisiones ──────────────────────────

    def _check_hit(self, attacker: Fighter, defender: Fighter):
        if not attacker.hitbox_active() or attacker.state == FS.SPECIAL: return
        hb = attacker.hitbox_rect()
        if hb is None: return
        dr = pygame.Rect(int(defender.x) - 60, int(defender.y) - defender.SH + 20,
                         120, defender.SH - 20)
        if not hb.colliderect(dr): return
        if attacker._hit_this_swing: return
        attacker._hit_this_swing = True
        d    = ATK_DATA[attacker.state]
        raw  = int(attacker.atk * d["mult"] * random.uniform(0.9, 1.12))
        push = attacker.facing
        dealt = defender.take_damage(raw, push)
        attacker.energy = min(100, attacker.energy + d["erg"])
        attacker.combo += 1; attacker.combo_t = 2.0
        crit = random.random() < 0.15
        col  = C["gold"] if crit else attacker.color
        cx   = int((attacker.x + defender.x) / 2)
        cy   = int(defender.y) - defender.SH // 2
        self.hit_nums.append(HitNumber(cx, cy,
            f"{'CRÍTICO! ' if crit else ''}-{dealt}", col, big=crit))
        self.fx.emit(cx, cy, attacker.color, n=18, size=6)
        self.shake = 0.35 if attacker.state == FS.HEAVY else 0.22
        if not attacker._hit_this_swing:
            attacker._hit_this_swing = True

    def _reset_hit_flag(self, f: Fighter):
        if not f.hitbox_active(): f._hit_this_swing = False

    def _try_projectile(self, f: Fighter):
        if f.state != FS.SPECIAL or f._proj_spawned: return
        if not f.can_spawn_projectile(): return
        f._proj_spawned = True
        cx  = f.x + f.facing * 80
        cy  = f.y - f.SH * 0.55
        dmg = int(f.atk * ATK_DATA[FS.SPECIAL]["mult"] * random.uniform(0.9, 1.1))
        self.projectiles.append(Projectile(cx, cy, f.facing, dmg, f.color))
        self.fx.emit(int(cx), int(cy), f.color, n=22, size=8,
                     vy=-2, vx=f.facing * 3)

    def _proj_hits(self):
        for proj in self.projectiles:
            if not proj.alive: continue
            for target, owner in [(self.player, self.ai.name),
                                   (self.ai,    self.player.name)]:
                if proj not in self.projectiles: continue
                tr = pygame.Rect(int(target.x) - 55, int(target.y) - target.SH + 20,
                                 110, target.SH - 20)
                pr = pygame.Rect(int(proj.x) - proj.r, int(proj.y) - proj.r,
                                 proj.r * 2, proj.r * 2)
                if pr.colliderect(tr):
                    push = 1 if proj.vx > 0 else -1
                    d    = target.take_damage(proj.damage, push)
                    proj.alive = False
                    self.hit_nums.append(HitNumber(int(proj.x), int(proj.y),
                                                   f"-{d}", proj.col, big=True))
                    self.fx.emit(int(proj.x), int(proj.y), proj.col, n=28, size=8)
                    self.shake = 0.5; break

    def _check_round_end(self):
        pd = (self.player.state == FS.KO)
        ad = (self.ai.state == FS.KO)
        tu = (self.round_timer <= 0)
        if not (pd or ad or tu): return
        if self.phase == FP.KO_SLOW: return
        if pd or (tu and self.player.hp < self.ai.hp):
            self.ai_wins += 1; self.round_result_txt = f"¡{AI_NAME} WINS!"
        elif ad or (tu and self.ai.hp < self.player.hp):
            self.p_wins  += 1; self.round_result_txt = f"¡{self.game.player_name} WINS!"
        else:
            self.round_result_txt = "EMPATE"
        self.phase = FP.KO_SLOW; self.phase_timer = 1.8; self.slow_f = 0.15

    # ── Handle ──────────────────────────────

    def handle(self, ev):
        if self.phase == FP.MATCH_END:
            if self.btn_menu.is_clicked(ev):
                won = self.p_wins > self.ai_wins
                self.game.push(ResultState(self.game, won, self.p_wins, self.ai_wins,
                                           self.round_num))
                return

        # Pausar / Despausar con tecla P o ESC
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_p, pygame.K_ESCAPE):
            if self.phase in (FP.FIGHT, FP.INTRO):
                self.paused = not self.paused
                return

        # Interacción mientras el juego está en pausa
        if self.paused:
            if self.btn_resume.is_clicked(ev):
                self.paused = False
            elif self.btn_restart.is_clicked(ev):
                self.paused = False
                self.p_wins = 0
                self.ai_wins = 0
                self.round_num = 1
                self._reset_round()
                self.phase = FP.INTRO
                self.phase_timer = 2.0
            elif self.btn_quit.is_clicked(ev):
                self.game.pop()
            return

        if self.phase != FP.FIGHT: return
        if ev.type == pygame.KEYDOWN:
            k = ev.key
            if k == pygame.K_z:
                self.player.do_attack(FS.ATTACK)
            if k == pygame.K_x:
                self.player.do_attack(FS.HEAVY)
            if k == pygame.K_c:
                self.player.do_attack(FS.SPECIAL)
            if k == pygame.K_a:
                self.player.dash()
            if k in (pygame.K_UP, pygame.K_SPACE):
                self.player.jump()

    # ── Update ──────────────────────────────

    def update(self, dt):
        if self.paused:
            mp = pygame.mouse.get_pos()
            self.btn_resume.update(mp, dt)
            self.btn_restart.update(mp, dt)
            self.btn_quit.update(mp, dt)
            return

        self.t += dt
        sf = self.slow_f

        # Phase transitions
        if self.phase == FP.INTRO:
            self.phase_timer -= dt
            if self.phase_timer <= 0: self.phase = FP.FIGHT
        elif self.phase == FP.KO_SLOW:
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                self.slow_f = 1.0; self.phase = FP.ROUND_END; self.phase_timer = 2.5
        elif self.phase == FP.ROUND_END:
            self.phase_timer -= dt
            if self.phase_timer <= 0:
                if (self.p_wins + self.ai_wins >= self.MAX_ROUNDS
                        or self.p_wins > self.MAX_ROUNDS // 2
                        or self.ai_wins > self.MAX_ROUNDS // 2):
                    self.phase = FP.MATCH_END
                else:
                    self._reset_round()
                    self.round_num += 1
                    self.phase = FP.INTRO; self.phase_timer = 2.0
        elif self.phase == FP.MATCH_END:
            self.btn_menu.update(pygame.mouse.get_pos(), dt)
            self.fx.update(dt * sf)
            if self.p_wins > self.ai_wins and random.random() < 0.25:
                self.fx.emit(random.randint(0, W), -8, C["gold"],
                             n=1, vy=3.5, vx=random.uniform(-1, 1), life=5.0, size=5)
            return

        if self.phase not in (FP.FIGHT, FP.KO_SLOW): return

        # Input jugador
        if self.phase == FP.FIGHT:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN]:
                self.player.block()
            else:
                self.player.unblock()
                if keys[pygame.K_LEFT]:
                    self.player.move_left(); self.player.facing = -1
                elif keys[pygame.K_RIGHT]:
                    self.player.move_right(); self.player.facing = 1
                else:
                    if self.player.state in (FS.WALKL, FS.WALKR) and self.player.on_ground:
                        self.player.state = FS.IDLE
            self.round_timer = max(0, self.round_timer - dt)

        # IA
        if self.ai.state != FS.KO:
            vx, do_jump, do_block, attack = self.ai_ctrl.update(
                self.ai, self.player, dt * sf, self.projectiles)
            if do_jump:
                self.ai.unblock()
                self.ai.jump()
            elif do_block:
                self.ai.block()
            else:
                self.ai.unblock()
                if abs(vx) > 0.1:
                    if vx < 0: self.ai.move_left();  self.ai.facing = -1
                    else:      self.ai.move_right(); self.ai.facing =  1
                elif self.ai.on_ground and self.ai.state in (FS.WALKL, FS.WALKR):
                    self.ai.state = FS.IDLE
            if attack and self.ai._can_act(): self.ai.do_attack(attack)

        # Facing dinámico
        if self.player.state not in (FS.ATTACK, FS.HEAVY, FS.SPECIAL, FS.DASH, FS.HIT):
            self.player.facing = 1 if self.ai.x > self.player.x else -1
        if self.ai.state not in (FS.ATTACK, FS.HEAVY, FS.SPECIAL, FS.DASH, FS.HIT):
            self.ai.facing = 1 if self.player.x > self.ai.x else -1

        # Física
        lw, rw = 60, W - 60
        self.player.update(dt * sf, lw, rw)
        self.ai.update(dt * sf, lw, rw)

        # Push
        dx = self.ai.x - self.player.x
        if abs(dx) < PUSH_DIST:
            push = (PUSH_DIST - abs(dx)) / 2
            sign = 1 if dx >= 0 else -1
            self.player.x = max(lw, min(rw, self.player.x - push * sign))
            self.ai.x     = max(lw, min(rw, self.ai.x     + push * sign))

        # Colisiones
        self._reset_hit_flag(self.player); self._reset_hit_flag(self.ai)
        self._check_hit(self.player, self.ai); self._check_hit(self.ai, self.player)
        self._try_projectile(self.player);     self._try_projectile(self.ai)
        for proj in self.projectiles: proj.update(dt * sf)
        self.projectiles = [p for p in self.projectiles if p.alive]
        self._proj_hits()

        # FX
        self.fx.update(dt * sf)
        self.hit_nums = [n for n in self.hit_nums if n.alive]
        for n in self.hit_nums: n.update(dt * sf)
        self.shake = max(0, self.shake - dt * sf * 4)

        self._check_round_end()

    def _reset_round(self):
        for f, x in ((self.player, 220), (self.ai, 1060)):
            f.x = x; f.y = GROUND_Y; f.vx = f.vy = 0
            f.hp = f.hp_max; f.energy = 0
            f.state = FS.IDLE; f.combo = 0
        self.player.facing = 1; self.ai.facing = -1
        self.projectiles.clear(); self.hit_nums.clear()
        self.round_timer = self.ROUND_TIME; self.slow_f = 1.0

    # ── Draw ────────────────────────────────

    def draw(self, surf):
        shk = random.randint(-int(self.shake * 20), int(self.shake * 20)) if self.shake > 0 else 0
        surf.blit(self.bg, (shk, 0))

        ov = pygame.Surface((W, H), pygame.SRCALPHA); ov.fill((0, 0, 0, 55))
        surf.blit(ov, (0, 0))

        # Suelo brillante
        py = GROUND_Y + 12
        for i in range(4, 0, -1):
            gl = pygame.Surface((W, 4), pygame.SRCALPHA)
            gl.fill((*C["border"], int(25 / i))); surf.blit(gl, (0, py + i * 3))
        pygame.draw.line(surf, C["border"], (0, py), (W, py), 2)

        self.player.draw_shadow(surf); self.ai.draw_shadow(surf)
        for proj in self.projectiles: proj.draw(surf)
        self.player.draw(surf); self.ai.draw(surf)
        self.fx.draw(surf)
        for n in self.hit_nums: n.draw(surf, self.game.F.dmg_big, self.game.F.dmg)

        # ── HUD ──────────────────────────────
        # Jugador
        draw_panel(surf, pygame.Rect(8, 8, 430, 88),
                   border=self.player.color, radius=10)
        draw_text(surf, self.game.player_name.upper() + f"  [{self.player.char.arch}]",
                  self.game.F.md, self.player.color, topleft=(18, 14))
        draw_hp(surf, 16, 46, 400, 20, self.player.hp, self.player.hp_max)
        draw_energy(surf, 16, 70, 400, 10, self.player.energy)
        draw_text(surf, f"{self.player.hp}/{self.player.hp_max}",
                  self.game.F.xs, C["text"], topleft=(18, 80))
        if self.player.combo >= 2:
            draw_text(surf, f"🔥 COMBO ×{self.player.combo}",
                      self.game.F.sm, C["gold"], topleft=(18, 28))

        # IA
        draw_panel(surf, pygame.Rect(W - 438, 8, 430, 88),
                   border=self.ai.color, radius=10)
        draw_text(surf, f"[{self.ai.char.arch}]  " + AI_NAME,
                  self.game.F.md, self.ai.color, topleft=(W - 428, 14))
        draw_hp(surf, W - 430, 46, 400, 20, self.ai.hp, self.ai.hp_max)
        draw_energy(surf, W - 430, 70, 400, 10, self.ai.energy)
        draw_text(surf, f"{self.ai.hp}/{self.ai.hp_max}",
                  self.game.F.xs, C["text"], topleft=(W - 428, 80))

        # Centro: ronda y timer
        draw_panel(surf, pygame.Rect(W // 2 - 90, 8, 180, 88),
                   border=(60, 80, 120), radius=10)
        draw_text(surf, f"RONDA {self.round_num}",
                  self.game.F.sm, C["gold"], center=(W // 2, 28))
        tc = int(self.round_timer)
        draw_text(surf, str(tc), self.game.F.title,
                  C["red"] if tc <= 10 else C["white"], center=(W // 2, 62))

        # Wins indicators
        for i in range((self.MAX_ROUNDS // 2) + 1):
            for wins, col, bx in [(self.p_wins, self.player.color, W // 2 - 72),
                                   (self.ai_wins, self.ai.color, W // 2 + 32)]:
                r = pygame.Rect(bx + i * 22, H - 22, 16, 16)
                pygame.draw.ellipse(surf, col if i < wins else (40, 40, 40), r)
                pygame.draw.ellipse(surf, col, r, 1)

        # ── Overlays de fase ──────────────────
        if self.phase == FP.INTRO:
            ov2 = pygame.Surface((W, H), pygame.SRCALPHA); ov2.fill((0, 0, 0, 120))
            surf.blit(ov2, (0, 0))
            a = int(pulse(self.t, 4, 80, 255))
            vs = self.game.F.title.render("VS", True, C["gold"])
            vs.set_alpha(a); surf.blit(vs, vs.get_rect(center=(W // 2, H // 2 - 20)))
            fi = self.game.F.title.render("¡FIGHT!", True, C["gold"])
            if self.phase_timer < 0.8:
                fi.set_alpha(int(pulse(self.t, 8, 100, 255)))
                surf.blit(fi, fi.get_rect(center=(W // 2, H // 2)))

        elif self.phase == FP.KO_SLOW:
            ov3 = pygame.Surface((W, H), pygame.SRCALPHA); ov3.fill((0, 0, 0, 100))
            surf.blit(ov3, (0, 0))
            ko = self.game.F.title.render("K.O.!", True, C["gold"])
            ko.set_alpha(int(pulse(self.t, 3, 160, 255)))
            surf.blit(ko, ko.get_rect(center=(W // 2, H // 2 - 40)))

        elif self.phase == FP.ROUND_END:
            ov4 = pygame.Surface((W, H), pygame.SRCALPHA); ov4.fill((0, 0, 0, 140))
            surf.blit(ov4, (0, 0))
            a = int(pulse(self.t, 2, 160, 255))
            wt = self.game.F.lg.render(self.round_result_txt, True, C["gold"])
            wt.set_alpha(a); surf.blit(wt, wt.get_rect(center=(W // 2, H // 2)))
            sc = self.game.F.md.render(f"TÚ {self.p_wins} — {self.ai_wins} IA",
                                       True, C["text"])
            sc.set_alpha(a); surf.blit(sc, sc.get_rect(center=(W // 2, H // 2 + 60)))

        elif self.phase == FP.MATCH_END:
            ov5 = pygame.Surface((W, H), pygame.SRCALPHA); ov5.fill((0, 0, 0, 165))
            surf.blit(ov5, (0, 0))
            self.fx.draw(surf)
            won = self.p_wins > self.ai_wins
            col = C["gold"] if won else self.ai.color
            a   = int(pulse(self.t, 2, 160, 255))
            mt  = self.game.F.title.render("¡VICTORIA!" if won else "DERROTA", True, col)
            mt.set_alpha(a); surf.blit(mt, mt.get_rect(center=(W // 2, H // 2 - 120)))
            draw_panel(surf, pygame.Rect(W // 2 - 260, H // 2 - 45, 520, 120),
                       border=col, radius=14)
            draw_text(surf, f"TÚ  {self.p_wins}  —  {self.ai_wins}  IA",
                      self.game.F.lg, C["gold"], center=(W // 2, H // 2 + 5))
            draw_text(surf, f"Rondas: {self.round_num}",
                      self.game.F.sm, C["text"], center=(W // 2, H // 2 + 52))
            self.btn_menu.draw(surf)

        # Controles hint
        if self.phase == FP.FIGHT and not self.paused:
            hints = [("←→", "Moverse"), ("↑/SPC", "Saltar"), ("↓", "Bloquear"),
                     ("Z", "Ataque"), ("X", "Fuerte"), ("C⚡", "Especial"), ("A", "Dash"),
                     ("P", "Pausa")]
            x0 = 30
            for key, txt in hints:
                w2 = len(key) * 10 + 44
                draw_panel(surf, pygame.Rect(x0, H - 36, w2, 24),
                           (20, 30, 60), 180, (50, 80, 120), 1, radius=6)
                draw_text(surf, f"{key} {txt}", self.game.F.xs, C["text"], topleft=(x0 + 6, H - 33))
                x0 += w2 + 8

        # ── Overlay de PAUSA ──────────────────
        if self.paused:
            ov_pause = pygame.Surface((W, H), pygame.SRCALPHA)
            ov_pause.fill((5, 10, 22, 210))
            surf.blit(ov_pause, (0, 0))

            pw, ph = 460, 310
            px, py = W // 2 - pw // 2, H // 2 - ph // 2
            draw_panel(surf, pygame.Rect(px, py, pw, ph),
                       color=(12, 18, 38), alpha=245, border=C["gold"], bw=2, radius=14)
            draw_text(surf, "⏸  BATALLA PAUSADA", self.game.F.lg, C["gold"],
                      center=(W // 2, py + 48))
            draw_text(surf, "Presiona [P] o [ESC] para continuar", self.game.F.xs, C["dim"],
                      center=(W // 2, py + 84))

            self.btn_resume.draw(surf)
            self.btn_restart.draw(surf)
            self.btn_quit.draw(surf)


# ─────────────────────────────────────────────
#  RESULTADO
# ─────────────────────────────────────────────

class ResultState(State):
    def __init__(self, game, won, p_wins, ai_wins, rounds):
        super().__init__(game)
        self.bg = load_img("victory.jpg" if won else "defeat.jpg", (W, H))
        self.ov = pygame.Surface((W, H), pygame.SRCALPHA); self.ov.fill((0, 0, 0, 145))
        self.won = won; self.p_wins = p_wins; self.ai_wins = ai_wins; self.rounds = rounds
        self.t = 0.0; self.fx = FX()
        self.btn_again = Button((W // 2 - 165, H - 188, 330, 58), "⚔  REVANCHA", game.F.md,
                                bc=(25, 60, 18), hc=(35, 150, 35))
        self.btn_chars = Button((W // 2 - 165, H - 116, 330, 48), "🎮  CAMBIAR PERSONAJE",
                                game.F.sm, hc=(20, 60, 130))
        self.btn_menu  = Button((W // 2 - 165, H - 58,  330, 44), "🏠  MENÚ",   game.F.sm)

    def handle(self, ev):
        if self.btn_again.is_clicked(ev):
            # Mismos personajes, nuevo combate
            self.game.states = [s for s in self.game.states
                                 if not isinstance(s, (ResultState, FightingState))]
            self.game.push(FightingState(self.game))
        if self.btn_chars.is_clicked(ev):
            self.game.states = [s for s in self.game.states
                                 if not isinstance(s, (ResultState, FightingState,
                                                        CharSelectState))]
            self.game.push(CharSelectState(self.game))
        if self.btn_menu.is_clicked(ev):
            self.game.states.clear(); self.game.push(MenuState(self.game))

    def update(self, dt):
        self.t += dt; mp = pygame.mouse.get_pos()
        for b in (self.btn_again, self.btn_chars, self.btn_menu): b.update(mp, dt)
        if self.won and random.random() < 0.3:
            self.fx.emit(random.randint(0, W), -6,
                         random.choice([C["gold"], C["green"], (255, 255, 255)]),
                         n=1, vy=3.5, vx=random.uniform(-1, 1), life=5.0, size=4)
        self.fx.update(dt)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0)); surf.blit(self.ov, (0, 0))
        self.fx.draw(surf)
        col = C["gold"] if self.won else (220, 40, 40)
        a   = int(pulse(self.t, 2, 150, 255))
        t   = self.game.F.title.render("¡VICTORIA!" if self.won else "DERROTA", True, col)
        t.set_alpha(a); surf.blit(t, t.get_rect(center=(W // 2, H // 2 - 160)))
        draw_panel(surf, pygame.Rect(W // 2 - 240, H // 2 - 70, 480, 125), border=col, radius=14)
        draw_text(surf, f"TÚ {self.p_wins}  —  {self.ai_wins} IA",
                  self.game.F.lg, C["gold"], center=(W // 2, H // 2 - 25))
        draw_text(surf, f"Rondas: {self.rounds}",
                  self.game.F.sm, C["text"], center=(W // 2, H // 2 + 25))
        draw_text(surf, f"Personaje: {self.game.player_char.name}  vs  {self.game.ai_char.name}",
                  self.game.F.xs, C["dim"], center=(W // 2, H // 2 + 48))
        self.btn_again.draw(surf)
        self.btn_chars.draw(surf)
        self.btn_menu.draw(surf)


# ─────────────────────────────────────────────
#  CLASIFICACIÓN
# ─────────────────────────────────────────────

class LeaderState(State):
    def __init__(self, game):
        super().__init__(game)
        self.bg = load_img("menu_bg.jpg", (W, H))
        self.ov = pygame.Surface((W, H), pygame.SRCALPHA); self.ov.fill((0, 0, 0, 170))
        self.btn_back = Button((W // 2 - 145, H - 92, 290, 50), "← VOLVER", game.F.md)
        self.data = [(n, v, d, r) for n, v, d, r in game.svc.obtener_clasificacion()
                     if n != AI_NAME]

    def handle(self, ev):
        if self.btn_back.is_clicked(ev): self.game.pop()

    def update(self, dt): self.btn_back.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0)); surf.blit(self.ov, (0, 0))
        draw_text(surf, "🏆  CLASIFICACIÓN", self.game.F.title, C["gold"], center=(W // 2, 55))
        draw_panel(surf, pygame.Rect(90, 115, 900, 40), (18, 38, 78), 220, C["border"], radius=6)
        for lbl, x in [("Pos", 130), ("Piloto", 310), ("V", 560), ("D", 640), ("Ratio", 720)]:
            draw_text(surf, lbl, self.game.F.sm, C["border"], topleft=(x, 124))
        if not self.data:
            draw_text(surf, "(sin combates)", self.game.F.md, C["dim"], center=(W // 2, H // 2))
        med = ["🥇", "🥈", "🥉"]
        for i, (n, v, d, r) in enumerate(self.data[:12]):
            y = 162 + i * 45
            draw_panel(surf, pygame.Rect(90, y, 900, 39),
                       (28, 48, 18) if i == 0 else (18, 28, 50), 220,
                       C["gold"] if i == 0 else (40, 60, 100), 1, radius=6)
            draw_text(surf, med[i] if i < 3 else f"{i+1}.", self.game.F.sm, C["gold"], topleft=(110, y + 10))
            draw_text(surf, n,       self.game.F.sm, C["white"],  topleft=(210, y + 10))
            draw_text(surf, str(v),  self.game.F.sm, C["green"],  topleft=(560, y + 10))
            draw_text(surf, str(d),  self.game.F.sm, C["red"],    topleft=(640, y + 10))
            draw_text(surf, f"{r:.0%}", self.game.F.sm, C["border"], topleft=(720, y + 10))
        self.btn_back.draw(surf)


# ─────────────────────────────────────────────
#  FUENTES
# ─────────────────────────────────────────────

class Fonts:
    def __init__(self):
        self.title   = pygame.font.SysFont("Arial Black", 72, bold=True)
        self.lg      = pygame.font.SysFont("Arial", 36, bold=True)
        self.md      = pygame.font.SysFont("Arial", 24, bold=True)
        self.sm      = pygame.font.SysFont("Arial", 18)
        self.xs      = pygame.font.SysFont("Consolas", 13)
        self.dmg     = pygame.font.SysFont("Arial Black", 30, bold=True)
        self.dmg_big = pygame.font.SysFont("Arial Black", 50, bold=True)


# ─────────────────────────────────────────────
#  MOTOR
# ─────────────────────────────────────────────

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("⚙ Mecha-Arena v5.0 ⚙")
        icon = pygame.Surface((32, 32)); icon.fill((0, 150, 255))
        pygame.display.set_icon(icon)
        self.screen = pygame.display.set_mode((W, H))
        self.clock  = pygame.time.Clock()
        self.F      = Fonts()
        self.svc    = AppService()
        self.player_name = ""
        self.player_char: Optional[CharDef] = None
        self.ai_char:     Optional[CharDef] = None
        self.states: List[State] = []
        self.push(MenuState(self))

    def push(self, s: State): self.states.append(s); s.on_enter()
    def pop(self):
        if len(self.states) > 1: self.states.pop()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    if len(self.states) > 1: self.states.pop()
                if self.states: self.states[-1].handle(ev)
            if self.states: self.states[-1].update(dt)
            self.screen.fill(C["bg"])
            if self.states: self.states[-1].draw(self.screen)
            fps = self.clock.get_fps()
            f = self.F.xs.render(f"{fps:.0f}fps", True, C["dim"])
            self.screen.blit(f, (W - 52, H - 20))
            pygame.display.flip()


if __name__ == "__main__":
    Game().run()
