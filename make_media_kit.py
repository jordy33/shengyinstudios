# -*- coding: utf-8 -*-
"""Shengyin Studios — media kit para distribución y redes.

Genera el logo (anillo + texto con gradiente metálico) en TODAS las
medidas que piden DistroKid y las plataformas a las que DistroKid entrega
el arte (Spotify for Artists, Apple Music for Artists, YouTube) más las
redes sociales principales.

Como el logo es 100% vectorial (contornos reales del font + un anillo
calculado), cada archivo se renderiza directo a su resolución final —
nunca se re-escala un PNG ya rasterizado, así que no hay pérdida de
nitidez sin importar cuántos tamaños generes.

Dependencias:
    pip install fonttools uharfbuzz cairosvg pillow

Salida: media_kit/<plataforma>/<archivo>.png (+ .svg del maestro)

Fuentes de las medidas (verificadas sep-2026, revisa si la plataforma
las cambió):
  - DistroKid cover art:      support.distrokid.com (mín. 3000x3000)
  - DistroKid foto de perfil: 250x250 recomendado (propaga a Spotify)
  - Spotify for Artists:      artists.spotify.com (avatar 750x750 min,
                               header 2660x1140 min)
  - Apple Music for Artists:  artists.apple.com (imagen 2400x2400,
                               cuadrada, SIN canal alfa)
  - YouTube:                  support.google.com (banner 2560x1440,
                               zona segura 1546x423; foto perfil 800x800)
  - Redes sociales:           specs públicas de cada plataforma (pueden
                               cambiar; usa el tamaño recomendado, no el
                               mínimo, para que se vea nítido a futuro)

Corre con:  python3 make_media_kit.py
"""
import math
import os
import uharfbuzz as hb
import cairosvg
from PIL import Image
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

FONT_PATH = 'Salina-SwExtraLightItalic.otf'
BRAND = 'Shengyin Studios'
OUTDIR = 'media_kit'

# ---- paleta
NEGRO = (0.035, 0.033, 0.031)   # negro cálido del fondo
COBRE = (0.784, 0.506, 0.278)   # #C88147  (anillo)
ORO   = (0.878, 0.702, 0.404)   # #E0B367  (letras)


# ---------------------------------------------------------------- color ----

def hexcolor(rgb):
    return '#%02x%02x%02x' % tuple(round(c * 255) for c in rgb)


def lighten(rgb, amt):
    return tuple(min(1.0, c + (1.0 - c) * amt) for c in rgb)


def darken(rgb, amt):
    return tuple(max(0.0, c * (1.0 - amt)) for c in rgb)


def metal_gradient(gid, base_rgb, x1, y1, x2, y2):
    """Gradiente de 5 bandas (sombra->color->brillo->color->sombra) que
    simula metal bajo una fuente de luz diagonal."""
    dark = hexcolor(darken(base_rgb, 0.55))
    mid = hexcolor(base_rgb)
    light = hexcolor(lighten(base_rgb, 0.65))
    return (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
            f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}">'
            f'<stop offset="0%" stop-color="{dark}"/>'
            f'<stop offset="28%" stop-color="{mid}"/>'
            f'<stop offset="50%" stop-color="{light}"/>'
            f'<stop offset="72%" stop-color="{mid}"/>'
            f'<stop offset="100%" stop-color="{dark}"/>'
            f'</linearGradient>')


# ------------------------------------------------------------ shaping ----

class ShapedText:
    """fontTools + uharfbuzz: shaping real (kerning/swashes vía GSUB/GPOS)
    y extracción de contornos vectoriales."""

    def __init__(self, font_path):
        self.ttfont = TTFont(font_path)
        self.upem = self.ttfont['head'].unitsPerEm
        self.glyph_set = self.ttfont.getGlyphSet()
        self.glyph_order = self.ttfont.getGlyphOrder()

        data = open(font_path, 'rb').read()
        face = hb.Face(data)
        self.hb_font = hb.Font(face)
        self.hb_font.scale = (self.upem, self.upem)

    def shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf)
        glyphs = []
        cursor = 0.0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            glyphs.append({
                'name': self.glyph_order[info.codepoint],
                'x': cursor + pos.x_offset,
                'y': pos.y_offset,
            })
            cursor += pos.x_advance
        return glyphs, cursor

    def glyph_path_d_transformed(self, name, sx, sy, tx, ty):
        """Path del glifo con la transformación ya horneada en las
        coordenadas (no como atributo transform=""), para que un
        gradiente userSpaceOnUse aplicado por herencia se resuelva en
        coordenadas globales del canvas."""
        pen = SVGPathPen(self.glyph_set)
        t = Transform(sx, 0, 0, sy, tx, ty)
        self.glyph_set[name].draw(TransformPen(pen, t))
        return pen.getCommands()

    def visual_bounds(self, glyphs):
        xmin = ymin = xmax = ymax = None
        for g in glyphs:
            bp = BoundsPen(self.glyph_set)
            self.glyph_set[g['name']].draw(bp)
            if not bp.bounds:
                continue
            bxmin, bymin, bxmax, bymax = bp.bounds
            lo_x, hi_x = g['x'] + bxmin, g['x'] + bxmax
            lo_y, hi_y = g['y'] + bymin, g['y'] + bymax
            xmin = lo_x if xmin is None else min(xmin, lo_x)
            xmax = hi_x if xmax is None else max(xmax, hi_x)
            ymin = lo_y if ymin is None else min(ymin, lo_y)
            ymax = hi_y if ymax is None else max(ymax, hi_y)
        return xmin, ymin, xmax, ymax


