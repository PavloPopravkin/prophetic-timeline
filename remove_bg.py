#!/usr/bin/env python3
"""
AI background removal — rembg.
Outputs WebP with transparency. Works on any background color.

MODELS:
  u2net             Default. General purpose. Fast.
  u2net_human_seg   Optimized for people / portraits. Best for humans.
  isnet-general-use Higher quality edges. Slower.
  silueta           Lightweight. Fast. Good for simple subjects.
  sam               Segment Anything — picks SPECIFIC object via point or box.

USAGE:

  # Auto — main subject detected automatically
  python3 remove_bg.py uploads/photo.jpg
  python3 remove_bg.py uploads/photo.jpg -o output.webp
  python3 remove_bg.py uploads/*.jpg                    # batch

  # Specific model
  python3 remove_bg.py photo.jpg --model u2net_human_seg
  python3 remove_bg.py photo.jpg --model isnet-general-use

  # SAM — click a point ON the object you want to keep (pixels)
  python3 remove_bg.py photo.jpg --point 450,600

  # SAM — multiple points: 1=keep, 0=remove
  python3 remove_bg.py photo.jpg --point 450,600 --point 800,100,0

  # SAM — bounding box [x1,y1,x2,y2] around the object
  python3 remove_bg.py photo.jpg --rect 100,50,800,1100

  # SAM — box + point together (most precise)
  python3 remove_bg.py photo.jpg --rect 100,50,800,1100 --point 450,600
"""

import sys, os, io, glob, time, argparse

VALID_MODELS = ["u2net", "u2net_human_seg", "isnet-general-use", "silueta", "sam"]


def build_parser():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("inputs", nargs="*")
    p.add_argument("-o", "--output",  default=None)
    p.add_argument("--model",  default="u2net", choices=VALID_MODELS)
    p.add_argument("--point",  action="append", default=[],
                   metavar="X,Y[,LABEL]",
                   help="Point on object (label 1=keep default, 0=remove hint)")
    p.add_argument("--rect",   default=None, metavar="X1,Y1,X2,Y2",
                   help="Bounding box around object to keep")
    p.add_argument("--quality", type=int, default=88)
    p.add_argument("-h", "--help", action="store_true")
    return p


def parse_sam_prompt(args):
    prompt = []
    for pt in args.point:
        parts = [float(x) for x in pt.split(",")]
        label = int(parts[2]) if len(parts) > 2 else 1
        prompt.append({"type": "point", "data": [parts[0], parts[1]], "label": label})
    if args.rect:
        coords = [float(x) for x in args.rect.split(",")]
        prompt.append({"type": "rectangle", "data": coords})
    return prompt if prompt else None


def remove_bg(input_path, output_path=None, model="u2net",
              sam_prompt=None, quality=88):
    try:
        from rembg import remove, new_session
        from PIL import Image
        import onnxruntime as ort
    except ImportError:
        sys.exit("Run: pip install rembg Pillow onnxruntime")

    # Patch: rembg/SAM creates multiple InferenceSession objects internally;
    # force providers on every one so ORT 1.9+ doesn't raise ValueError.
    _providers = ort.get_available_providers()
    _orig_IS   = ort.InferenceSession
    class _PatchedIS(_orig_IS):
        def __init__(self, path, *a, **kw):
            kw.setdefault('providers', _providers)
            super().__init__(path, *a, **kw)
    ort.InferenceSession = _PatchedIS

    if not os.path.exists(input_path):
        print(f"  NOT FOUND: {input_path}")
        return None

    if output_path is None:
        base = os.path.splitext(input_path)[0]
        output_path = base + "_no_bg.webp"

    t0 = time.time()

    use_model = "sam" if sam_prompt else model
    session   = new_session(use_model)

    data   = open(input_path, "rb").read()
    kwargs = {"session": session}
    if sam_prompt:
        kwargs["sam_prompt"] = sam_prompt

    result = remove(data, **kwargs)
    img    = Image.open(io.BytesIO(result)).convert("RGBA")
    img.save(output_path, "WEBP", quality=quality, method=4)

    src_kb = os.path.getsize(input_path)  // 1024
    out_kb = os.path.getsize(output_path) // 1024
    dt     = time.time() - t0
    tag    = "sam+prompt" if sam_prompt else use_model
    print(f"  {os.path.basename(input_path)} → {os.path.basename(output_path)}"
          f"  [{src_kb}KB→{out_kb}KB]  {dt:.1f}s  [{tag}]")
    return output_path


if __name__ == "__main__":
    parser = build_parser()
    args, _ = parser.parse_known_args()

    if args.help or not args.inputs:
        print(__doc__)
        sys.exit(0)

    sam_prompt = parse_sam_prompt(args)

    paths = []
    for a in args.inputs:
        expanded = glob.glob(a)
        paths += expanded if expanded else [a]

    if len(paths) == 1:
        remove_bg(paths[0], args.output, args.model, sam_prompt, args.quality)
    else:
        print(f"Batch: {len(paths)} files  model={args.model}")
        for p in paths:
            remove_bg(p, None, args.model, sam_prompt, args.quality)
