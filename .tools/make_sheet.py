"""Genera la hoja de conceptos del logo: círculo cobre con ranura sobre negro."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canvas import Canvas
import typekit as tk
import brandkit as bk

SALINA = 'Salina-SwExtraLightItalic.otf'
ARIAL  = '/System/Library/Fonts/Supplemental/Arial.ttf'

sal = tk.Font(SALINA)
arl = tk.Font(ARIAL)
wm  = bk.Wordmark(sal)
BRAND = 'Shengyin Studios'


def label(cv, x, y, txt):
    cv.text(arl, txt, x, y, 21, (0.45, 0.42, 0.39), tracking=1.1)


# ---------------------------------------------------------------- conceptos
def concepto_A(cv, ox, oy, w, h, slot_deg=30.0, two=False, size=None):
    """Círculo envolvente; la ranura queda en la banda de las letras."""
    cx, cy = ox + w/2.0, oy + h/2.0
    if size is None:
        size = min(h * 0.34, (w - 240) / (wm.width(1.0)))
    tw = wm.width(size)
    r  = tw/2.0 + size*0.85
    grosor = max(2.0, r*0.055)
    # la banda de las letras, en y
    banda_y = cy + size*(0.10)          # ligero ajuste óptico
    baseline = banda_y + size*bk.BANDA
    # la ranura se sitúa donde el círculo cruza esa banda
    dy = banda_y - cy
    import math
    if abs(dy) < r:
        ang = math.degrees(math.asin(max(-1.0, min(1.0, dy/r))))
    else:
        ang = 0.0
    cv.draw(bk.slot_ring_path(cx, cy, r, grosor, slot_deg, ang), bk.COBRE)
    if two:
        cv.draw(bk.slot_ring_path(cx, cy, r, grosor, slot_deg, 180 - ang), bk.COBRE)
    paths, run, x0 = wm.paths(cx, baseline, size)
    cv.draw(paths, bk.COBRE)
    return cx, cy, r


def concepto_C(cv, ox, oy, w, h, slot_deg=32.0):
    """Símbolo (círculo con ranura) + logotipo a la derecha."""
    cy = oy + h/2.0
    size = h*0.34
    tw = wm.width(size)
    r = size*0.98
    gap = size*0.62
    total = 2*r + gap + tw
    left = ox + (w - total)/2.0
    ccx = left + r
    banda_y = cy + size*0.10
    baseline = banda_y + size*bk.BANDA
    cv.draw(bk.slot_ring_path(ccx, cy, r, max(2.0, r*0.062), slot_deg, 0.0), bk.COBRE)
    paths, run, x0 = wm.paths(ccx + r + gap + tw/2.0, baseline, size)
    cv.draw(paths, bk.COBRE)


def concepto_D(cv, ox, oy, w, h, slot_deg=34.0):
    """La 'o' final de Studios ES el círculo, con su ranura."""
    cy = oy + h/2.0
    size = h*0.34
    banda_y = cy + size*0.10
    baseline = banda_y + size*bk.BANDA
    cx = ox + w/2.0
    paths, run, x0 = wm.paths(cx, baseline, size, replace_last_o=True)
    cv.draw(paths, bk.COBRE)
    ob = wm.last_o_box(size)
    ocx = cx + (ob[0]+ob[2])/2.0
    ocy = baseline - (ob[1]+ob[3])/2.0
    orx = (ob[2]-ob[0])/2.0
    cv.draw(bk.slot_ring_path(ocx, ocy, orx*1.06, max(1.5, orx*0.11), slot_deg, 205.0), bk.COBRE)


def concepto_E(cv, ox, oy, w, h, slot_deg=26.0):
    """Círculo grande, logotipo dentro, dos ranuras donde pasan las letras."""
    cx, cy = ox + w/2.0, oy + h/2.0
    size = h*0.20
    tw = wm.width(size)
    r = max(tw/2.0 + size*1.6, h*0.40)
    banda_y = cy + size*0.10
    baseline = banda_y + size*bk.BANDA
    import math
    dy = banda_y - cy
    ang = math.degrees(math.asin(max(-1.0, min(1.0, dy/r)))) if abs(dy) < r else 0.0
    g = max(2.0, r*0.045)
    cv.draw(bk.slot_ring_path(cx, cy, r, g, slot_deg, ang), bk.COBRE)
    cv.draw(bk.slot_ring_path(cx, cy, r, g, slot_deg, 180 - ang), bk.COBRE)
    paths, run, x0 = wm.paths(cx, baseline, size)
    cv.draw(paths, bk.COBRE)


# ---------------------------------------------------------------- hoja
W = H = 2600
cv = Canvas(W, H, bk.NEGRO)
PAD = 70
CW, CH = (W - PAD*3)/2.0, (H - PAD*3)/2.0

concepto_A(cv, PAD,           PAD,           CW, CH, slot_deg=30.0)
concepto_A(cv, PAD*2 + CW,    PAD,           CW, CH, slot_deg=26.0, two=True)
concepto_C(cv, PAD,           PAD*2 + CH,    CW, CH)
concepto_D(cv, PAD*2 + CW,    PAD*2 + CH,    CW, CH)

label(cv, PAD+16,           PAD+16,            'A  ·  UNA RANURA, EN LA BANDA DE LAS LETRAS')
label(cv, PAD*2+CW+16,      PAD+16,            'B  ·  DOS RANURAS: EL INFINITO SE ROMPE DONDE PASAN LAS LETRAS')
label(cv, PAD+16,           PAD*2+CH+16,       'C  ·  SÍMBOLO + LOGOTIPO')
label(cv, PAD*2+CW+16,      PAD*2+CH+16,       'D  ·  LA “O” DE STUDIOS ES EL CÍRCULO')

cv.save_png('design/logo/sheet-conceptos.png')
cv.save_svg('design/logo/sheet-conceptos.svg', bg=True)
print('hoja de conceptos ->', W, 'x', H)
