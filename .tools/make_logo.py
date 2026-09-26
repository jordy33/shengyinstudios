import sys, math
sys.path.insert(0, '.tools')
from canvas import Canvas
import typekit as tk

SALINA = 'Salina-SwExtraLightItalic.otf'
ARIAL  = '/System/Library/Fonts/Supplemental/Arial.ttf'
sal = tk.Font(SALINA)
arl = tk.Font(ARIAL)

BG     = (0.035, 0.033, 0.031)
COPPER = (0.784, 0.506, 0.278)
GOLD   = (0.870, 0.686, 0.392)
BRAND  = 'Shengyin Studios'
BAND   = 0.256          # centro de la banda de las letras, en em sobre la línea base


def stroke_path(pts, w):
    n = len(pts); left, right = [], []
    for i, p in enumerate(pts):
        if i == 0:      dx, dy = pts[1][0]-p[0], pts[1][1]-p[1]
        elif i == n-1:  dx, dy = p[0]-pts[-2][0], p[1]-pts[-2][1]
        else:           dx, dy = pts[i+1][0]-pts[i-1][0], pts[i+1][1]-pts[i-1][1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy/L*w/2.0, dx/L*w/2.0
        left.append((p[0]+nx, p[1]+ny)); right.append((p[0]-nx, p[1]-ny))
    loop = left + right[::-1]
    return [(loop[0], [('L', q) for q in loop[1:]])]


def arc_pts(cx, cy, r, a0, a1, steps=500):
    return [(cx + r*math.cos(a0 + (a1-a0)*i/steps),
             cy + r*math.sin(a0 + (a1-a0)*i/steps)) for i in range(steps+1)]


def ring(cv, cx, cy, r, w, color, slot_deg=0.0, slot_center_deg=0.0):
    """Círculo con una ranura centrada en slot_center_deg (0 = derecha, 90 = arriba)."""
    if slot_deg <= 0:
        cv.draw(stroke_path(arc_pts(cx, cy, r, 0, 2*math.pi), w), color); return
    half = math.radians(slot_deg)/2.0
    c = math.radians(slot_center_deg)
    cv.draw(stroke_path(arc_pts(cx, cy, r, c+half, c+2*math.pi-half), w), color)


def wordmark_width(size):
    return sal.shape(BRAND, size=size)['width']


def place(cv, cx, cy, size, color):
    """Logotipo centrado en cx, con la banda de las letras en cy."""
    run = sal.shape(BRAND, size=size)
    x = cx - run['width']/2.0
    cv.draw(tk.run_to_subpaths(sal, run, x=x, y=cy - BAND*size), color)
    return run['width']


def caption(cv, ox, oy, txt):
    cv.text(arl, txt, ox, oy, 21, (0.40, 0.38, 0.36), tracking=1.1)


W = H = 2400
cv = Canvas(W, H, BG)

# ---------- A · círculo envolvente, UNA ranura a la derecha, en la banda de las letras
def vA(ox, oy):
    cx, cy = ox+600, oy+600
    size = 74
    tw = wordmark_width(size)
    r = tw/2 + 105
    ring(cv, cx, cy, r, 12.0, COPPER, slot_deg=34.0, slot_center_deg=0.0)
    place(cv, cx, cy, size, COPPER)
    caption(cv, ox+50, oy+50, 'A  ·  UNA RANURA, A LA DERECHA, EN LA BANDA DE LAS LETRAS')

# ---------- B · círculo envolvente, DOS ranuras (izq. y der.)
def vB(ox, oy):
    cx, cy = ox+600, oy+600
    size = 74
    tw = wordmark_width(size)
    r = tw/2 + 105
    ring(cv, cx, cy, r, 12.0, COPPER, slot_deg=26.0, slot_center_deg=0.0)
    ring(cv, cx, cy, r, 12.0, COPPER, slot_deg=26.0, slot_center_deg=180.0)
    place(cv, cx, cy, size, COPPER)
    caption(cv, ox+50, oy+50, 'B  ·  DOS RANURAS: EL INFINITO SE ROMPE DONDE PASAN LAS LETRAS')

# ---------- C · símbolo + logotipo, ranura mirando al texto
def vC(ox, oy):
    cy = oy+600
    size = 96
    tw = wordmark_width(size)
    r = 132.0
    gap = 78
    total = 2*r + gap + tw
    left = ox + (1200 - total)/2
    ccx = left + r
    ring(cv, ccx, cy, r, 11.0, COPPER, slot_deg=30.0, slot_center_deg=0.0)
    place(cv, ccx + r + gap + tw/2, cy, size, COPPER)
    caption(cv, ox+50, oy+50, 'C  ·  SÍMBOLO + LOGOTIPO, RANURA ENFRENTADA AL TEXTO')

# ---------- D · la "o" de Studios es el círculo
def vD(ox, oy):
    cy = oy+600
    size = 96
    run = sal.shape(BRAND, size=size)
    idx = [i for i,g in enumerate(run['glyphs']) if g['name']=='o'][-1]
    og  = run['glyphs'][idx]
    x0  = ox + (1200 - run['width'])/2.0
    base = cy - BAND*size
    for i, g in enumerate(run['glyphs']):
        if i == idx or g['name'] == 'space': continue
        cv.draw(tk.translate(sal.glyph_path(g['gid'], size), x0+g['x'], base+g['y']), COPPER)
    ob = tk.bbox(sal.glyph_path(og['gid'], size))
    ocx = x0 + og['x'] + (ob[0]+ob[2])/2.0
    ocy = base + (ob[1]+ob[3])/2.0
    orx = (ob[2]-ob[0])/2.0
    ring(cv, ocx, ocy, orx*1.10, 6.5, COPPER, slot_deg=34.0, slot_center_deg=172.0)
    caption(cv, ox+50, oy+50, 'D  ·  LA “O” DE STUDIOS ES EL CÍRCULO, CON SU RANURA')

vA(  30, 1230)
vB(1230, 1230)
vC(  30,   30)
vD(1230,   30)

cv.save_png('design/logo/sheet-conceptos.png')
cv.save_svg('design/logo/sheet-conceptos.svg', bg=True)
print('ok')
