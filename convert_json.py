import os
import json
import argparse
import numpy as np
from PIL import Image

def get_color_id(h, s, v):
    if v < 35:
        return 5

    if s < 15 and v > 85: return 0
    if s < 15 and v <= 85: return 5

    if (h >= 0 and h < 20) or (h >= 330 and h <= 360): return 1
    if h >= 80 and h < 160: return 2
    if h >= 180 and h < 260: return 3
    if h >= 30 and h < 70: return 4

    return 1

def convert_hsv_to_matrix(image_path, target_w=240, target_h=280, warp_spacing=8):
    try:
        img_rgb = Image.open(image_path).convert('RGB')

        margin = 10
        img_rgb.thumbnail((target_w - margin, target_h - margin), Image.Resampling.LANCZOS)

        new_img = Image.new('RGB', (target_w, target_h), (235, 215, 170))
        offset = ((target_w - img_rgb.width) // 2, (target_h - img_rgb.height) // 2)
        new_img.paste(img_rgb, offset)

        jac_w = target_w // warp_spacing
        img_j = new_img.resize((jac_w, target_h), Image.Resampling.LANCZOS)
        img_q = img_j.resize((target_w, target_h), Image.Resampling.NEAREST)

        hsv_data = np.array(img_q.convert('HSV'))
        matrix = []

        for r in range(target_h):
            row = []
            for c in range(target_w):
                h = hsv_data[r, c, 0] / 255 * 360
                s = hsv_data[r, c, 1] / 255 * 100
                v = hsv_data[r, c, 2] / 255 * 100
                row.append(get_color_id(h, s, v))
            matrix.append(row)

        matrix_np = np.array(matrix)
        h, w = matrix_np.shape
        block = warp_spacing

        for r in range(h):
            for c in range(0, w, block):
                segment = matrix_np[r, c:c+block]
                if len(segment) == 0:
                    continue
                vals, counts = np.unique(segment, return_counts=True)
                majority = vals[np.argmax(counts)]
                matrix_np[r, c:c+block] = majority

        matrix = matrix_np.tolist()
        return matrix

    except Exception as e:
        print(f"Lỗi: {e}")
        return None

def save_library(name, matrix, filename="pattern_library.json"):
    lib = {}
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                lib = json.load(f)
            except:
                lib = {}

    lib[name] = {
        "color_map": {
            "0":[235,215,170],
            "1":[180,40,50],
            "2":[45,110,75],
            "3":[35,75,145],
            "4":[215,155,35],
            "5":[125, 95, 65]
        },
        "matrix": matrix
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(lib, f)

    print(f"Đã lưu {name}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--name", default="ete")
    args = p.parse_args()

    m = convert_hsv_to_matrix(args.input)
    if m:
        save_library(args.name, m)
        
## python convert_json.py --input ete.jpg --name ete --size 60 --thick 1