#!/usr/bin/env python3
"""
Chroma key with auto-calibration + flood-fill connected-background isolation.
Usage: python3 chroma_key.py <input.jpg> [output.webp] [--debug]
"""
import sys, os
import cv2
import numpy as np


def remove_background(input_path, output_path=None, debug=False):
    img = cv2.imread(input_path)
    if img is None:
        sys.exit(f"Cannot read: {input_path}")
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ── 1. Auto-sample actual background hue from corners ──────────────
    s = 40
    corners = [img[0:s,0:s], img[0:s,w-s:w], img[h-s:h,0:s], img[h-s:h,w-s:w],
               img[0:s,w//2-s:w//2+s], img[h-s:h,w//2-s:w//2+s]]
    samples_bgr  = np.concatenate([c.reshape(-1,3) for c in corners])
    samples_hsv  = cv2.cvtColor(samples_bgr.reshape(-1,1,3), cv2.COLOR_BGR2HSV).reshape(-1,3)
    valid = (samples_hsv[:,1] > 35) & (samples_hsv[:,2] > 25)
    if valid.sum() >= 10:
        hv = samples_hsv[valid, 0]
        h_med = float(np.median(hv))
        h_std = float(np.std(hv))
        h_lo  = max(0,   int(h_med - max(18, h_std * 3)))
        h_hi  = min(180, int(h_med + max(18, h_std * 3)))
        print(f"Background hue: {h_med*2:.0f}° → HSV H=[{h_lo},{h_hi}]")
    else:
        h_lo, h_hi = 45, 95  # fallback green
        print("Corners desaturated, using default green H=[45,95]")

    # ── 2. Wide HSV mask ────────────────────────────────────────────────
    s_lo, v_lo = 35, 20
    mask_hsv = cv2.inRange(hsv, np.array([h_lo, s_lo, v_lo]),
                                np.array([h_hi, 255,  255]))

    # ── 3. Flood-fill from corners → isolate CONNECTED background ───────
    flood = mask_hsv.copy()
    seed_pts = [(0,0),(0,w-1),(h-1,0),(h-1,w-1),
                (0,w//2),(h-1,w//2),(h//2,0),(h//2,w-1)]
    for (fy, fx) in seed_pts:
        if flood[fy, fx] == 255:
            cv2.floodFill(flood, None, (fx, fy), 128)
    mask_bg = np.where(flood == 128, 255, 0).astype(np.uint8)

    # Include isolated green blobs touching the main background (via dilation bridge)
    bridge = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19))
    mask_bg = cv2.bitwise_or(mask_bg,
                  cv2.bitwise_and(mask_hsv, cv2.dilate(mask_bg, bridge)))

    # ── 4. Morphological cleanup ─────────────────────────────────────────
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask_bg = cv2.morphologyEx(mask_bg, cv2.MORPH_CLOSE, k5)
    mask_bg = cv2.morphologyEx(mask_bg, cv2.MORPH_OPEN,  k3)

    # ── 5. Feather edges ─────────────────────────────────────────────────
    alpha = (cv2.GaussianBlur(
                 cv2.bitwise_not(mask_bg).astype(np.float32) / 255.0,
                 (0, 0), 2.5) * 255).clip(0, 255).astype(np.uint8)

    # ── 6. Save ──────────────────────────────────────────────────────────
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + "_no_bg.webp"

    b, g, r = cv2.split(img)
    cv2.imwrite(output_path, cv2.merge([b, g, r, alpha]),
                [cv2.IMWRITE_WEBP_QUALITY, 88] if output_path.endswith('.webp')
                else [cv2.IMWRITE_PNG_COMPRESSION, 9])

    pct = 100 * (alpha < 128).sum() / (h * w)
    print(f"Transparent: {pct:.1f}%  |  "
          f"{os.path.getsize(input_path)//1024} KB → {os.path.getsize(output_path)//1024} KB")
    print(f"Saved: {output_path}")

    if debug:
        cv2.imwrite(output_path.replace('.webp', '_mask_debug.png'),
                    cv2.cvtColor(np.stack([mask_bg*0, mask_bg, mask_bg*0], axis=2),
                                 cv2.COLOR_BGR2BGR))


if __name__ == "__main__":
    args  = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = [a for a in sys.argv[1:] if     a.startswith('--')]
    if not args:
        print("Usage: python3 chroma_key.py <input.jpg> [output.webp] [--debug]")
        sys.exit(1)
    remove_background(args[0], args[1] if len(args) > 1 else None, '--debug' in flags)
