"""Type toolkit: HarfBuzz shaping -> fontTools outlines -> SVG paths + raster preview.
Internal coordinate model: FONT units, y-UP, baseline at y=0 (as in the font).
SVG output flips y. The rasterizer flips y internally."""
import math, zlib, struct
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen


def _flatten_cubic(p0, p1, p2, p3, tol=0.06):
    out = []
    stack = [(p0, p1, p2, p3, 0)]
    while stack:
        a, b, c, d, depth = stack.pop()
        dx = d[0]-a[0]; dy = d[1]-a[1]
        d1 = abs((b[0]-d[0])*dy - (b[1]-d[1])*dx)
        d2 = abs((c[0]-d[0])*dy - (c[1]-d[1])*dx)
        if depth > 18 or ((d1+d2)**2 <= tol*(dx*dx+dy*dy)):
            out.append(d)
        else:
            def mid(p, q): return ((p[0]+q[0])/2.0, (p[1]+q[1])/2.0)
            a1 = mid(a,b); a2 = mid(b,c); a3 = mid(c,d)
            b1 = mid(a1,a2); b2 = mid(a2,a3); cc = mid(b1,b2)
            stack.append((cc, b2, a3, d, depth+1))
            stack.append((a, a1, b1, cc, depth+1))
    return out


class PathPen(BasePen):
    """Records subpaths as [start, [('L',pt) | ('C',c1,c2,pt), ...]] with optional affine tf."""
    def __init__(self, glyphSet=None, tf=None):
        super().__init__(glyphSet)
        self.subpaths = []
        self.cur = None
        self.tf = tf or (1,0,0,1,0,0)

    def _t(self, pt):
        a,b,c,d,e,f = self.tf
        return (pt[0]*a + pt[1]*c + e, pt[0]*b + pt[1]*d + f)

    def _moveTo(self, pt):
        self.cur = [self._t(pt), []]
        self.subpaths.append(self.cur)

    def _lineTo(self, pt):
        self.cur[1].append(('L', self._t(pt)))

    def _curveToOne(self, p1, p2, p3):
        self.cur[1].append(('C', self._t(p1), self._t(p2), self._t(p3)))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[1][-1][-1] if self.cur[1] else self.cur[0]
        c1 = (p0[0] + 2.0/3*(p1[0]-p0[0]), p0[1] + 2.0/3*(p1[1]-p0[1]))
        c2 = (p2[0] + 2.0/3*(p1[0]-p2[0]), p2[1] + 2.0/3*(p1[1]-p2[1]))
        self.cur[1].append(('C', self._t(c1), self._t(c2), self._t(p2)))

    def _closePath(self): self.cur = None
    def _endPath(self): self.cur = None


class Font:
    def __init__(self, path):
        self.path = path
        self.blob = hb.Blob.from_file_path(path)
        self.face = hb.Face(self.blob)
        self.hbfont = hb.Font(self.face)
        self.tt = TTFont(path)
        self.upem = self.tt["head"].unitsPerEm
        self.glyphset = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()

    def shape(self, text, features=None, size=1000.0):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf, features or {})
        s = size / self.upem
        glyphs, x = [], 0.0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            glyphs.append(dict(name=self.order[info.codepoint], gid=info.codepoint,
                               x=x + pos.x_offset*s, y=pos.y_offset*s,
                               x_adv=pos.x_advance*s, cluster=info.cluster))
            x += pos.x_advance * s
        return dict(glyphs=glyphs, width=x, size=size, text=text, features=features or {})

    def glyph_path(self, gid, size, tf=None):
        s = size / self.upem
        base = (s, 0.0, 0.0, s, 0.0, 0.0)
        if tf:
            a,b,c,d,e,f = tf
            # apply extra transform on top of scale
            base = (s*a, s*b, s*c, s*d, e, f)
        pen = PathPen(self.glyphset, base)
        self.glyphset[self.order[gid]].draw(pen)
        return pen.subpaths


