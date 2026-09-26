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

FONT_PATH = 'Salina-SwExtraLightItalic.otf'
BRAND = 'Shengyin Studios'

# ---- paleta
NEGRO = (0.035, 0.033, 0.031)   # negro cálido del fondo
COBRE = (0.784, 0.506, 0.278)   # #C88147  (anillo)
ORO  = (0.784, 0.506, 0.278)   # #C88147  (letras)
# ORO   = (0.878, 0.702, 0.404)   # #E0B367  (letras)


def hexcolor(rgb):
    return '#%02x%02x%02x' % tuple(round(c * 255) for c in rgb)


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

    # ---- letras: un <path> por glifo, posicionado con transform
    letter_paths = []
    for g in glyphs:
        d = sal.glyph_path_d(g['name'])
        if not d:
            continue
        gx = x_start + g['x'] * scale
        gy = baseline_y - g['y'] * scale
        letter_paths.append(
            f'<path transform="translate({gx:.2f},{gy:.2f}) scale({scale:.6f},{-scale:.6f})" d="{d}"/>'
        )

    ring_d = ring_path_d(cx, cy, r, slot_deg, center_deg=0.0)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect x="0" y="0" width="{W}" height="{H}" fill="{hexcolor(NEGRO)}"/>
  <path d="{ring_d}" fill="none" stroke="{hexcolor(COBRE)}" stroke-width="{ring_w}" stroke-linecap="round"/>
  <g fill="{hexcolor(ORO)}">
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