def arc_points(cx, cy, r, a0, a1, steps=400):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / steps),
             cy + r * math.sin(a0 + (a1 - a0) * i / steps))
            for i in range(steps + 1)]


def ring_path_d(cx, cy, r, slot_deg, center_deg=0.0):
    half = math.radians(slot_deg) / 2.0
    c = math.radians(center_deg)
    pts = arc_points(cx, cy, r, c + half, c + 2 * math.pi - half)
    d = f'M {pts[0][0]:.2f},{pts[0][1]:.2f} '
    d += ' '.join(f'L {x:.2f},{y:.2f}' for x, y in pts[1:])
    return d


# --------------------------------------------------------- diseño base ----

class LogoDesign:
    """Geometría del logo calculada UNA vez en un espacio de diseño
    centrado en (0,0). render() la reescala/traslada a cualquier canvas
    y caja de encuadre sin perder nitidez (todo sigue siendo vectorial
    hasta el momento final de rasterizar)."""

    RING_GAP_DEG = 34.0
    RING_W_RATIO = 13.0 / 120.0   # grosor de anillo relativo al font-size de referencia
    RING_MARGIN_RATIO = 130.0 / 120.0  # separación letras<->anillo, relativa

    def __init__(self, font_path, brand):
        self.sal = ShapedText(font_path)
        ref_size = 120.0
        self.base_scale = ref_size / self.sal.upem

        self.glyphs, _ = self.sal.shape(brand)
        xmin, ymin, xmax, ymax = self.sal.visual_bounds(self.glyphs)
        self.ink_cx_units = (xmin + xmax) / 2.0
        self.ink_cy_units = (ymin + ymax) / 2.0
        self.xmin, self.xmax = xmin, xmax

        tw_design = (xmax - xmin) * self.base_scale
        self.r_design = tw_design / 2.0 + self.RING_MARGIN_RATIO * ref_size
        self.ring_w_design = self.RING_W_RATIO * ref_size
        # diámetro total (anillo + su propio grosor) = lo que hay que
        # encajar dentro de la caja de destino
        self.diameter_design = 2.0 * (self.r_design + self.ring_w_design / 2.0)

    def render(self, canvas_w, canvas_h, fit_w, fit_h, fit_cx, fit_cy,
               svg_path, png_path, flatten_alpha=True):
        k = min(fit_w, fit_h) / self.diameter_design
        scale = self.base_scale * k
        r = self.r_design * k
        ring_w = self.ring_w_design * k

        tx = fit_cx - self.ink_cx_units * scale
        ty = fit_cy + self.ink_cy_units * scale

        letter_paths = []
        for g in self.glyphs:
            gx = tx + g['x'] * scale
            gy = ty - g['y'] * scale
            d = self.sal.glyph_path_d_transformed(g['name'], scale, -scale, gx, gy)
            if d:
                letter_paths.append(f'<path d="{d}"/>')

        ring_d = ring_path_d(fit_cx, fit_cy, r, self.RING_GAP_DEG, center_deg=0.0)

        # gradientes: anillo dimensionado a su radio, texto a su ancho
        # real -> ambos muestran la banda de brillo completa
        ring_x1, ring_y1 = fit_cx - r, fit_cy - r
        ring_x2, ring_y2 = fit_cx + r, fit_cy + r
        text_left = tx + self.xmin * scale
        text_right = tx + self.xmax * scale
        half_tw = (text_right - text_left) / 2.0
        text_x1, text_y1 = fit_cx - half_tw, fit_cy - half_tw
        text_x2, text_y2 = fit_cx + half_tw, fit_cy + half_tw

        grad_defs = (
            metal_gradient('copperMetal', COBRE, ring_x1, ring_y1, ring_x2, ring_y2) +
            metal_gradient('goldMetal', ORO, text_x1, text_y1, text_x2, text_y2)
        )

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}">
  <defs>
    {grad_defs}
  </defs>
  <rect x="0" y="0" width="{canvas_w}" height="{canvas_h}" fill="{hexcolor(NEGRO)}"/>
  <path d="{ring_d}" fill="none" stroke="url(#copperMetal)" stroke-width="{ring_w:.2f}" stroke-linecap="round"/>
  <g fill="url(#goldMetal)">
    {''.join(letter_paths)}
  </g>
