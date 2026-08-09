# -*- coding: utf-8 -*-
"""Minimal reader/writer for the specific TGA variant used by this game's
loose (non-DatFile-container) texture assets: uncompressed, 8bpp indexed
color, 32bpp (RGBA) colormap. PIL's TGA plugin chokes on the 32bpp-depth
colormap header (raises 'unrecognized raw mode'), so this decodes/encodes
by hand instead.

These loose .tga files live directly under paths like `_Data/Logo/`,
`_Data/Title/`, `_Data/Field/Scene/`, `_Data/Menu/ItemImage/Event/` inside
the l7c archive (unlike SystemTex.dat etc., which are proprietary
multi-section containers handled by texture.py). Because they're
standalone files, l7ca_patch_multi.py can patch them directly -- no
container-level recompile step is needed, just drop edited .tga files into
a directory tree that mirrors the archive paths (e.g.
`<root>/_Data/Logo/Attention_Ruca.tga`) and run l7ca_patch_multi.py.

Round-trip validated (2026-08-09): load_tga -> save_tga -> load_tga produces
byte-identical pixel data for both fully-opaque and partial-alpha sources.
"""
import struct
from PIL import Image


def load_tga(path):
    with open(path, "rb") as f:
        data = f.read()
    idlen, cmaptype, imgtype = data[0], data[1], data[2]
    cmap_first, cmap_len = struct.unpack_from("<HH", data, 3)
    cmap_depth = data[7]
    xorg, yorg, width, height = struct.unpack_from("<HHHH", data, 8)
    depth = data[16]
    descriptor = data[17]
    offset = 18 + idlen
    assert cmaptype == 1 and imgtype == 1 and cmap_depth == 32 and depth == 8, (
        f"unexpected TGA variant in {path}: cmaptype={cmaptype} imgtype={imgtype} "
        f"cmap_depth={cmap_depth} depth={depth}"
    )
    palette = []
    for _ in range(cmap_len):
        b, g, r, a = data[offset : offset + 4]
        palette.append((r, g, b, a))
        offset += 4
    indices = data[offset : offset + width * height]
    pixels = bytearray(width * height * 4)
    for i, idx in enumerate(indices):
        r, g, b, a = palette[idx]
        pixels[i * 4 : i * 4 + 4] = bytes([r, g, b, a])
    im = Image.frombytes("RGBA", (width, height), bytes(pixels))
    if not (descriptor & 0x20):
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    return im, dict(cmap_len=cmap_len, descriptor=descriptor)


def save_tga(im, path, cmap_len=256, descriptor=0x00):
    """Re-encode an RGBA image back into the same 8bpp-indexed/32bpp-palette
    TGA variant. Quantizes to <=256 colors automatically if needed (alpha is
    preserved only in the exact-color fast path; quantized images that were
    fully opaque stay fully opaque)."""
    im = im.convert("RGBA")
    width, height = im.size

    def exact_indices():
        colors = {}
        order = []
        px = im.load()
        idx_grid = [0] * (width * height)
        for y in range(height):
            for x in range(width):
                c = px[x, y]
                if c not in colors:
                    if len(order) >= 256:
                        return None, None
                    colors[c] = len(order)
                    order.append(c)
                idx_grid[y * width + x] = colors[c]
        return order, idx_grid

    order, idx_grid = exact_indices()
    if order is None:
        alphas = im.getchannel("A")
        fully_opaque = alphas.getextrema() == (255, 255)
        if fully_opaque:
            # quantize RGB only, alpha stays 255 everywhere
            rgb = im.convert("RGB")
            quant = rgb.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.NONE)
            pal_bytes = quant.getpalette()
            n_colors = len(pal_bytes) // 3
            order = [
                (pal_bytes[i * 3], pal_bytes[i * 3 + 1], pal_bytes[i * 3 + 2], 255)
                for i in range(n_colors)
            ]
            idx_grid = list(quant.getdata())
        else:
            # Posterize alpha to a handful of levels and retry exact-match
            # dedup -- text-on-transparent renders only mix a couple of base
            # colors, so this comfortably fits under 256 total combinations.
            for levels in (48, 32, 16, 8, 4):
                step = 255 / (levels - 1)
                px = im.load()
                new_px = [None] * (width * height)
                for y in range(height):
                    for x in range(width):
                        r, g, b, a = px[x, y]
                        a2 = round(round(a / step) * step)
                        new_px[y * width + x] = (r, g, b, a2)
                colors = {}
                order2 = []
                ok = True
                idx_grid2 = [0] * (width * height)
                for i, c in enumerate(new_px):
                    if c not in colors:
                        if len(order2) >= 256:
                            ok = False
                            break
                        colors[c] = len(order2)
                        order2.append(c)
                    idx_grid2[i] = colors[c]
                if ok:
                    order, idx_grid = order2, idx_grid2
                    break
            if order is None:
                raise ValueError(f"{path}: could not fit under 256 colors even after alpha posterization")
    palette = order + [(0, 0, 0, 0)] * (cmap_len - len(order))

    out = bytearray()
    out += bytes([0, 1, 1])  # idlen, cmaptype, imgtype
    out += struct.pack("<HH", 0, cmap_len)
    out += bytes([32])  # cmap_depth
    out += struct.pack("<HH", 0, 0)  # x/y origin
    out += struct.pack("<HH", width, height)
    out += bytes([8, descriptor])  # depth, descriptor
    for (r, g, b, a) in palette:
        out += bytes([b, g, r, a])
    # pixel rows: descriptor bit5 unset (bottom-left origin) means we must
    # flip vertically before writing to match the on-disk row order.
    rows = [idx_grid[y * width : (y + 1) * width] for y in range(height)]
    if not (descriptor & 0x20):
        rows = list(reversed(rows))
    for row in rows:
        out += bytes(row)
    with open(path, "wb") as f:
        f.write(bytes(out))
