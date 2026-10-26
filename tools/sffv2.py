"""Minimal SFF v2.00 writer/reader (Elecbyte sprite format used by MUGEN 1.x / Ikemen GO).

Sprites are 8-bit indexed, RLE8-compressed. Palette index 0 is always transparent.
Layout follows the loader in Ikemen GO (src/image.go: SffHeader.Read, readHeaderV2,
readV2, loadPalettes)."""
import struct

SIG = b"ElecbyteSpr\x00"


def rle8_encode(px: bytes) -> bytes:
    out = bytearray()
    i, n = 0, len(px)
    while i < n:
        c = px[i]
        run = 1
        while i + run < n and px[i + run] == c and run < 63:
            run += 1
        if run > 1 or (c & 0xC0) == 0x40:
            out.append(0x40 | run)
            out.append(c)
        else:
            out.append(c)
        i += run
    return bytes(out)


def rle8_decode(rle: bytes, size: int) -> bytes:
    p = bytearray()
    i = 0
    while len(p) < size and i < len(rle):
        d = rle[i]; i += 1
        n = 1
        if d & 0xC0 == 0x40:
            n = d & 0x3F
            d = rle[i]; i += 1
        p.extend([d] * n)
    return bytes(p[:size])


class SffWriter:
    """palettes: list of (group, item, [(r,g,b)*<=256]).
    sprites: list of dict(group, number, w, h, ax, ay, pixels(bytes), pal(int index into palettes))"""

    def __init__(self):
        self.palettes = []
        self.sprites = []
        self._keys = set()

    def add_palette(self, group, item, colors):
        assert len(colors) <= 256
        self.palettes.append((group, item, list(colors)))
        return len(self.palettes) - 1

    def add_sprite(self, group, number, w, h, ax, ay, pixels, pal):
        key = (group, number)
        if key in self._keys:
            raise ValueError("duplicate sprite %s" % (key,))
        self._keys.add(key)
        assert len(pixels) == w * h, (group, number, w, h, len(pixels))
        self.sprites.append(dict(group=group, number=number, w=w, h=h, ax=ax, ay=ay,
                                 pixels=bytes(pixels), pal=pal))

    def write(self, path):
        # ldata: palettes ; tdata: sprite data
        ldata = bytearray()
        pal_nodes = []
        for g, it, cols in self.palettes:
            cols = cols + [(0, 0, 0)] * (256 - len(cols))
            off = len(ldata)
            for r, gg, b in cols:
                ldata += bytes((r, gg, b, 0))
            pal_nodes.append(struct.pack("<HHHHII", g, it, 256, 0, off, 256 * 4))
        tdata = bytearray()
        spr_nodes = []
        dedup = {}
        for idx, s in enumerate(self.sprites):
            dkey = (s["w"], s["h"], s["pixels"], s["pal"])
            if dkey in dedup:  # linked sprite (same image)
                link = dedup[dkey]
                spr_nodes.append(struct.pack("<HHHHhhHBBIIHH", s["group"], s["number"], s["w"], s["h"],
                                             s["ax"], s["ay"], link, 2, 8, 0, 0, s["pal"], 1))
                continue
            dedup[dkey] = idx
            enc = struct.pack("<I", len(s["pixels"])) + rle8_encode(s["pixels"])
            off = len(tdata)
            tdata += enc
            spr_nodes.append(struct.pack("<HHHHhhHBBIIHH", s["group"], s["number"], s["w"], s["h"],
                                         s["ax"], s["ay"], 0, 2, 8, off, len(enc), s["pal"], 1))
        hdr_size = 512
        spr_off = hdr_size
        pal_off = spr_off + 28 * len(spr_nodes)
        l_off = pal_off + 16 * len(pal_nodes)
        t_off = l_off + len(ldata)
        hdr = bytearray(SIG)
        hdr += bytes((0, 0, 0, 2))           # verlo3 verlo2 verlo1 verhi -> 2.00
        hdr += struct.pack("<II", 0, 0)       # reserved
        hdr += bytes((0, 0, 0, 2))           # compat version
        hdr += struct.pack("<II", 0, 0)       # reserved
        hdr += struct.pack("<IIII", spr_off, len(spr_nodes), pal_off, len(pal_nodes))
        hdr += struct.pack("<IIII", l_off, len(ldata), t_off, len(tdata))
        hdr += struct.pack("<II", 0, 0)
        hdr += b"\x00" * (hdr_size - len(hdr))
        assert len(hdr) == 512
        with open(path, "wb") as f:
            f.write(hdr)
            for n in spr_nodes:
                f.write(n)
            for n in pal_nodes:
                f.write(n)
            f.write(ldata)
            f.write(tdata)


def read_sff(path):
    """Reader mirroring Ikemen GO's v2 loader; returns (palettes, sprites dict)."""
    d = open(path, "rb").read()
    assert d[:12] == SIG
    ver = d[15]
    assert ver == 2, "only v2"
    spr_off, nspr, pal_off, npal = struct.unpack_from("<IIII", d, 36)
    l_off, l_len, t_off, t_len = struct.unpack_from("<IIII", d, 52)
    pals = []
    for i in range(npal):
        g, it, nc, link, off, ln = struct.unpack_from("<HHHHII", d, pal_off + 16 * i)
        raw = d[l_off + off:l_off + off + ln]
        pals.append(((g, it), [tuple(raw[j * 4:j * 4 + 3]) for j in range(ln // 4)]))
    sprites = {}
    order = []
    for i in range(nspr):
        g, n, w, h, ax, ay, link, fmt, depth, off, ln, pal, flags = struct.unpack_from(
            "<HHHHhhHBBIIHH", d, spr_off + 28 * i)
        base = t_off if flags & 1 else l_off
        if ln == 0:
            src = order[link]
            px = sprites[src]["pixels"]
        else:
            assert fmt == 2
            raw = d[base + off: base + off + ln]
            (usize,) = struct.unpack_from("<I", raw, 0)
            assert usize == w * h
            px = rle8_decode(raw[4:], w * h)
        sprites[(g, n)] = dict(w=w, h=h, ax=ax, ay=ay, pixels=px, pal=pal)
        order.append((g, n))
    return pals, sprites