</svg>'''

        os.makedirs(os.path.dirname(svg_path), exist_ok=True)
        with open(svg_path, 'w') as f:
            f.write(svg)

        cairosvg.svg2png(url=svg_path, write_to=png_path,
                          output_width=canvas_w, output_height=canvas_h)

        if flatten_alpha:
            # Algunas plataformas (Apple Music en particular) rechazan
            # imágenes con canal alfa, aunque sea 100% opaco. Aplanamos
            # a RGB puro para evitar cualquier duda.
            img = Image.open(png_path).convert('RGB')
            img.save(png_path)


# --------------------------------------------------------------- specs ----
# (nombre_archivo, ancho, alto, ancho_encuadre, alto_encuadre, cx, cy, nota)
# ancho/alto_encuadre = tamaño de la caja donde debe caber el logo
# (más chica que el canvas para dejar margen de seguridad / zona segura)

def sq(canvas, fit_ratio=0.9):
    """Spec cuadrado simple: encuadre centrado, `fit_ratio` del canvas."""
    fit = canvas * fit_ratio
    c = canvas / 2.0
    return canvas, canvas, fit, fit, c, c


SPECS = [
    # ---- DistroKid (distribución) ----
    ('distrokid/cover_art_3000x3000.png', *sq(3000, 0.90),
     'DistroKid cover art — min. 3000x3000, cuadrado, sin URLs/promo'),
    ('distrokid/profile_512x512.png', *sq(512, 0.90),
     'Foto de perfil DistroKid (recomendado 250x250 min; se sube a 512 para nitidez)'),

    # ---- Spotify for Artists ----
    ('spotify/artist_profile_1500x1500.png', *sq(1500, 0.80),
     'Spotify for Artists — avatar circular, min. 750x750 (margen extra por el crop circular)'),
    # header: banner ancho, el 35% inferior queda tapado por nombre/botones,
    # así que centramos el logo en el tercio superior
    ('spotify/artist_header_2660x1140.png', 2660, 1140, 1140 * 0.72, 1140 * 0.72,
     1330, 1140 * 0.40,
     'Spotify for Artists — header 2660x1140, contenido en el tercio superior'),

    # ---- Apple Music for Artists ----
    ('applemusic/artist_image_2400x2400.png', *sq(2400, 0.82),
     'Apple Music for Artists — 2400x2400, cuadrado, SIN transparencia'),

    # ---- YouTube ----
    ('youtube/profile_800x800.png', *sq(800, 0.80),
     'YouTube — foto de canal circular, 800x800'),
    # banner: solo lo que cae en la zona segura 1546x423 (centrada) se ve
    # garantizado en todos los dispositivos
    ('youtube/channel_banner_2560x1440.png', 2560, 1440, 1546 * 0.78, 423 * 0.78,
     1280, 720,
     'YouTube — banner 2560x1440; logo dentro de la zona segura 1546x423'),

    # ---- Redes sociales ----
    ('social/instagram_profile_320x320.png', *sq(320, 0.78),
     'Instagram — foto de perfil circular, min. 320x320'),
    ('social/facebook_profile_320x320.png', *sq(320, 0.78),
     'Facebook — foto de perfil circular, min. 320x320'),
    ('social/tiktok_profile_200x200.png', *sq(200, 0.78),
     'TikTok — foto de perfil circular, 200x200'),
    ('social/x_profile_400x400.png', *sq(400, 0.78),
     'X (Twitter) — foto de perfil circular, 400x400'),
    ('social/x_header_1500x500.png', 1500, 500, 500 * 0.75, 500 * 0.75, 750, 250,
     'X (Twitter) — banner de cabecera, 1500x500'),
]


def main():
    design = LogoDesign(FONT_PATH, BRAND)

    print(f'{"archivo":45s} {"tamaño":>12s}   nota')
    print('-' * 100)
    for rel_path, cw, ch, fw, fh, fcx, fcy, note in SPECS:
        png_path = os.path.join(OUTDIR, rel_path)
        svg_path = os.path.splitext(png_path)[0] + '.svg'
        design.render(cw, ch, fw, fh, fcx, fcy, svg_path, png_path)
        print(f'{rel_path:45s} {cw}x{ch:<7}  {note}')

    print(f'\nok -> {OUTDIR}/  ({len(SPECS)} assets, PNG + SVG cada uno)')


if __name__ == '__main__':
    main()
