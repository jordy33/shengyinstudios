# -*- coding: utf-8 -*-
"""Logo de Shengyin Studios (marca de música) — versión autocontenida.

No depende de módulos caseros (.tools/canvas.py, .tools/typekit.py).
Solo usa librerías de terceros bien mantenidas:

    pip install --break-system-packages fonttools uharfbuzz cairosvg

- fonttools   -> extrae los contornos vectoriales reales de cada glifo
- uharfbuzz   -> shaping correcto (kerning, ligaduras/swashes vía GSUB/GPOS)
- cairosvg    -> rasteriza el SVG final a PNG usando los MISMOS paths

Salidas:
  - logo.svg  (fuente de verdad, vectorial)
  - logo.png  (preview, rasterizado desde el mismo SVG)

Corre con:  python3 make_logo.py
"""
import math
import uharfbuzz as hb
import cairosvg
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

FONT_PATH = 'Salina-SwExtraLightItalic.otf'
BRAND = 'Shengyin Studios'

# ---- paleta
NEGRO = (0.035, 0.033, 0.031)   # negro cálido del fondo
COBRE = (0.784, 0.506, 0.278)   # #C88147  (anillo)
ORO   = (0.878, 0.702, 0.404)   # #E0B367  (letras)


def hexcolor(rgb):
    return '#%02x%02x%02x' % tuple(round(c * 255) for c in rgb)


def lighten(rgb, amt):
    return tuple(min(1.0, c + (1.0 - c) * amt) for c in rgb)


def darken(rgb, amt):
    return tuple(max(0.0, c * (1.0 - amt)) for c in rgb)


def metal_gradient(gid, base_rgb, x1, y1, x2, y2):
    """Gradiente lineal de 5 bandas que simula una superficie metálica
    curva bajo una fuente de luz: sombra -> color -> brillo -> color ->
    sombra. userSpaceOnUse para que el barrido de luz sea continuo sobre
    TODO el logo (anillo + letras comparten el mismo sistema de
    coordenadas), en vez de que cada letra tenga su propio brillo
    aislado (que se ve "pegado", no metálico)."""
    dark = hexcolor(darken(base_rgb, 0.55))
    mid = hexcolor(base_rgb)
    light = hexcolor(lighten(base_rgb, 0.65))
    return f'''<linearGradient id="{gid}" gradientUnits="userSpaceOnUse"
      x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}">
      <stop offset="0%"  stop-color="{dark}"/>
      <stop offset="28%" stop-color="{mid}"/>
      <stop offset="50%" stop-color="{light}"/>
      <stop offset="72%" stop-color="{mid}"/>
      <stop offset="100%" stop-color="{dark}"/>
    </linearGradient>'''


def arc_points(cx, cy, r, a0, a1, steps=400):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / steps),
             cy + r * math.sin(a0 + (a1 - a0) * i / steps))
            for i in range(steps + 1)]


def ring_path_d(cx, cy, r, slot_deg, center_deg=0.0):
    """Arco (polilínea) con UNA sola abertura de `slot_deg` grados,
    centrada en `center_deg` (0 = derecha, 90 = arriba). Se dibuja con
    stroke, no relleno, así que no hace falta triangular a mano."""
    half = math.radians(slot_deg) / 2.0
    c = math.radians(center_deg)
    pts = arc_points(cx, cy, r, c + half, c + 2 * math.pi - half)
    d = f'M {pts[0][0]:.2f},{pts[0][1]:.2f} '
    d += ' '.join(f'L {x:.2f},{y:.2f}' for x, y in pts[1:])
    return d