def bbox(subpaths):
    xs, ys = [], []
    for start, segs in subpaths:
        pts = [start] + [p for s in segs for p in s[1:]]
        for p in pts: xs.append(p[0]); ys.append(p[1])
    if not xs: return (0,0,0,0)
    return (min(xs), min(ys), max(xs), max(ys))


def translate(subpaths, dx=0.0, dy=0.0):
    def T(p): return (p[0]+dx, p[1]+dy)
    return [(T(start), [(s[0],) + tuple(T(p) for p in s[1:]) for s in segs]) for start, segs in subpaths]


def scale_pts(subpaths, sx, sy=None, ox=0.0, oy=0.0):
    sy = sx if sy is None else sy
    def T(p): return (ox + p[0]*sx, oy + p[1]*sy)
    return [(T(start), [(s[0],) + tuple(T(p) for p in s[1:]) for s in segs]) for start, segs in subpaths]


def shear(subpaths, k):
    """Horizontal shear: x' = x + k*y (extra slant)."""
    def T(p): return (p[0] + k*p[1], p[1])
    return [(T(start), [(s[0],) + tuple(T(p) for p in s[1:]) for s in segs]) for start, segs in subpaths]


def run_to_subpaths(font, run, x=0.0, y=0.0, tracking=0.0, justify=None):
    """Coloca una tirada compuesta. Salida en unidades de fuente (y ARRIBA), con la
    línea base en y. El rasterizador y subpaths_to_d se encargan del volteo vertical."""
    out = []
    n = len(run["glyphs"])
    extra = 0.0
    if justify is not None and n > 1:
        total = run["width"] + tracking*(n-1)
        extra = (justify - total)/(n-1)
    for i, g in enumerate(run["glyphs"]):
        if g["name"] == "space": continue
        subs = font.glyph_path(g["gid"], run["size"])
        out += translate(subs, x + g["x"] + i*(tracking+extra), y + g["y"])
    return out


def subpaths_to_d(subpaths, prec=2):
    def f(v):
        s = f"{v:.{prec}f}"
        if '.' in s: s = s.rstrip('0').rstrip('.')
        return s if s not in ('-0','') else '0'
    parts = []
    for start, segs in subpaths:
        parts.append(f"M{f(start[0])} {f(-start[1])}")
        for s in segs:
            if s[0] == 'L':
                parts.append(f"L{f(s[1][0])} {f(-s[1][1])}")
            else:
                parts.append("C" + " ".join(f"{f(p[0])} {f(-p[1])}" for p in s[1:]))
        parts.append("Z")
    return "".join(parts)


def to_svg(path_d, W, H, fill="#111111", bg=None, extra=""):
    b = f'<rect width="{W}" height="{H}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'{b}<path d="{path_d}" fill="{fill}" fill-rule="nonzero"/>{extra}</svg>')


