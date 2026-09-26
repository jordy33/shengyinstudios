import sys, os
sys.path.insert(0, '.tools')
from canvas import Canvas
import typekit as tk

SALINA = 'Salina-SwExtraLightItalic.otf'
ARIAL  = '/System/Library/Fonts/Supplemental/Arial.ttf'
ARIALB = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'

sal = tk.Font(SALINA)
arl = tk.Font(ARIAL)
arb = tk.Font(ARIALB)

W, H = 2900, 2050
c = Canvas(W, H, (1.0, 1.0, 1.0))
INK   = (0.09, 0.09, 0.11)
GREY  = (0.52, 0.52, 0.55)
RULE  = (0.87, 0.87, 0.88)
ACC   = (0.72, 0.16, 0.20)

curs = H - 105

# ---------- title ----------
c.text(sal, 'Salina Swashes ExtraLight Italic', 95, curs, 96, INK)
curs -= 52
c.text(arl, 'LECTURA TIPOGRÁFICA DEL ARCHIVO  ·  Salina-SwExtraLightItalic.otf  ·  SHA-256 586d692c...178c',
       95, curs, 24, GREY, tracking=0.6)
curs -= 44
c.line(95, curs, W-95, curs, 2.0, RULE)
curs -= 70

def row(label, text, size, feats=None, tracking=0.0, color=INK, gap=95, note=None):
    global curs
    c.text(arb, label, 95, curs, 25, GREY, tracking=1.6)
    if note:
        wlab = c.text_width(arb, label, 25, tracking=1.6)
        c.text(arl, note, 95 + wlab + 26, curs, 24, ACC, tracking=0.3)
    curs -= 30
    c.draw(tk.run_to_subpaths(sal, sal.shape(text, feats, size=size), x=95, y=curs), color)
    curs -= gap

# 1. uppercase default (calt on -> swash initials + N_G ligature)
row('MAYÚSCULAS  ·  formas por defecto (calt activo: iniciales con swash)',
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 100, None, gap=88)
# 2. uppercase base
row('MAYÚSCULAS  ·  formas base (calt desactivado)',
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 100, {'calt': False}, gap=88)
# 3. lowercase
row('MINÚSCULAS  ·  cursiva didone de alto contraste',
    'abcdefghijklmnopqrstuvwxyz', 100, gap=88)
# 4. figures
row('CIFRAS Y SIGNOS  ·  proporcionales por defecto (pnum), hay tnum / onum / frac / sups',
    '0123456789  &@#?!.,:;()[]{}%/+', 96, gap=88)
# 5. accent coverage
row('ACENTOS Y DIACRÍTICOS  ·  español completo · latín extendido · cirílico · SIN caracteres CJK',
    'ÁÉÍÓÚÜÑáéíóúüñ¿¡ÇçÅØÆß', 92, gap=88)
curs -= 12
c.line(95, curs, W-95, curs, 2.0, RULE)
curs -= 78

# 6. the mark candidates
row('MARCA  ·  title case', 'Shengyin Studios', 150, gap=190)
row('MARCA  ·  versales (aparece la ligadura N_G y las iniciales con swash)', 'SHENGYIN STUDIOS', 150, gap=175)
row('DETALLE  ·  SHENGYIN en grande: ligadura N_G + S inicial con swash', 'SHENGYIN', 210, gap=60)

c.save_png('design/01-font-readout.png')
c.save_svg('design/01-font-readout.svg', bg=True)
print('saved readout')
