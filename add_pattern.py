import json
import os

def save_library(pattern_name, matrix, filename="pattern_library.json"):
    library = {}
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try: 
                library = json.load(f)
            except: 
                library = {}

    color_map = {
        "0": [235, 215, 170],
        "1": [180, 40, 50],
        "2": [45, 110, 75],
        "3": [35, 75, 145],
        "4": [215, 155, 35]
    }

    library[pattern_name] = {
        "color_map": color_map,
        "matrix": matrix
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(library, f, indent=2)
    print(f"Đã thêm mẫu '{pattern_name}' vào {filename}")

def generate_caro(height=80, width=120, block_size=10):
    matrix = []
    for r in range(height):
        row = []
        for c in range(width):
            if ((r // block_size) + (c // block_size)) % 2 == 0:
                row.append(1)
            else:
                row.append(0)
        matrix.append(row)
    return matrix

def generate_multi_caro(height=80, width=120, block_size=10, colors=[0, 1, 2, 3]):
    matrix = []
    num_colors = len(colors)
    
    for r in range(height):
        row = []
        for c in range(width):
            block_r = r // block_size
            block_c = c // block_size

            color_index = (block_r + block_c) % num_colors

            row.append(colors[color_index])
        matrix.append(row)
        
    return matrix

def generate_stripes(height=80, width=120, thickness=4, spacing=16):
    matrix = []
    for r in range(height):
        row = []
        for c in range(width):
            is_vertical = (c % spacing) < thickness
            is_horizontal = (r % spacing) < thickness
            
            if is_vertical and is_horizontal: row.append(3)
            elif is_vertical: row.append(2)
            elif is_horizontal: row.append(4)
            else: row.append(0)
        matrix.append(row)
    return matrix

def generate_zigzag(height=80, width=120, wave_length=20, band_height=20, thickness=3):
    matrix = []
    for r in range(height):
        row = []
        for c in range(width):
            offset_y = abs((c % wave_length) - (wave_length // 2))
            local_r = r % band_height
            if abs(local_r - offset_y) <= thickness:
                row.append(1)
            else:
                row.append(0)
        matrix.append(row)
    return matrix

if __name__ == "__main__":
    print("Đang tạo các hoa văn toán học...")
    mat_caro = generate_caro(height=80, width=120, block_size=8)
    save_library("caro", mat_caro)
    mat_stripes = generate_stripes(height=80, width=120, thickness=3, spacing=15)
    save_library("stripes", mat_stripes)
    mat_zigzag = generate_zigzag(height=80, width=120, wave_length=24, band_height=24, thickness=2)
    save_library("zigzag", mat_zigzag)
    mat_caro_3 = generate_multi_caro(80, 120, block_size=8, colors=[1, 2, 4])
    save_library("caro_3_mau", mat_caro_3)
    mat_caro_5 = generate_multi_caro(80, 120, block_size=5, colors=[0, 1, 2, 3, 4])
    save_library("caro_5_mau", mat_caro_5)
    mat_caro_nhat = generate_multi_caro(80, 120, block_size=10, colors=[0, 2, 0, 4])
    save_library("caro_nhat", mat_caro_nhat)