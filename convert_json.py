import os
import json
import argparse
import numpy as np
from PIL import Image

def get_color_id(h, s, v):
    if v < 35: return 5
    if s < 15 and v > 85: return 0
    if s < 15 and v <= 85: return 5
    if (h >= 0 and h < 20) or (h >= 330 and h <= 360): return 1
    if h >= 80 and h < 160: return 2
    if h >= 180 and h < 260: return 3
    if h >= 30 and h < 70: return 4
    return 1

def enforce_global_two_colors(matrix, warp_spacing):
    """
    Ép toàn bộ matrix chỉ còn 2 màu: 
    - Màu 0 (nền)
    - 1 màu họa tiết duy nhất (màu xuất hiện nhiều nhất, không phải màu 0)
    """
    matrix_np = np.array(matrix)
    
    unique_vals, counts = np.unique(matrix_np, return_counts=True)
    color_counts = {val: count for val, count in zip(unique_vals, counts) if val != 0}
    
    if not color_counts:
        return matrix_np.tolist()

    accent_color = max(color_counts, key=color_counts.get)
    
    matrix_np = np.where((matrix_np != 0) & (matrix_np != accent_color), accent_color, matrix_np)
    
    return matrix_np.tolist()

def enforce_uniform_warp_blocks(matrix, warp_spacing):
    """
    Đảm bảo mỗi block warp_spacing ô trên cùng 1 hàng có cùng 1 màu
    (vì 1 sợi dọc chỉ có 1 màu trên toàn bộ chiều dài)
    """
    matrix_np = np.array(matrix)
    h, w = matrix_np.shape
    
    for r in range(h):
        for c in range(0, w, warp_spacing):
            block = matrix_np[r, c:c+warp_spacing]
            if len(block) == 0:
                continue
            
            unique_vals, counts = np.unique(block, return_counts=True)

            if len(unique_vals) == 1:
                continue
            
            if len(unique_vals) == 2:
                count_0 = counts[unique_vals.tolist().index(0)] if 0 in unique_vals else 0
                count_accent = counts[unique_vals.tolist().index([x for x in unique_vals if x != 0][0])] if len([x for x in unique_vals if x != 0]) > 0 else 0
                
                if count_accent >= count_0:
                    selected_color = [x for x in unique_vals if x != 0][0]
                else:
                    selected_color = 0
            else:
                selected_color = unique_vals[0]
            
            matrix_np[r, c:c+warp_spacing] = selected_color
    
    return matrix_np.tolist()

def apply_border_padding(matrix, warp_spacing, border_rows=12):
    """
    Xử lý padding 4 góc:
    - Trên/Dưới (border_rows hàng): giữ nguyên màu họa tiết
    - Trái/Phải: đan xen 2 màu (nền và họa tiết) theo đúng quy tắc dệt
    """
    matrix_np = np.array(matrix)
    h, w = matrix_np.shape
    border_cols = 4 * warp_spacing

    unique_vals = np.unique(matrix_np)
    accent_color = [x for x in unique_vals if x != 0]
    accent_color = accent_color[0] if accent_color else 1
    
    for r in range(border_rows):
        matrix_np[r, :] = accent_color
    for r in range(h - border_rows, h):
        matrix_np[r, :] = accent_color
    
    for r in range(border_rows, h - border_rows):
        # Cột trái
        for c in range(0, border_cols, warp_spacing):

            warp_idx = c // warp_spacing
            if (warp_idx + r) % 2 == 0:
                matrix_np[r, c:c+warp_spacing] = 0
            else:
                matrix_np[r, c:c+warp_spacing] = accent_color
        
        # Cột phải
        for c in range(w - border_cols, w, warp_spacing):
            warp_idx = c // warp_spacing
            if (warp_idx + r) % 2 == 0:
                matrix_np[r, c:c+warp_spacing] = 0
            else:
                matrix_np[r, c:c+warp_spacing] = accent_color
    
    return matrix_np.tolist()

def convert_hsv_to_matrix(image_path, target_w=300, target_h=340, warp_spacing=6):
    try:
        img_rgb = Image.open(image_path).convert('RGB')
   
        border_cols = 4 * warp_spacing
        border_rows = 12
        
        safe_w = target_w - (2 * border_cols) - 20
        safe_h = target_h - (2 * border_rows) - 20
        
        img_rgb.thumbnail((safe_w, safe_h), Image.Resampling.LANCZOS)
        
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
        
        matrix_np = np.array(enforce_global_two_colors(matrix_np.tolist(), warp_spacing))
        
        matrix_np = np.array(enforce_uniform_warp_blocks(matrix_np.tolist(), warp_spacing))
        
        matrix_final = apply_border_padding(matrix_np.tolist(), warp_spacing, border_rows)
        
        return matrix_final
        
    except Exception as e:
        print(f"Lỗi: {e}")
        return None

def save_library(name, matrix, filename="pattern_library.json"):
    lib = {}
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try: lib = json.load(f)
            except: lib = {}
    
    lib[name] = {
        "color_map": {
            "0": [235, 220, 185],  # Màu Be (Nền)
            "1": [180, 40, 50],    # Đỏ
            "2": [45, 110, 75],    # Xanh lá
            "3": [35, 75, 145],    # Xanh dương
            "4": [215, 155, 35],   # Vàng
            "5": [120, 40, 140]    # Tím
        },
        "matrix": matrix
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(lib, f)
    print(f"Đã lưu {name} với matrix size {len(matrix)}x{len(matrix[0])}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--name", default="ete")
    args = p.parse_args()
    
    m = convert_hsv_to_matrix(args.input, warp_spacing=6)
    if m:
        save_library(args.name, m)
        print("Hoàn tất!")
