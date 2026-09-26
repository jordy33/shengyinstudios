"""Utilidades de marca: cobre/oro, círculo con ranura, logotipo y caja de seguridad.

Convención de coordenadas (igual que CSS/SVG):
  x crece a la derecha, y crece HACIA ABAJO, origen en la esquina superior izquierda.
  Las funciones de texto reciben la LÍNEA BASE en `y`.
"""
import math
sys_path_done = False
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import typekit as tk

# ---------------------------------------------------------------- paleta
NEGRO      = (0.035, 0.033, 0.031)   # negro cálido del fondo
COBRE      = (0.784, 0.506, 0.278)   # #C88147  cobre
COBRE_CLARO= (0.847, 0.596, 0.353)   # #D8985A
ORO        = (0.878, 0.702, 0.404)   # #E0B367  oro
ORO_PALIDO = (0.925, 0.804, 0.576)   # #ECCD93  oro pálido
Hueso      = (0.937, 0.918, 0.878)

# métricas reales del font (unidades/1000 em, sobre la línea base)
ASC   = 0.754    # ascendente de 'h'
CAP   = 0.710    # altura de versal 'S'
XH    = 0.505    # altura de x  'n'
DESC  = 0.241    # descendente de 'g'
BANDA = 0.256    # centro de la banda de las letras (x-height / 2)


# ---------------------------------------------------------------- trazos
def stroke_path(pts, w, cap='butt'):
    """Convierte una polilínea densa en un polígono cerrado de grosor w."""
    n = len(pts)
    if n < 2: return []
    left, right = [], []
    for i, p in enumerate(pts):
        if i == 0:       dx, dy = pts[1][0]-p[0], pts[1][1]-p[1]
        elif i == n-1:   dx, dy = p[0]-pts[-2][0], p[1]-pts[-2][1]
        else:            dx, dy = pts[i+1][0]-pts[i-1][0], pts[i+1][1]-pts[i-1][1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy/L*w/2.0, dx/L*w/2.0
        left.append((p[0]+nx, p[1]+ny)); right.append((p[0]-nx, p[1]-ny))
    loop = left + right[::-1]
    return [(loop[0], [('L', q) for q in loop[1:]])]


def arc_pts(cx, cy, r, a0, a1, steps=None):
    if steps is None:
        steps = max(24, int(abs(a1-a0)*r/1.2))
    return [(cx + r*math.cos(a0 + (a1-a0)*i/steps),
             cy + r*math.sin(a0 + (a1-a0)*i/steps)) for i in range(steps+1)]


def circle_path(cx, cy, r):
    k = r*0.5522847498
    return [((cx+r, cy), [
        ('C', (cx+r, cy+k), (cx+k, cy+r), (cx, cy+r)),
        ('C', (cx-k, cy+r), (cx-r, cy+k), (cx-r, cy)),
        ('C', (cx-r, cy-k), (cx-k, cy-r), (cx, cy-r)),
        ('C', (cx+k, cy-r), (cx+r, cy-k), (cx+r, cy)),
    ])]


def slot_ring_path(cx, cy, r, w, slot_deg, slot_center_deg):
    """Anillo de radio r y grosor w, con una ranura angular de slot_deg."""
    if slot_deg <= 0:
        return stroke_path(arc_pts(cx, cy, r, 0, 2*math.pi), w)
    half = math.radians(slot_deg)/2.0
    c = math.radians(slot_center_deg)
    return stroke_path(arc_pts(cx, cy, r, c+half, c+2*math.pi-half), w)


# ---------------------------------------------------------------- logotipo
class Wordmark:
    """Logotipo 'Shengyin Studios' compuesto con Salina Swashes ExtraLight Italic."""

    def __init__(self, font, text='Shengyin Studios'):
        self.font = font
        self.text = text

    def run(self, size):
        return self.font.shape(self.text, size=size)

    def width(self, size):
        return self.run(size)['width']

    def paths(self, cx, baseline, size, replace_last_o=None):
        """Paths del logotipo centrado en cx, con la línea base indicada.
        Si replace_last_o es un dict, se omite esa 'o' (para poner el círculo)."""
        run = self.run(size)
        x0 = cx - run['width']/2.0
        out = []
        skip = None
        if replace_last_o is not None:
            idxs = [i for i, g in enumerate(run['glyphs']) if g['name'] == 'o']
            if idxs: skip = idxs[-1]
        for i, g in enumerate(run['glyphs']):
            if g['name'] == 'space' or i == skip: continue
            out += tk.translate(self.font.glyph_path(g['gid'], size), x0 + g['x'], baseline)
        return out, run, x0

    def last_o_box(self, size):
        """Caja de la última 'o' cuando el logotipo está centrado en 0."""
        run = self.run(size)
        idx = [i for i, g in enumerate(run['glyphs']) if g['name'] == 'o'][-1]
        g = run['glyphs'][idx]
        bb = tk.bbox(self.font.glyph_path(g['gid'], size))
        x_off = -run['width']/2.0 + g['x']
        return (bb[0]+x_off, bb[1], bb[2]+x_off, bb[3])


def em(text_font, size, key):
    return size * {'asc': ASC, 'cap': CAP, 'xh': XH, 'desc': DESC, 'band': BANDA}[key]