class ShapedText:
    """Envuelve fontTools + uharfbuzz para shaping y extracción de contornos."""

    def __init__(self, font_path):
        self.ttfont = TTFont(font_path)
        self.upem = self.ttfont['head'].unitsPerEm
        self.glyph_set = self.ttfont.getGlyphSet()
        self.glyph_order = self.ttfont.getGlyphOrder()

        data = open(font_path, 'rb').read()
        face = hb.Face(data)
        self.hb_font = hb.Font(face)
        self.hb_font.scale = (self.upem, self.upem)

        os2 = self.ttfont['OS/2']
        self.x_height = getattr(os2, 'sxHeight', self.upem * 0.5)

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
        return glyphs, cursor  # cursor final = ancho total en unidades de fuente

    def glyph_path_d(self, name):
        pen = SVGPathPen(self.glyph_set)
        self.glyph_set[name].draw(pen)
        return pen.getCommands()

    def glyph_path_d_transformed(self, name, sx, sy, tx, ty):
        """Igual que glyph_path_d pero con la transformación (escala +
        traslado) ya 'horneada' en las coordenadas del path, en vez de
        ponerla en un atributo transform="" del <path>. Es necesario para
        que un gradiente userSpaceOnUse aplicado por herencia (fill en el
        <g> padre) se resuelva en coordenadas globales del canvas y no en
        el sistema de coordenadas local (diminuto y con Y invertida) de
        cada glifo — si no, el brillo del metal sale distorsionado y
        distinto en cada letra."""
        pen = SVGPathPen(self.glyph_set)
        t = Transform(sx, 0, 0, sy, tx, ty)
        self.glyph_set[name].draw(TransformPen(pen, t))
        return pen.getCommands()

    def visual_bounds(self, glyphs):
        """Bounding box REAL de la tinta (incluye swashes que sobresalen
        del cuadro de avance), en unidades de fuente. Esto es lo que hay
        que centrar, no el ancho de avance ni el x-height nominal."""
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


def main():
    W = H = 1600
    cx = cy = W / 2.0
    size = 120.0

    sal = ShapedText(FONT_PATH)
    scale = size / sal.upem

    glyphs, cursor_units = sal.shape(BRAND)

    # Centrado ÓPTICO: usamos el bounding box real de la tinta (incluye
    # swashes que sobresalen del cuadro de avance), no el ancho de avance
    # ni una fórmula de x-height. Esto es lo que corrige el descentrado.
    xmin, ymin, xmax, ymax = sal.visual_bounds(glyphs)
    ink_cx_units = (xmin + xmax) / 2.0
    ink_cy_units = (ymin + ymax) / 2.0
    tw = (xmax - xmin) * scale  # ancho visual real del logotipo en px

    r = tw / 2.0 + 130
    ring_w = 13.0
    slot_deg = 34.0

    # x_start/baseline_y se eligen para que el CENTRO DE LA TINTA
    # (no el origin/baseline nominal) caiga exactamente en (cx, cy).
    x_start = cx - ink_cx_units * scale
    baseline_y = cy + ink_cy_units * scale

    # ---- letras: un <path> por glifo, YA en coordenadas finales del canvas
    # (transformación horneada, ver glyph_path_d_transformed)
    letter_paths = []
    for g in glyphs:
        gx = x_start + g['x'] * scale
        gy = baseline_y - g['y'] * scale
        d = sal.glyph_path_d_transformed(g['name'], scale, -scale, gx, gy)
        if not d:
            continue
        letter_paths.append(f'<path d="{d}"/>')

    ring_d = ring_path_d(cx, cy, r, slot_deg, center_deg=0.0)

    # Cada elemento (anillo, texto) recibe su PROPIO gradiente, escalado a
    # su propio tamaño, pero con la misma dirección de luz (diagonal a 45°)
    # para que se sienta como una sola fuente de luz consistente. Si se usa
    # un único gradiente dimensionado para el radio del anillo, el texto
    # (mucho más angosto) queda atrapado en la banda media y se ve apagado
    # en vez de brillar.
    ring_x1, ring_y1 = cx - r, cy - r
    ring_x2, ring_y2 = cx + r, cy + r

    text_left_px = x_start + xmin * scale
    text_right_px = x_start + xmax * scale
    half_tw = (text_right_px - text_left_px) / 2.0
    text_x1, text_y1 = cx - half_tw, cy - half_tw
    text_x2, text_y2 = cx + half_tw, cy + half_tw

    grad_defs = (
        metal_gradient('copperMetal', COBRE, ring_x1, ring_y1, ring_x2, ring_y2) +
        metal_gradient('goldMetal', ORO, text_x1, text_y1, text_x2, text_y2)
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    {grad_defs}
  </defs>
  <rect x="0" y="0" width="{W}" height="{H}" fill="{hexcolor(NEGRO)}"/>
  <path d="{ring_d}" fill="none" stroke="url(#copperMetal)" stroke-width="{ring_w}" stroke-linecap="round"/>
  <g fill="url(#goldMetal)">
    {''.join(letter_paths)}
  </g>
</svg>'''

    with open('logo.svg', 'w') as f:
        f.write(svg)

    cairosvg.svg2png(url='logo.svg', write_to='logo.png',
                      output_width=W, output_height=H)

    print(f'ok -> logo.svg / logo.png  (ancho logotipo {tw:.0f}px, radio {r:.0f}px)')


if __name__ == '__main__':
    main()
