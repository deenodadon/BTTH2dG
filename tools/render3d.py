"""Tiny software renderer for "2.5D" pre-rendered fighter sprites.

Characters are built from analytic 3D primitives (tapered capsules, ellipsoids,
bevelled slabs) seen through an orthographic camera.  Each primitive writes
depth + normal into a z-buffer; the result is cel-shaded (three light bands,
rim light, specular on hair/metal) and outlined, imitating the 3D-CG look of
the Battle Through the Heavens donghua.

World units: x forward (character faces +x), y up, z toward the camera.
One world unit == one pixel in the final sprite.
"""
import math

import numpy as np

SS = 2  # supersampling factor

LIGHT = np.array([0.42, 0.62, 0.66])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
HALF = LIGHT + np.array([0, 0, 1.0])
HALF = HALF / np.linalg.norm(HALF)


class Mat:
    """Surface material."""

    def __init__(self, color, spec=0.0, shade=1.0, emissive=0.0, outline=0.28, rim=0.18,
                 shadow_tint=(0.86, 0.86, 1.0), bands=(0.45, 0.05), name=""):
        self.color = np.array(color, dtype=np.float32)
        self.spec = spec
        self.shade = shade
        self.emissive = emissive
        self.outline = outline
        self.rim = rim
        self.shadow_tint = np.array(shadow_tint, dtype=np.float32)
        self.bands = bands
        self.name = name

    def darker(self, k):
        m = Mat(self.color, self.spec, self.shade * k, self.emissive, self.outline, self.rim,
                self.shadow_tint, self.bands, self.name)
        return m

    def with_color(self, color):
        m = Mat(color, self.spec, self.shade, self.emissive, self.outline, self.rim,
                self.shadow_tint, self.bands, self.name)
        return m


