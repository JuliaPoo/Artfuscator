import argparse
from PIL import Image
import numpy as np

from .utils import compile

parser = argparse.ArgumentParser(
    description='Compiling elvm nasm output to artful stuff'
)

parser.add_argument(
    "-i", type=str, 
    help="filepath of greyscale image (single channel image)"
)
parser.add_argument(
    "nasmfile", type=str,
    help="nasm filepath"
)

args = parser.parse_args()

nasm_code = open(args.nasmfile).read()
art = Image.open(args.i)

if art.mode != "L":
    raise Exception(
        "Image provided isn't a single channel greyscale image! (Mode `L`)"
    )

compiled = compile(nasm_code, np.array(art))
open(args.nasmfile, "w").write(compiled)