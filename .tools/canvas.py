"""Compose shapes/glyph runs into a single canvas that emits BOTH PNG and SVG."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import math
import typekit as tk


class Canvas:
    def __init__(self, W, H, bg=(1.0,1.0,1.0)):
        self.W, self.H = W, H
        self.bg = bg
        self.buf = bytearray(int(255*bg[0]+.5) for _ in range(1)) * 0  # placeholder
        self.buf = bytearray(W*H*4)
        for i in range(W*H):
            j = i*4
            self.buf[j]   = int(255*bg[0]+0.5)
            self.buf[j+1] = int(255*bg[1]+0.5)
            self.buf[j+2] = int(255*bg[2]+0.5)
            self.buf[j+3] = 255
        self.shapes = []

    # ---- primitives ----
    def draw(self, subpaths, fill=(0.07,0.07,0.07), opacity=1.0, record=True):
        if not subpaths: return self
        xs, ys = [], []
        for start, segs in subpaths:
            for p in [start] + [q for s in segs for q in s[1:]]:
                xs.append(p[0]); ys.append(p[1])
        if not xs: return self
        viewport = (math.floor(min(xs))-2, math.floor(self.H - max(ys))-2,
                    (max(xs)-min(xs))+5, (max(ys)-min(ys))+5)
        cov, vx0, vy0, vw, vh = tk.coverage(subpaths, self.W, self.H, (0.0,0.0), viewport)
        if vw > 0 and vh > 0:
            fr, fg, fb = fill
            buf = self.buf
            W = self.W
            for r in range(vh):
                crow = r*vw
                brow = ((vy0 + r)*W + vx0)*4
                for col in range(vw):
                    a = cov[crow + col]*opacity
                    if a <= 0.0: continue
                    j = brow + col*4
                    buf[j]   = int(buf[j]  *(1-a) + 255*fr*a + 0.5)
                    buf[j+1] = int(buf[j+1]*(1-a) + 255*fg*a + 0.5)
                    buf[j+2] = int(buf[j+2]*(1-a) + 255*fb*a + 0.5)
        if record:
            self.shapes.append((tk.subpaths_to_d(subpaths), fill, opacity))
        return self

    def rect(self, x, y, w, h, fill=(0,0,0), opacity=1.0, radius=0.0):
        if radius <= 0:
            sp = [((x,y), [('L',(x+w,y)),('L',(x+w,y+h)),('L',(x,y+h))])]
        else:
            k = radius*0.5523
            sp = [((x+radius, y), [
                ('L',(x+w-radius, y)),
                ('C',(x+w-radius+k, y),(x+w, y+radius-k),(x+w, y+radius)),
                ('L',(x+w, y+h-radius)),
                ('C',(x+w, y+h-radius+k),(x+w-radius+k, y+h),(x+w-radius, y+h)),
                ('L',(x+radius, y+h)),
                ('C',(x+radius-k, y+h),(x, y+h-radius+k),(x, y+h-radius)),
                ('L',(x, y+radius)),
                ('C',(x, y+radius-k),(x+radius-k, y),(x+radius, y)),
            ])]
        return self.draw(sp, fill, opacity)

    def line(self, x1, y1, x2, y2, w, fill=(0,0,0), opacity=1.0, round_caps=False):
        import math
        dx, dy = x2-x1, y2-y1
        L = math.hypot(dx, dy)
        if L == 0: return self
        nx, ny = -dy/L*w/2.0, dx/L*w/2.0
        sp = [((x1+nx, y1+ny), [('L',(x2+nx, y2+ny)),('L',(x2-nx, y2-ny)),('L',(x1-nx, y1-ny))])]
        if round_caps:
            r = w/2.0
            for cx, cy in ((x1,y1),(x2,y2)):
                sp.append(((cx+r, cy), [
                    ('C',(cx+r, cy+r*0.5523),(cx+r*0.5523, cy+r),(cx, cy+r)),
                    ('C',(cx-r*0.5523, cy+r),(cx-r, cy+r*0.5523),(cx-r, cy)),
                    ('C',(cx-r, cy-r*0.5523),(cx-r*0.5523, cy-r),(cx, cy-r)),
                    ('C',(cx+r*0.5523, cy-r),(cx+r, cy-r*0.5523),(cx+r, cy)),
                ]))
        return self.draw(sp, fill, opacity)

    def circle(self, cx, cy, r, fill=(0,0,0), opacity=1.0):
        k = r*0.5523
        sp = [((cx+r, cy), [
            ('C',(cx+r, cy+k),(cx+k, cy+r),(cx, cy+r)),
            ('C',(cx-k, cy+r),(cx-r, cy+k),(cx-r, cy)),
            ('C',(cx-r, cy-k),(cx-k, cy-r),(cx, cy-r)),
            ('C',(cx+k, cy-r),(cx+r, cy-k),(cx+r, cy)),
        ])]
        return self.draw(sp, fill, opacity)

    def ring(self, cx, cy, r, w, fill=(0,0,0), opacity=1.0):
        self.circle(cx, cy, r, fill, opacity)
        return self.circle(cx, cy, max(0.0, r-w), tuple(1.0 if c == 0 else c for c in (0,0,0)), 1.0) if False else self._knockout_circle(cx, cy, r-w)

    def _knockout_circle(self, cx, cy, r):
        # erase by drawing background colour (keeps PNG/SVG simple)
        return self.circle(cx, cy, r, self.bg, 1.0)

    # ---- text ----
    def text(self, font, s, x, y, size, fill=(0.07,0.07,0.07), features=None,
             tracking=0.0, anchor='start', opacity=1.0):
        run = font.shape(s, features=features, size=size)
        if anchor == 'middle': x -= run["width"]/2.0
        elif anchor == 'end':   x -= run["width"]
        subs = tk.run_to_subpaths(font, run, x=x, y=y, tracking=tracking)
        self.draw(subs, fill, opacity)
        return run["width"]

    def text_width(self, font, s, size, features=None, tracking=0.0):
        run = font.shape(s, features=features, size=size)
        n = len(run["glyphs"])
        return run["width"] + tracking*max(0, n-1)

    # ---- output ----
    def save_png(self, path):
        tk.write_png(path, self.buf, self.W, self.H)
        return path

    def save_svg(self, path, width_attr=True, bg=True):
        parts = []
        if bg and self.bg:
            parts.append('<rect width="%d" height="%d" fill="%s"/>' % (
                self.W, self.H, _hex(self.bg)))
        for d, fill, op in self.shapes:
            o = '' if op >= 1.0 else ' fill-opacity="%g"' % op
            parts.append('<path d="%s" fill="%s"%s fill-rule="nonzero"/>' % (d, _hex(fill), o))
        wa = ' width="%d" height="%d"' % (self.W, self.H) if width_attr else ''
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d"%s>\n  %s\n</svg>\n'
               % (self.W, self.H, wa, "\n  ".join(parts)))
        open(path, 'w').write(svg)
        return path


def _hex(c):
    if isinstance(c, str): return c
    return '#%02x%02x%02x' % tuple(max(0, min(255, int(255*v+0.5))) for v in c[:3])
