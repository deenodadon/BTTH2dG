"""Character looks, based on the user's BTTH reference doc and the donghua designs."""
from rig import default_mats

SKIN = (1.0, 0.87, 0.76)


def _d(**kw):
    cols = kw.pop("colors")
    d = dict(kw)
    d["mats"] = default_mats(cols)
    d["colors"] = cols
    return d


DESIGNS = {
    # Xiao Yan: black robes with crimson trim, black spiky hair, the Heavy Profound Ruler on his back.
    "xiaoyan": _d(
        name="Xiao Yan", hair="spiky", lower="robe", sleeves="fitted", weapon="ruler",
        weapon_bands=[(-1.0, -0.74, (0.32, 0.16, 0.1)), (-0.74, -0.70, (0.85, 0.62, 0.25)),
                      (-0.1, -0.06, (0.55, 0.08, 0.06)), (0.3, 0.34, (0.55, 0.08, 0.06)),
                      (0.94, 1.0, (0.85, 0.62, 0.25))],
        colors=dict(skin=SKIN, hair=(0.09, 0.08, 0.11), robe=(0.17, 0.16, 0.2), robe2=(0.5, 0.08, 0.08),
                    trim=(0.78, 0.16, 0.1), belt=(0.62, 0.12, 0.08), pants=(0.13, 0.12, 0.15),
                    shoe=(0.1, 0.09, 0.1), eye=(0.22, 0.12, 0.08), weapon=(0.12, 0.11, 0.13))),
    # Yao Lao: translucent old master, white hair & beard, pale robes, floats (no feet).
    "yaolao": _d(
        name="Yao Lao", hair="old", lower="ghost", sleeves="wide", width=1.05, height=0.98,
        colors=dict(skin=(0.98, 0.88, 0.8), hair=(0.93, 0.94, 0.97), hair_spec=0.1,
                    robe=(0.84, 0.87, 0.92), robe2=(0.7, 0.78, 0.86), trim=(0.32, 0.58, 0.74),
                    belt=(0.36, 0.52, 0.68), pants=(0.8, 0.82, 0.86), shoe=(0.3, 0.3, 0.35),
                    eye=(0.15, 0.2, 0.25), brow=(0.9, 0.9, 0.92), pin=(0.45, 0.75, 0.85))),
    # Xun'er: lavender dress, long dark hair tied with a violet ribbon.
    "xuner": _d(
        name="Xun'er", hair="pony", lower="dress", sleeves="wide", female=True, width=0.88, height=0.94,
        hair_len=6,
        colors=dict(skin=(1.0, 0.89, 0.8), hair=(0.14, 0.1, 0.2), robe=(0.74, 0.64, 0.88),
                    robe2=(0.94, 0.92, 0.98), trim=(0.92, 0.82, 0.45), belt=(0.5, 0.32, 0.72),
                    pants=(0.95, 0.94, 0.98), shoe=(0.95, 0.93, 0.98), eye=(0.3, 0.18, 0.12),
                    ribbon=(0.55, 0.3, 0.75))),
    # Medusa: crimson & black gown with gold, purple hair, golden crown.
    "medusa": _d(
        name="Medusa", hair="long", lower="dress", sleeves="fitted", female=True, width=0.9, height=0.98,
        hair_len=7, crown=True, mantle="gold",
        colors=dict(skin=(1.0, 0.88, 0.8), hair=(0.4, 0.12, 0.46), robe=(0.66, 0.08, 0.13),
                    robe2=(0.14, 0.06, 0.09), trim=(0.93, 0.74, 0.3), belt=(0.9, 0.7, 0.28),
                    pants=(0.95, 0.85, 0.78), shoe=(0.85, 0.66, 0.26), eye=(0.75, 0.55, 0.1),
                    jewel=(0.6, 0.1, 0.8))),
    # Yun Yun: white robes trimmed sky-blue, hair bun with jade pin, longsword.
    "yunyun": _d(
        name="Yun Yun", hair="bun", lower="dress", sleeves="wide", female=True, width=0.88, height=0.97,
        hair_len=5, weapon="sword",
        colors=dict(skin=(1.0, 0.89, 0.8), hair=(0.1, 0.09, 0.13), robe=(0.93, 0.95, 0.99),
                    robe2=(0.76, 0.86, 0.97), trim=(0.4, 0.64, 0.9), belt=(0.3, 0.5, 0.8),
                    pants=(0.9, 0.93, 0.98), shoe=(0.85, 0.88, 0.95), eye=(0.15, 0.12, 0.2),
                    weapon=(0.82, 0.87, 0.93), pin=(0.35, 0.8, 0.62))),
    # Little Fairy Doctor: white & grey-lilac robes, black hair, flower in hair, poison aura.
    "fairydoctor": _d(
        name="Little Fairy Doctor", hair="long", lower="dress", sleeves="wide", female=True, width=0.86,
        height=0.93, hair_len=6, hairflower="flower",
        colors=dict(skin=(0.98, 0.9, 0.86), hair=(0.12, 0.1, 0.14), robe=(0.9, 0.9, 0.94),
                    robe2=(0.62, 0.55, 0.7), trim=(0.55, 0.42, 0.66), belt=(0.45, 0.36, 0.56),
                    pants=(0.88, 0.88, 0.92), shoe=(0.7, 0.66, 0.76), eye=(0.4, 0.22, 0.45),
                    flower=(0.72, 0.55, 0.85))),
}
