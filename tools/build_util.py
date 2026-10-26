"""Shared helpers for the asset build."""
import numpy as np
from PIL import Image


def quantize_set(images, ncolors=255):
    """images: list of RGBA uint8 arrays. Returns (palette [(r,g,b)]*256 with idx0 transparent, indexed list)."""
    px = [im[..., :3][im[..., 3] > 0] for im in images]
    allpx = np.concatenate([p for p in px if len(p)], axis=0) if any(len(p) for p in px) else np.zeros((1, 3), np.uint8)
    if len(allpx) > 1_500_000:
        idx = np.random.default_rng(0).choice(len(allpx), 1_500_000, replace=False)
        allpx = allpx[idx]
    strip = Image.fromarray(allpx.reshape(-1, 1, 3))
    q = strip.quantize(colors=ncolors, method=Image.Quantize.MEDIANCUT, kmeans=1)
    pal = q.getpalette()[:ncolors * 3]
    pal += [0] * (ncolors * 3 - len(pal))
    palimg = Image.new("P", (1, 1))
    palimg.putpalette(pal + pal[0:3] * ((768 - len(pal)) // 3))
    out = []
    for im in images:
        rgb = Image.fromarray(np.ascontiguousarray(im[..., :3]))
        m = rgb.quantize(palette=palimg, dither=Image.Dither.NONE)
        ind = np.asarray(m, dtype=np.uint8).astype(np.int32)
        ind[ind >= ncolors] = 0
        ind = ind + 1
        ind[im[..., 3] == 0] = 0
        out.append(ind.astype(np.uint8))
    colors = [(255, 0, 255)] + [tuple(pal[i * 3:i * 3 + 3]) for i in range(ncolors)]
    colors += [(0, 0, 0)] * (256 - len(colors))
    return colors, out


quantize_rgba = quantize_set