class Canvas:
    def __init__(self, xmin=-200, xmax=200, ymin=-30, ymax=330):
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.W = int((xmax - xmin) * SS)
        self.H = int((ymax - ymin) * SS)
        self.depth = np.full((self.H, self.W), -1e9, dtype=np.float32)
        self.nrm = np.zeros((self.H, self.W, 3), dtype=np.float32)
        self.mid = np.full((self.H, self.W), -1, dtype=np.int32)
        self.pid = np.full((self.H, self.W), -1, dtype=np.int32)
        self.mats = []
        self._matidx = {}
        self.npid = 0
        # optional per-pixel color override (bands / decals)
        self.col = np.zeros((self.H, self.W, 3), dtype=np.float32)
        self.hascol = np.zeros((self.H, self.W), dtype=bool)

    # -- coordinate helpers -------------------------------------------------
    def _bbox(self, x0, y0, x1, y1):
        """world bbox -> pixel slice bounds, clipped. returns None if empty."""
        c0 = int(math.floor((x0 - self.xmin) * SS))
        c1 = int(math.ceil((x1 - self.xmin) * SS)) + 1
        r0 = int(math.floor((self.ymax - y1) * SS))
        r1 = int(math.ceil((self.ymax - y0) * SS)) + 1
        c0, r0 = max(c0, 0), max(r0, 0)
        c1, r1 = min(c1, self.W), min(r1, self.H)
        if c0 >= c1 or r0 >= r1:
            return None
        return r0, r1, c0, c1

    def _grid(self, bb):
        r0, r1, c0, c1 = bb
        xs = self.xmin + (np.arange(c0, c1, dtype=np.float32) + 0.5) / SS
        ys = self.ymax - (np.arange(r0, r1, dtype=np.float32) + 0.5) / SS
        X, Y = np.meshgrid(xs, ys)
        return X, Y

    def _mat(self, m):
        k = id(m)
        if k not in self._matidx:
            self._matidx[k] = len(self.mats)
            self.mats.append(m)
        return self._matidx[k]

    def _commit(self, bb, inside, z, nx, ny, nz, mat, colfn=None, X=None, Y=None, t=None):
        r0, r1, c0, c1 = bb
        dsub = self.depth[r0:r1, c0:c1]
        win = inside & (z > dsub)
        if not win.any():
            return
        pid = self.npid
        self.npid += 1
        dsub[win] = z[win]
        nsub = self.nrm[r0:r1, c0:c1]
        nsub[..., 0][win] = nx[win]
        nsub[..., 1][win] = ny[win]
        nsub[..., 2][win] = nz[win]
        self.mid[r0:r1, c0:c1][win] = self._mat(mat)
        self.pid[r0:r1, c0:c1][win] = pid
        hs = self.hascol[r0:r1, c0:c1]
        if colfn is not None:
            cols = colfn(X, Y, t)
            if cols is not None:
                cmask, cval = cols
                m2 = win & cmask
                csub = self.col[r0:r1, c0:c1]
                csub[m2] = cval if np.ndim(cval) == 1 else cval[m2]
                hs[m2] = True
                hs[win & ~cmask] = False
                return
        hs[win] = False

    # -- primitives -----------------------------------------------------------
    def capsule(self, a, b, ra, rb, mat, bands=None, open_end=False):
        """Tapered capsule between 3D points a,b with radii ra, rb.
        bands: list of (t0, t1, color) to recolor stretches along the capsule."""
        ax, ay, az = a
        bx, by, bz = b
        r = max(ra, rb)
        bb = self._bbox(min(ax, bx) - r, min(ay, by) - r, max(ax, bx) + r, max(ay, by) + r)
        if bb is None:
            return
        X, Y = self._grid(bb)
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 < 1e-6:
            traw = np.zeros_like(X)
        else:
            traw = ((X - ax) * dx + (Y - ay) * dy) / L2
        t = np.clip(traw, 0, 1)
        cx = ax + t * dx
        cy = ay + t * dy
        rr = ra + (rb - ra) * t
        px, py = X - cx, Y - cy
        d2 = px * px + py * py
        inside = d2 < rr * rr
        if open_end:
            inside &= traw <= 1.0
        h = np.sqrt(np.maximum(rr * rr - d2, 0))
        z = az + (bz - az) * t + h
        inv = 1.0 / np.maximum(rr, 1e-3)
        colfn = None
        if bands:
            def colfn(X_, Y_, t_):
                m = np.zeros(t_.shape, dtype=bool)
                out = np.zeros(t_.shape + (3,), dtype=np.float32)
                for t0, t1, c in bands:
                    mm = (t_ >= t0) & (t_ <= t1)
                    out[mm] = c
                    m |= mm
                return m, out
        self._commit(bb, inside, z, px * inv, py * inv, h * inv, mat, colfn, X, Y, t)

    def sphere(self, c, r, mat):
        self.capsule(c, c, r, r, mat)

    def ellipsoid(self, c, rx, ry, rz, ang, mat, bands=None):
        """Ellipsoid centred at c, radii rx (along angle `ang` deg), ry, rz.
        bands: list of (v0, v1, color) in normalised local-y (-1..1) to recolor."""
        cx, cy, cz = c
        r = max(rx, ry)
        bb = self._bbox(cx - r, cy - r, cx + r, cy + r)
        if bb is None:
            return
        X, Y = self._grid(bb)
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        u = (X - cx) * ca + (Y - cy) * sa
        v = -(X - cx) * sa + (Y - cy) * ca
        q = (u / rx) ** 2 + (v / ry) ** 2
        inside = q < 1
        hz = np.sqrt(np.maximum(1 - q, 0))
        z = cz + rz * hz
        gu, gv, gz = u / (rx * rx), v / (ry * ry), hz / rz
        gx = gu * ca - gv * sa
        gy = gu * sa + gv * ca
        n = np.sqrt(gx * gx + gy * gy + gz * gz) + 1e-6
        colfn = None
        if bands:
            vv = v / ry

            def colfn(X_, Y_, t_):
                m = np.zeros(vv.shape, dtype=bool)
                out = np.zeros(vv.shape + (3,), dtype=np.float32)
                for v0, v1, col in bands:
                    mm = (vv >= v0) & (vv <= v1)
                    out[mm] = col
                    m |= mm
                return m, out
        self._commit(bb, inside, z, gx / n, gy / n, gz / n, mat, colfn, X, Y, None)

    def slab(self, c, ang, hl, hw, thick, mat, bevel=2.5, bands=None):
        """Flat bevelled board (ruler / sword blade). centre c, half-length hl along ang (deg),
        half-width hw, thickness `thick` toward camera.  bands: (u0,u1,color) with u in -1..1."""
        cx, cy, cz = c
        r = math.hypot(hl, hw)
        bb = self._bbox(cx - r, cy - r, cx + r, cy + r)
        if bb is None:
            return
        X, Y = self._grid(bb)
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        u = (X - cx) * ca + (Y - cy) * sa
        v = -(X - cx) * sa + (Y - cy) * ca
        inside = (np.abs(u) < hl) & (np.abs(v) < hw)
        eu = np.clip((np.abs(u) - (hl - bevel)) / bevel, 0, 1) * np.sign(u)
        ev = np.clip((np.abs(v) - (hw - bevel)) / bevel, 0, 1) * np.sign(v)
        nu, nv = eu * 0.8, ev * 0.8
        nz = np.sqrt(np.maximum(1 - nu * nu - nv * nv, 0.05))
        nx = nu * ca - nv * sa
        ny = nu * sa + nv * ca
        z = cz + thick * nz
        colfn = None
        if bands:
            uu = u / hl

            def colfn(X_, Y_, t_):
                m = np.zeros(uu.shape, dtype=bool)
                out = np.zeros(uu.shape + (3,), dtype=np.float32)
                for u0, u1, col in bands:
                    mm = (uu >= u0) & (uu <= u1)
                    out[mm] = col
                    m |= mm
                return m, out
        self._commit(bb, inside, z, nx, ny, nz, mat, colfn, X, Y, None)

    def polygon(self, pts, z, mat, normal=(0, 0.3, 0.95), bulge=0.0):
        """Flat polygon (cloth panels / hair locks) at depth z with a fixed normal."""
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bb = self._bbox(min(xs), min(ys), max(xs), max(ys))
        if bb is None:
            return
        X, Y = self._grid(bb)
        inside = np.zeros(X.shape, dtype=bool)
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            cond = ((y0 > Y) != (y1 > Y))
            with np.errstate(divide="ignore", invalid="ignore"):
                xi = (x1 - x0) * (Y - y0) / (y1 - y0 + 1e-9) + x0
            inside ^= cond & (X < xi)
        nn = np.array(normal, dtype=np.float32)
        nn = nn / np.linalg.norm(nn)
        zz = np.full(X.shape, z, dtype=np.float32)
        self._commit(bb, inside, zz, np.full(X.shape, nn[0]), np.full(X.shape, nn[1]),
                     np.full(X.shape, nn[2]), mat)

    # -- shading --------------------------------------------------------------
    def shade(self):
        """Return RGBA uint8 image at final resolution and the world-space origin pixel."""
        H, W = self.H, self.W
        mask = self.mid >= 0
        rgb = np.zeros((H, W, 3), dtype=np.float32)
        N = self.nrm
        ndl = N[..., 0] * LIGHT[0] + N[..., 1] * LIGHT[1] + N[..., 2] * LIGHT[2]
        ndh = np.clip(N[..., 0] * HALF[0] + N[..., 1] * HALF[1] + N[..., 2] * HALF[2], 0, 1)
        outline_k = np.zeros((H, W), dtype=np.float32)
        for i, m in enumerate(self.mats):
            mm = self.mid == i
            if not mm.any():
                continue
            base = np.broadcast_to(m.color, (H, W, 3))
            col = np.where(self.hascol[..., None] & mm[..., None], self.col, base)[mm]
            nd = ndl[mm]
            hi, mid = m.bands
            k = np.where(nd > hi, 1.0, np.where(nd > mid, 0.80, 0.64)).astype(np.float32)
            tint = np.where((nd > hi)[:, None], 1.0, m.shadow_tint[None, :])
            c = col * k[:, None] * tint * m.shade
            if m.spec > 0:
                sp = (ndh[mm] ** 48 > 0.45).astype(np.float32) * m.spec
                c = c + sp[:, None]
            nx = N[..., 0][mm]
            nz = N[..., 2][mm]
            rim = ((nx < -0.55) & (nz < 0.6)).astype(np.float32) * m.rim
            c = c + rim[:, None] * np.array([0.55, 0.65, 1.0], dtype=np.float32)
            if m.emissive > 0:
                c = c * (1 - m.emissive) + col * m.emissive
            rgb[mm] = np.clip(c, 0, 1)
            outline_k[mm] = m.outline
        # outlines: silhouette + depth discontinuities
        edge = np.zeros((H, W), dtype=bool)
        d = self.depth
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            nb_mask = np.roll(np.roll(mask, dy, 0), dx, 1)
            nb_d = np.roll(np.roll(d, dy, 0), dx, 1)
            nb_p = np.roll(np.roll(self.pid, dy, 0), dx, 1)
            edge |= mask & ~nb_mask
            edge |= mask & nb_mask & (nb_d - d > 5.0) & (nb_p != self.pid)
        # outer outline grows one supersample pixel outside the silhouette
        grow = np.zeros((H, W), dtype=bool)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            grow |= np.roll(np.roll(mask, dy, 0), dx, 1)
        outer = grow & ~mask
        out_rgb = rgb.copy()
        ok = outline_k[..., None]
        out_rgb[edge] = (rgb * ok)[edge]
        # colour for outer ring: darkest neighbour colour
        ring = np.zeros((H, W, 3), dtype=np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            ring = np.maximum(ring, np.roll(np.roll(rgb * ok, dy, 0), dx, 1))
        out_rgb[outer] = ring[outer] * 0.8
        alpha = (mask | outer).astype(np.float32)
        # downsample
        h2, w2 = H // SS, W // SS
        a = alpha[:h2 * SS, :w2 * SS].reshape(h2, SS, w2, SS).sum(axis=(1, 3))
        c = (out_rgb[:h2 * SS, :w2 * SS] * alpha[:h2 * SS, :w2 * SS, None]).reshape(h2, SS, w2, SS, 3).sum(axis=(1, 3))
        cov = a / (SS * SS)
        c = c / np.maximum(a, 1e-6)[..., None]
        img = np.zeros((h2, w2, 4), dtype=np.uint8)
        img[..., :3] = np.clip(c * 255 + 0.5, 0, 255).astype(np.uint8)
        img[..., 3] = np.where(cov >= 0.5, 255, 0).astype(np.uint8)
        origin = (-self.xmin, self.ymax)  # pixel position of world (0,0)
        return img, origin
