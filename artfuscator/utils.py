from typing import List, Tuple
import re

from PIL import Image
import numpy as np
import random


FUNC_START_SIG: str = r"; ----- Start of"
FUNC_END_SIG: str = r"; ----- End of func -----"
OP_COMMENT_SIG: str = r" ; op:"
OP_SET_SIG: str = r" set[a-z]+ +al"
BB_START_SIG: str = r"BB\d+:"
BB_END_SIG: str = r" call PCJMP"

INST_PER_PIX = 25


def split_blocks(blockstr: List[str]) -> List[List[str]]:

    blocks: List[List[str]] = []
    j = 0
    isfirst = False
    currbb = -1
    while j < len(blockstr):

        l = blockstr[j]

        if l.startswith(OP_COMMENT_SIG):
            j += 1
            continue

        if re.match(BB_START_SIG, l):
            blocks.append([l])
            c = int(re.search(r"\d+", l).group())
            assert c == currbb+1
            currbb = c
            isfirst = True
            j += 1
            continue

        if isfirst:
            blocks[-1][0] += l
            isfirst = False
            j += 1
            continue

        blocks[-1].append(l)
        j += 1

    return blocks


def parse_nasm(lines: List[str]) \
        -> Tuple[List[str], List[List[str]], List[str]]:

    lines = [l for l in lines if l]

    prefix: List[str] = []
    for j, l in enumerate(lines):
        if l.startswith(FUNC_START_SIG):
            j += 1
            break
        prefix.append(l)

    blockstr: List[str] = []
    for j0, l in enumerate(lines[j:]):
        j0 += j
        if l.startswith(FUNC_END_SIG):
            j0 += 1
            break
        blockstr.append(l)

    postfix = lines[j0:]

    return prefix, split_blocks(blockstr), postfix


def get_pixel_array(art: np.ndarray, blocks: List[List[str]]) \
        -> np.ndarray:
    """
    art is a greyscale image, represented as a 2D np.uint8 array.
    """

    nlines = sum(map(len, blocks))
    sy, sx = art.shape
    art = Image.fromarray(art)

    if not hasattr(Image, 'Resampling'):  # Pillow<9.0
        Image.Resampling = Image

    err = 0
    h, l = 1, 0
    best_scale = 0
    while True:

        s = (h+l)/2

        a = art.resize(
            (round(sx*s), round(sy*s)),
            Image.Resampling.NEAREST)
        a = np.array(a)
        a = (INST_PER_PIX*(a.astype("float") / 255)).astype(np.uint8)

        ascore = a.sum()
        nerr = ascore - nlines
        if nerr == err:
            break
        err = nerr

        if err < 0:
            l = s
        elif err > 0:
            h = s
            best_scale = s
        else:
            break

    a = art.resize(
        (round(sx*best_scale), round(sy*best_scale)),
        Image.Resampling.NEAREST)
    a = np.array(a)
    a = (INST_PER_PIX*(a.astype("float") / 255)).astype(np.uint8)
    return a


def pad_blocks(blocks: List[List[str]], pixel_arr: np.ndarray) \
        -> List[List[str]]:

    diff = pixel_arr.sum() - sum(map(len, blocks))
    assert diff >= 0

    if diff == 0:
        return blocks
    pad = [f"BB{len(blocks)}: nop"]
    if diff > 1:
        while len(pad) < diff-1:
            rbb = random.choice(blocks)
            if len(rbb) <= 1:
                continue
            pad.append(random.choice(rbb[1:]))

    return blocks + [pad]


def get_pixel_blocks(padded_blocks: List[List[str]], pixel_arr: np.ndarray) \
        -> List[List[List[str]]]:

    bbs = sum(padded_blocks, start=[])
    sy, sx = pixel_arr.shape
    pbbs: List[List[str]] = []
    ptr = 0
    for x in range(sx):
        for y in range(sy):
            nb = pixel_arr[y, x]
            pbbs.append(bbs[ptr:ptr+nb])
            # SET inst is first inst
            if len(pbbs[-1]) > 0 and re.match(OP_SET_SIG, pbbs[-1][0]):
                l = pbbs[-1].pop(0)
                pbbs[-2].append(l)
            ptr += nb

    pixel_blocks = [[
        pbbs[x*sy + y]
        for x in range(sx)
    ]
        for y in range(sy)
    ]

    return pixel_blocks


def wrap_pixel_blocks(pixel_blocks: List[List[List[str]]]):

    sy, sx = len(pixel_blocks), len(pixel_blocks[0])
    for y in range(sy):
        for x in range(sx):
            p = pixel_blocks[y][x]
            p.insert(
                0, f"PIX_{x}_{y}: vfmaddsub132ps xmm0, xmm1, [cs:ebx+edx*4+mem]")
            if y+1 == sy:
                p.append(f" mov esi, {x+1}")
                p.append(f" jmp PIX_END")
            else:
                p.append(f" jmp PIX_{x}_{y+1}")

    pad = [
        [f"PIX_PAD_{y}: nop"] + ["nop"]*INST_PER_PIX + [f"jmp PIX_PAD_{y+1}"]
        for y in range(sy-1)
    ] + [
        [f"PIX_PAD_{sy-1}: nop"] + ["nop"]*INST_PER_PIX + [f"jmp PIX_END"]
    ]

    return pixel_blocks + [pad]


def wrap_postfix(postfix: List[str], pixel_blocks: List[List[List[str]]]) \
        -> List[str]:

    end_switch = [
        "PIX_END:",
        "jmp PIX_START"
    ]
    pixel_table = ["PIX_TABLE:"] + [
        f" dd PIX_{x}_0"
        for x in range(len(pixel_blocks[0]))
    ] + [" dd PIX_PAD_0"]
    return end_switch + pixel_table + postfix


def wrap_prefix(prefix: List[str]) -> List[str]:

    # set esi = 0?
    start_switch = [
        "PIX_START:",
        " mov esi, [PIX_TABLE + 4*esi]",
        " jmp esi"
    ]
    # change jz BB0 to jz PIX_START
    prefix[-2] = prefix[-2].replace("BB0", "PIX_START")
    return prefix + start_switch


def compile(nasm_code: str, art: np.ndarray) -> str:

    lines = nasm_code.split("\n")
    prefix, blocks, postfix = parse_nasm(lines)

    pixel_arr = get_pixel_array(art, blocks)
    padded_blocks = pad_blocks(blocks, pixel_arr)
    pixel_blocks = get_pixel_blocks(padded_blocks, pixel_arr)

    pixel_blocks = wrap_pixel_blocks(pixel_blocks)
    postfix = wrap_postfix(postfix, pixel_blocks)
    prefix = wrap_prefix(prefix)

    return "\n".join(
        prefix
        + sum(
            map(lambda b: sum(b, start=[]), pixel_blocks),
            start=[])
        + postfix)