def coverage(subpaths, W, H, translate_px=(0.0,0.0), viewport=None):
    """Global nonzero-winding coverage. Input y-UP font coords; pixels y-down.
    viewport=(x0,y0,w,h) in pixel space limits the work. Returns (cov, x0, y0, w, h)."""
    tx, ty = translate_px
    if viewport is None:
        vx0, vy0, vw, vh = 0, 0, W, H
    else:
        # el viewport se RECORTA al lienzo y el ancho/alto se recalcula tras el recorte
        vx0 = max(0, int(math.floor(viewport[0])))
        vy0 = max(0, int(math.floor(viewport[1])))
        vx1 = min(W, int(math.ceil(viewport[0] + viewport[2])))
        vy1 = min(H, int(math.ceil(viewport[1] + viewport[3])))
        vw, vh = vx1 - vx0, vy1 - vy0
        if vw <= 0 or vh <= 0:
            return [], vx0, vy0, 0, 0
    edges = []
    exmin = exmax = None
    for start, segs in subpaths:
        pts = [(start[0]+tx, H - (start[1]+ty))]
        for s in segs:
            if s[0] == 'L':
                pts.append((s[1][0]+tx, H - (s[1][1]+ty)))
            else:
                for p in _flatten_cubic(pts[-1], (s[1][0]+tx, H-(s[1][1]+ty)),
                                        (s[2][0]+tx, H-(s[2][1]+ty)), (s[3][0]+tx, H-(s[3][1]+ty))):
                    pts.append(p)
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]; x2, y2 = pts[(i+1) % n]
            if y1 != y2:
                edges.append((x1, y1, x2, y2))

    # Cobertura vertical EXACTA por aristas: sin supersampling en Y.
    # Cada arista aporta peso 'dy' a las filas que solapa en la banda [vy0, vy0+vh).
    N = vh
    buckets = [[] for _ in range(N)]
    for ei, (x1, y1, x2, y2) in enumerate(edges):
        if y1 < y2: ylo, yhi = y1, y2
        else:       ylo, yhi = y2, y1
        if yhi <= vy0 or ylo >= vy0 + vh: continue
        ylo = max(ylo, float(vy0)); yhi = min(yhi, float(vy0 + vh))
        ja = int(ylo) - vy0
        jb = min(N - 1, int(math.ceil(yhi)) - 1 - vy0)
        for j in range(ja, jb+1):
            buckets[j].append((ei, max(0.0, min(yhi, j+1+vy0) - max(ylo, j+vy0))))

    cov = [0.0] * (vw * N)
    for jr in range(N):
        bl = buckets[jr]
        if not bl: continue
        yc = jr + vy0 + 0.5
        xs = []
        for ei, wgt in bl:
            x1, y1, x2, y2 = edges[ei]
            if y1 == y2: continue
            lo, hi = (y1, y2) if y1 < y2 else (y2, y1)
            if lo <= yc < hi:
                t = (yc - y1)/(y2 - y1)
                xs.append((x1 + t*(x2-x1), wgt if y2 > y1 else -wgt))
        if not xs: continue
        xs.sort(key=lambda v: v[0])
        wind = 0.0
        row = jr*vw
        m = len(xs)
        for i in range(m-1):
            wind += xs[i][1]
            if wind != 0.0:
                xa, xb = xs[i][0], xs[i+1][0]
                if xb <= vx0 or xa >= vx0+vw: continue
                if xa < vx0: xa = float(vx0)
                if xb > vx0+vw: xb = float(vx0+vw)
                ia = int(xa) - vx0; ib = int(math.ceil(xb)) - 1 - vx0
                # recorte duro al ancho de fila del buffer
                if ia < 0: ia = 0
                if ib > vw-1: ib = vw-1
                if ib < ia: continue
                if ia == ib:
                    cov[row+ia] += wind*(xb - xa)
                else:
                    cov[row+ia] += wind*(ia + vx0 + 1 - xa)
                    for px in range(ia+1, ib):
                        cov[row+px] += wind
                    cov[row+ib] += wind*(xb - (ib + vx0))

    for i in range(vw*N):
        v = cov[i]
        cov[i] = 1.0 if v > 1.0 else (0.0 if v < 0.0 else v)
    return cov, vx0, vy0, vw, vh


def rasterize(subpaths, W, H, fill=(0.07,0.07,0.07), bg=(1.0,1.0,1.0), translate_px=(0.0,0.0)):
    c,_,_,_,_ = coverage(subpaths, W, H, translate_px=translate_px)
    fr, fg, fb = fill
    br, bgc, bb = bg
    img = bytearray(W*H*4)
    for i in range(W*H):
        a = c[i]
        j = i*4
        img[j]   = int(255*(fr*a + br*(1-a)) + 0.5)
        img[j+1] = int(255*(fg*a + bgc*(1-a)) + 0.5)
        img[j+2] = int(255*(fb*a + bb*(1-a)) + 0.5)
        img[j+3] = 255
    return img


def write_png(path, img, W, H):
    raw = bytearray()
    for y in range(H):
        raw.append(0); raw += img[y*W*4:(y+1)*W*4]
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t+d) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    open(path,'wb').write(png)
