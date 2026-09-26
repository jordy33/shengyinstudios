"""Lector de PNG mínimo (soporta los 5 filtros). Devuelve filas RGBA."""
import zlib, struct

def readpng(path):
    d = open(path,'rb').read()
    pos = 8; W = H = None; idat = b''
    while pos < len(d):
        ln = struct.unpack('>I', d[pos:pos+4])[0]
        t = d[pos+4:pos+8]; ch = d[pos+8:pos+8+ln]
        if t == b'IHDR':
            W, H, bd, ct = struct.unpack('>IIBB', ch[:10])
        elif t == b'IDAT':
            idat += ch
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = W*4
    out = []; prev = bytearray(stride); i = 0
    for y in range(H):
        ft = raw[i]; i += 1
        line = bytearray(raw[i:i+stride]); i += stride
        if ft == 1:
            for x in range(4, stride): line[x] = (line[x] + line[x-4]) & 255
        elif ft == 2:
            for x in range(stride): line[x] = (line[x] + prev[x]) & 255
        elif ft == 3:
            for x in range(stride):
                a = line[x-4] if x >= 4 else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif ft == 4:
            for x in range(stride):
                a = line[x-4] if x >= 4 else 0
                b = prev[x]
                c = prev[x-4] if x >= 4 else 0
                p = a + b - c
                pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        out.append(bytes(line)); prev = line
    return W, H, out


def ink(path):
    """Devuelve (W,H,get) con get(x,y) = cobertura de tinta 0..1 (asume negro sobre blanco)."""
    W, H, rows = readpng(path)
    return W, H, (lambda x, y: 1.0 - rows[y][x*4]/255.0)
