import json
import os
import numpy as np
import argparse
from PIL import Image, ImageFilter, ImageDraw, ImageFont

def ensure_sample_library_exists(filename="pattern_library.json"):
    """Tạo pattern mẫu nếu chưa có hoặc thiếu sample_pattern"""
    need_create = True
    
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "sample_pattern" in data:
                    need_create = False
        except:
            need_create = True
    
    if not need_create:
        return

    matrix = []
    for r in range(30):
        row = []
        for c in range(48):
            if (r + c // 6) % 3 == 0:
                row.append(4)
            elif (r - c // 6) % 3 == 0:
                row.append(4)
            else:
                row.append(0)
        matrix.append(row)

    sample_data = {
        "sample_pattern": {
            "matrix": matrix,
            "color_map": {
                "0": [235, 220, 185],
                "1": [180, 40, 50],
                "2": [45, 110, 75],
                "3": [35, 75, 145],
                "4": [215, 155, 35],
                "5": [120, 40, 140]
            }
        }
    }
    
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            existing_data.update(sample_data)
            sample_data = existing_data
        except:
            pass
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=4)
    
    print(f"[✓] Đã tạo pattern mẫu 'sample_pattern' trong {filename}")

class SmartWeaver3D:
    def __init__(self, pattern_key, library_file="pattern_library.json", 
                 border_style="background", border_top=12, border_bottom=12, 
                 border_left=24, border_right=24,
                 show_markers=False):
        self.library_file = library_file
        self.pattern_key = pattern_key
        self.border_style = border_style
        self.show_markers = show_markers
        
        self.border_top = border_top
        self.border_bottom = border_bottom
        self.border_left = border_left
        self.border_right = border_right
        
        self.cell_size = 36
        self.warp_spacing = 6
        self.block_size = 12

        try:
            with open(self.library_file, 'r', encoding='utf-8') as f:
                all_patterns = json.load(f)
                
            if self.pattern_key not in all_patterns:
                raise KeyError(f"Pattern '{self.pattern_key}' không tồn tại")
                
            pattern_data = all_patterns[self.pattern_key]
            
        except Exception as e:
            raise ValueError(f"Không thể load pattern: {e}")

        self.pattern_matrix = np.array(pattern_data["matrix"])
        
        self.pattern_matrix = self._fix_diamond_colors(self.pattern_matrix)
        
        # Đồng bộ màu: tất cả họa tiết thành màu 4
        for r in range(self.pattern_matrix.shape[0]):
            for c in range(self.pattern_matrix.shape[1]):
                if self.pattern_matrix[r, c] != 0:
                    self.pattern_matrix[r, c] = 4
        
        self.mat_h_cells, self.mat_w_cells = self.pattern_matrix.shape

        if self.border_top + self.border_bottom >= self.mat_h_cells:
            self.border_top = min(self.border_top, self.mat_h_cells // 4)
            self.border_bottom = min(self.border_bottom, self.mat_h_cells // 4)
            
        if self.border_left + self.border_right >= self.mat_w_cells:
            self.border_left = min(self.border_left, self.mat_w_cells // 4)
            self.border_right = min(self.border_right, self.mat_w_cells // 4)

        self.color_map = {int(k): np.array(v) for k, v in pattern_data["color_map"].items()}
        self.default_bg_id = 0
        self.default_bg_color = self.color_map.get(self.default_bg_id, np.array([235, 220, 185]))

        # Vùng trung tâm
        self.core_start_row = self.border_top + 4
        self.core_end_row = self.mat_h_cells - self.border_bottom - 4
        self.core_start_col = self.border_left + 24
        self.core_end_col = self.mat_w_cells - self.border_right - 24
        
        self.expanded_start_col = max(self.border_left, self.core_start_col - self.block_size)
        self.expanded_end_col = min(self.mat_w_cells - self.border_right, self.core_end_col + self.block_size)
        
        print(f"[✓] Khởi tạo thành công pattern '{pattern_key}' với kích thước {self.mat_h_cells}x{self.mat_w_cells}")
        print(f"   Border: top={self.border_top}, bottom={self.border_bottom}, left={self.border_left}, right={self.border_right}")
        print(f"   Border style: {self.border_style}")
        print(f"   Vùng core: hàng {self.core_start_row}→{self.core_end_row-1}, cột {self.core_start_col}→{self.core_end_col-1}")
        
        # Phát hiện và merge các vùng họa tiết
        self._detect_and_merge_regions()
        
        # Xây dựng cấu trúc dệt
        self._build_weave_structure()
    
    
    def _detect_and_merge_regions(self):
        """Phát hiện và MERGE các vùng liên tục - Xen kẽ merge theo từng hàng"""
        raw_regions = []
        
        print("\n=== BƯỚC 1: PHÁT HIỆN VÙNG LIÊN TỤC ===")
        print(f"   Xen kẽ merge: hàng {self.core_start_row} (merge nền) → hàng {self.core_end_row-1} (merge họa tiết)")
        
        # Duyệt từng hàng trong vùng core
        for r in range(self.core_start_row, self.core_end_row):
            # Xác định hàng này merge màu gì (xen kẽ)
            if (r - self.core_start_row) % 2 == 0:
                merge_target = 0  # merge màu NỀN
                merge_name = "NỀN"
            else:
                merge_target = -1  # merge màu HỌA TIẾT (≠ 0)
                merge_name = "HỌA TIẾT"
            
            print(f"\n   Hàng {r:3d}: MERGE {merge_name}")
            
            # Duyệt các cột từ expanded_start_col đến expanded_end_col
            c = self.expanded_start_col
            while c < self.expanded_end_col:
                current_color = self.pattern_matrix[r, c]
                
                # QUYẾT ĐỊNH CÓ XÉT VÙNG NÀY KHÔNG
                if merge_target == 0:
                    if current_color != 0:
                        c += 1
                        continue
                else:
                    if current_color == 0:
                        c += 1
                        continue
                
                start_col = c
                run_length = 1
                
                while (c + run_length) < self.expanded_end_col:
                    next_color = self.pattern_matrix[r, c + run_length]
                    if merge_target == 0:
                        if next_color != 0:
                            break
                    else:
                        if next_color == 0:
                            break
                    run_length += 1
                
                end_col = c + run_length - 1
                touches_core = (start_col < self.core_end_col and end_col >= self.core_start_col)
                
                if touches_core and run_length >= 2:
                    raw_regions.append({
                        'row': r, 'start': start_col, 'end': end_col,
                        'color': current_color, 'length': run_length,
                        'merge_type': merge_name
                    })
                    print(f"      RAW: {merge_name} (màu {current_color}) | Cột {start_col:3d}→{end_col:3d} | Dài {run_length:2d}")
                
                c += run_length
        
        print(f"\n=== BƯỚC 2: MERGE CÁC VÙNG CÙNG MÀU, GẦN NHAU (gap <= 2) ===")
        
        self.pattern_regions = []
        rows_dict = {}
        for reg in raw_regions:
            if reg['row'] not in rows_dict:
                rows_dict[reg['row']] = []
            rows_dict[reg['row']].append(reg)
        
        for row, regions in rows_dict.items():
            regions.sort(key=lambda x: x['start'])
            merged = []
            current = regions[0].copy()
            
            for next_reg in regions[1:]:
                gap = next_reg['start'] - current['end'] - 1
                if current['color'] == next_reg['color'] and gap <= 2:
                    current['end'] = next_reg['end']
                    current['length'] = current['end'] - current['start'] + 1
                    print(f"   MERGE: Hàng {row} | Màu {current['color']} | {current['start']}→{current['end']} (gap={gap})")
                else:
                    merged.append(current)
                    current = next_reg.copy()
            merged.append(current)
            
            for reg in merged:
                if reg['start'] < self.core_end_col and reg['end'] >= self.core_start_col:
                    self.pattern_regions.append(reg)
                    print(f"   FINAL: Hàng {row:3d} | Màu {reg['color']} | Cột {reg['start']:3d}→{reg['end']:3d} | Dài {reg['length']:2d}")
        
        # Đồng bộ màu
        print(f"\n=== BƯỚC 3: ĐỒNG BỘ MÀU (GIỮ NGUYÊN MÀU CỦA VÙNG) ===")
        for region in self.pattern_regions:
            target_color = region['color']
            for c in range(region['start'], region['end'] + 1):
                self.pattern_matrix[region['row'], c] = target_color
            print(f"   Đồng bộ màu {target_color} cho hàng {region['row']}, cột {region['start']}-{region['end']}")
        
        # === TẠO MARKER - CHỈNH SỬA VỊ TRÍ ===
        print(f"\n=== BƯỚC 4: TẠO MARKER ===")
        self.marker_positions = []
        
        for region in self.pattern_regions:
            # Marker tại cột BẮT ĐẦU của region (trong vùng core)
            start_col = region['start']
            end_col = region['end']
            
            # Chỉ thêm marker nếu nó nằm trong vùng core
            if start_col >= self.core_start_col and start_col < self.core_end_col:
                self.marker_positions.append({
                    'row': region['row'], 
                    'col': start_col, 
                    'type': 'start', 
                    'color': region['color']
                })
                print(f"   Marker START: Hàng {region['row']} | cột {start_col}")
            
            if end_col >= self.core_start_col and end_col < self.core_end_col:
                self.marker_positions.append({
                    'row': region['row'], 
                    'col': end_col, 
                    'type': 'end', 
                    'color': region['color']
                })
                print(f"   Marker END: Hàng {region['row']} | cột {end_col}")
        
        self.marker_set = set()
        for m in self.marker_positions:
            self.marker_set.add((m['row'], m['col']))
        
        # DEBUG: In danh sách marker
        print(f"\n=== DANH SÁCH MARKER ===")
        for m in sorted(self.marker_positions, key=lambda x: (x['row'], x['col'])):
            print(f"   Hàng {m['row']:3d} | Cột {m['col']:3d} | {m['type']}")
        
        # Tạo ma trận đánh dấu hình chữ nhật (chỉ cho vùng có độ dài > 12)
        self.force_rectangular = np.zeros_like(self.pattern_matrix, dtype=bool)
        for region in self.pattern_regions:
            region_length = region['end'] - region['start'] + 1
            if region_length > 12:
                for c in range(region['start'], region['end'] + 1):
                    if (region['row'], c) not in self.marker_set:
                        self.force_rectangular[region['row'], c] = True
                print(f"   ✓ HÌNH CHỮ NHẬT: hàng {region['row']}, cột {region['start']}-{region['end']} (dài {region_length} > 12)")
            else:
                print(f"   ✗ BỎ QUA (hình thoi): hàng {region['row']}, cột {region['start']}-{region['end']} (dài {region_length} <= 12)")
        
        print(f"\n=== THỐNG KÊ ===")
        print(f"   Số vùng RAW: {len(raw_regions)}")
        print(f"   Số vùng sau MERGE: {len(self.pattern_regions)}")
        print(f"   Số marker: {len(self.marker_positions)}")
        print(f"   Số ô hình chữ nhật: {np.sum(self.force_rectangular)}")
        print("=====================================\n")    


    def _draw_markers(self, img):
        if not self.show_markers:
            return img
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        draw = ImageDraw.Draw(img)
        marker_size = self.cell_size // 3
        marker_color = (255, 255, 255)
        
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except:
            font = ImageFont.load_default()
        
        for marker in self.marker_positions:
            center_x = marker['col'] * self.cell_size + self.cell_size // 2
            center_y = marker['row'] * self.cell_size + self.cell_size // 2
            
            draw.line([(center_x - marker_size, center_y - marker_size), 
                       (center_x + marker_size, center_y + marker_size)], fill=marker_color, width=3)
            draw.line([(center_x - marker_size, center_y + marker_size), 
                       (center_x + marker_size, center_y - marker_size)], fill=marker_color, width=3)
            
            text = "S" if marker['type'] == 'start' else "E"
            draw.text((center_x - marker_size - 5, center_y - marker_size - 5), text, fill=marker_color, font=font)
        
        for region in self.pattern_regions:
            y = region['row'] * self.cell_size
            x_start = region['start'] * self.cell_size
            x_end = (region['end'] + 1) * self.cell_size
            draw.rectangle([x_start, y, x_end, y + self.cell_size], outline=(255, 255, 0), width=2)
        
        return img

    def _fix_diamond_colors(self, matrix):
        matrix = np.array(matrix)
        h, w = matrix.shape
        
        weave_mask = np.zeros_like(matrix, dtype=bool)
        for r in range(h):
            for c in range(w):
                warp_thread_index = c // self.warp_spacing
                weave_mask[r, c] = ((warp_thread_index + r) % 2 == 1)
        
        for r in range(h):
            for c in range(w):
                if not weave_mask[r, c]:
                    left_start = max(0, c - self.warp_spacing)
                    left_end = c
                    right_start = c
                    right_end = min(w, c + self.warp_spacing)
                    
                    left_half = matrix[r, left_start:left_end]
                    right_half = matrix[r, right_start:right_end]
                    
                    def get_accent_color(half):
                        non_zero = half[half != 0]
                        if len(non_zero) > 0:
                            return np.bincount(non_zero).argmax()
                        return 0
                    
                    left_color = get_accent_color(left_half)
                    right_color = get_accent_color(right_half)
                    
                    if left_color != right_color:
                        if left_color != 0:
                            accent = left_color
                        elif right_color != 0:
                            accent = right_color
                        else:
                            accent = 0
                        
                        if accent != 0:
                            matrix[r, left_start:left_end] = accent
                            matrix[r, right_start:right_end] = accent
        
        return matrix

    def _build_weave_structure(self):
        self.weave_mask = np.zeros_like(self.pattern_matrix, dtype=bool)
        for r in range(self.mat_h_cells):
            for c in range(self.mat_w_cells):
                warp_thread_index = c // self.warp_spacing
                self.weave_mask[r, c] = ((warp_thread_index + r) % 2 == 1)

    def get_weft_threads_for_row(self, r):
        row_data = self.pattern_matrix[r, :]
        unique_colors = np.unique(row_data)
        weft_A_id = self.default_bg_id
        weft_B_id = self.default_bg_id

        for color in unique_colors:
            if color != self.default_bg_id:
                weft_B_id = color
                break

        if weft_B_id == self.default_bg_id:
            weft_B_id = 4
            
        return weft_A_id, weft_B_id

    def _get_accent_color_for_border(self):
        return 4
    
    def get_woven_state(self, r, c):
        weft_A_id, weft_B_id = self.get_weft_threads_for_row(r)
        is_warp_on_top = self.weave_mask[r, c]

        if r >= self.border_top and r < self.border_top + 4:
            return 4, is_warp_on_top
        
        if r >= (self.mat_h_cells - self.border_bottom - 4) and r < (self.mat_h_cells - self.border_bottom):
            return 4, is_warp_on_top

        if r < self.border_top:
            if self.border_style == "background":
                return self.default_bg_id, is_warp_on_top
            elif self.border_style == "alternating":
                return (weft_B_id if (c // self.warp_spacing) % 2 == 0 else weft_A_id), is_warp_on_top
            else:
                return 4, is_warp_on_top
        
        if r >= (self.mat_h_cells - self.border_bottom):
            if self.border_style == "background":
                return self.default_bg_id, is_warp_on_top
            elif self.border_style == "alternating":
                return (weft_B_id if (c // self.warp_spacing) % 2 == 0 else weft_A_id), is_warp_on_top
            else:
                return 4, is_warp_on_top

        # LEFT BORDER (xen kẽ màu)
        if c < self.border_left:
            return (weft_B_id if r % 2 == 0 else weft_A_id), is_warp_on_top
        
        # RIGHT BORDER (xen kẽ màu)
        if c >= (self.mat_w_cells - self.border_right):
            return (weft_B_id if r % 2 == 0 else weft_A_id), is_warp_on_top

        # MAIN PATTERN AREA
        target_color_id = self.pattern_matrix[r, c]
        if target_color_id == weft_B_id and weft_B_id != self.default_bg_id:
            return weft_B_id, is_warp_on_top
        return weft_A_id, is_warp_on_top
    
    
    def render(self):
        """Render ảnh 3D - Đồng nhất hiệu ứng đổ bóng sợi dọc"""
        h_px = self.mat_h_cells * self.cell_size
        w_px = self.mat_w_cells * self.cell_size
        out = np.zeros((h_px, w_px, 3), dtype=np.float32)

        yy, xx = np.mgrid[0:self.cell_size, 0:self.cell_size]
        center = (self.cell_size - 1) / 2.0
        
        # === HIỆU ỨNG BO TRÒN CHO HÌNH CHỮ NHẬT ===
        dist_from_center_y = np.abs(yy - center) / center
        vertical_curve = np.cos(dist_from_center_y * np.pi / 2.0)
        vertical_curve = np.clip(vertical_curve, 0.75, 1.0)
        
        dist_to_left = xx / center
        dist_to_right = (self.cell_size - 1 - xx) / center
        left_curve = np.clip(1.0 - np.power(dist_to_left, 1.8) * 0.12, 0.88, 1.0)
        right_curve = np.clip(1.0 - np.power(dist_to_right, 1.8) * 0.12, 0.88, 1.0)
        horizontal_curve = np.minimum(left_curve, right_curve)
        
        rounded_mask = vertical_curve * horizontal_curve
        
        striation = 0.92 + 0.08 * np.sin(yy * 1.5) * np.cos(yy * 4.0)
        
        warp_profile = np.exp(-((xx - center)**2) / 8.0)
        shadow_profile = 1.0 - 0.65 * np.exp(-((xx - center)**2) / 12.0) 
        indent_profile = 1.0 - 0.12 * np.exp(-((xx - center)**2) / 4.0)
        
        warp_color_base = np.array([230, 225, 215], dtype=np.float32)

        block_px = self.warp_spacing * self.cell_size          
        half_block_px = block_px / 2.0                         
        warp_thread_half = self.cell_size / 2.0                

        np.random.seed(42)
        global_noise = np.random.uniform(0.88, 1.06, (self.mat_h_cells * self.cell_size, 
                                                    self.mat_w_cells * self.cell_size))

        for i in range(self.mat_h_cells):
            for j in range(self.mat_w_cells):
                y0, x0 = i * self.cell_size, j * self.cell_size

                color_id, _ = self.get_woven_state(i, j)
                color = self.color_map.get(color_id, self.default_bg_color).astype(np.float32)

                x_global = j * self.cell_size + xx  
                shifted_x = x_global - warp_thread_half
                nearest_warp_col_idx = np.round(shifted_x / block_px).astype(np.int32)
                x_nearest_warp_center = nearest_warp_col_idx * block_px + warp_thread_half
                
                dist_from_warp = np.abs(x_global - x_nearest_warp_center) / half_block_px
                dist_from_warp = np.clip(dist_from_warp, 0.0, 1.0)

                # === LOGIC QUYẾT ĐỊNH HÌNH DẠNG ===
                use_rectangular = False
                is_marker = (i, j) in self.marker_set
                
                if is_marker:
                    use_rectangular = False
                    warp_on_top_scalar = True
                elif self.force_rectangular[i, j]:
                    use_rectangular = True
                
                warp_on_top_array = ((nearest_warp_col_idx + i) % 2 == 1)
                
                if not is_marker:
                    warp_on_top_scalar = warp_on_top_array[self.cell_size//2, self.cell_size//2]
                
                # === XÁC ĐỊNH SỢI DỌC THỨ 8 ===
                is_warp_at_8th = False
                if (j % self.warp_spacing == 0):
                    warp_index = j // self.warp_spacing + 1
                    if warp_index == 8:
                        is_warp_at_8th = True
                
                # === TÍNH TOÁN diamond_width, height_x, under_warp_shadow ===
                if use_rectangular:
                    # HÌNH CHỮ NHẬT: bo tròn
                    diamond_width = rounded_mask
                    warp_for_shadow = np.zeros_like(dist_from_warp, dtype=bool)
                    height_x = 0.85 * diamond_width
                    deep_shadow = 1.0 - 0.7 * np.exp(-(dist_from_warp**2) / 0.1)
                    under_warp_shadow = np.where(warp_for_shadow, deep_shadow, 1.0)
                    
                elif is_marker:
                    # MARKER: VUỐT NHỌN
                    taper_factor = 0.28
                    diamond_width = np.where(
                        warp_on_top_array,
                        1.0 - taper_factor * (1.0 - np.exp(-2.8 * (1.0 - dist_from_warp))),
                        1.0 - taper_factor * (1.0 - np.exp(-2.8 * dist_from_warp))
                    )
                    diamond_width = np.clip(diamond_width, 0.18, 1.0)
                    
                    height_x = np.where(
                        warp_on_top_array,
                        0.45 + 0.55 * (1.0 - np.exp(-2.5 * (1.0 - dist_from_warp))),
                        0.9 - 0.45 * (1.0 - np.exp(-2.5 * dist_from_warp))
                    )
                    
                    deep_shadow = 1.0 - 0.85 * np.exp(-(dist_from_warp**2) / 0.045)
                    under_warp_shadow = np.where(warp_on_top_array, deep_shadow, 1.0)
                    warp_for_shadow = warp_on_top_array
                    
                else:
                    # PADDING - HÌNH THOI BÌNH THƯỜNG
                    taper_factor = 0.35
                    diamond_width = np.where(
                        warp_on_top_array,
                        1.0 - taper_factor * (2.0 - dist_from_warp), 
                        1.0 - taper_factor * dist_from_warp          
                    )
                    diamond_width = np.clip(diamond_width, 0.2, 1.0)
                    
                    height_x = np.where(
                        warp_on_top_array,
                        0.38 + 0.62 * (dist_from_warp ** 1.5),
                        0.92 - 0.22 * dist_from_warp
                    )
                    
                    deep_shadow = 1.0 - 0.8 * np.exp(-(dist_from_warp**2) / 0.1)
                    under_warp_shadow = np.where(warp_on_top_array, deep_shadow, 1.0)
                    warp_for_shadow = warp_on_top_array
                
                # === TÍNH TOÁN HIỆU ỨNG ÁNH SÁNG ===
                norm_dist_y = np.abs(yy - center) / (self.cell_size / 1.6)
                effective_dist_y = norm_dist_y / np.maximum(diamond_width, 0.15) * 0.9
                wave_offset = np.sin(i * 0.13) * 0.04
                effective_dist_y = np.clip(effective_dist_y + wave_offset, 0.0, 1.1)
                dist_from_sub_center = np.abs(effective_dist_y - 0.5)
                norm_sub_dist = np.clip(dist_from_sub_center / 0.5, 0.0, 1.0)
                height_y_local = np.cos(norm_sub_dist * np.pi / 2.0)
                center_gap_shadow = 1.0 - 0.8 * np.exp(-(effective_dist_y**2) / 0.025)
                height_y_local = height_y_local * center_gap_shadow
                ao_local = np.power(height_y_local, 0.55) * under_warp_shadow
                shade = (0.45 * (height_y_local * height_x) + 0.55 * ao_local)
                spec = np.power(height_y_local, 1.4) * 0.45 * height_x * under_warp_shadow

                roughness_noise = global_noise[y0:y0+self.cell_size, x0:x0+self.cell_size, np.newaxis]
                
                base_tile = (color * shade[:,:,None] * striation[:,:,None] * roughness_noise) + spec[:,:,None]
                
                # === VẼ SỢI DỌC ===
                if (j % self.warp_spacing == 0):
                    # Xác định có cần vẽ sợi dọc nổi không
                    should_draw_warp = False
                    warp_alpha_mult = 0.7
                    
                    if is_marker:
                        should_draw_warp = True
                        warp_alpha_mult = 0.85  # Marker nổi rõ hơn
                    elif not use_rectangular:
                        should_draw_warp = True
                        warp_alpha_mult = 0.7   # Padding bình thường
                    elif use_rectangular and is_warp_at_8th:
                        should_draw_warp = True
                        warp_alpha_mult = 0.7   # Sợi dọc thứ 8 giống padding
                    
                    if should_draw_warp and warp_on_top_scalar:
                        # Công thức chung cho tất cả sợi dọc nổi (đồng nhất hiệu ứng)
                        shadowed_base = base_tile * shadow_profile[:,:,None]
                        warp_layer = warp_color_base * roughness_noise
                        warp_alpha = (warp_profile * warp_alpha_mult)[:,:,None]
                        tile = warp_layer * warp_alpha + shadowed_base * (1.0 - warp_alpha)
                    elif not use_rectangular and not warp_on_top_scalar:
                        # Sợi dọc nằm dưới (bình thường)
                        tile = base_tile * indent_profile[:,:,None]
                    else:
                        tile = base_tile
                else:
                    tile = base_tile

                out[y0:y0+self.cell_size, x0:x0+self.cell_size] = np.clip(tile, 0, 255)

        # Làm mượt nhẹ
        img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        img = img.filter(ImageFilter.GaussianBlur(radius=0.25)) 
        img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=100, threshold=2))
        
        if self.show_markers:
            img = self._draw_markers(img)
        
        return img
        


if __name__ == "__main__":
    ensure_sample_library_exists()
    
    parser = argparse.ArgumentParser(description='Render 3D vải dệt Jacquard')
    parser.add_argument("--key", type=str, default="sample_pattern")
    parser.add_argument("--scale", type=float, default=0.15)
    parser.add_argument("--border_style", type=str, default="background",
                       choices=["alternating", "background", "accent"])
    parser.add_argument("--border_top", type=int, default=50)
    parser.add_argument("--border_bottom", type=int, default=50)
    parser.add_argument("--border_left", type=int, default=24)
    parser.add_argument("--border_right", type=int, default=24)
    parser.add_argument("--show_markers", action="store_true")
    
    args = parser.parse_args()

    print(f"[*] Đang render pattern: '{args.key}' ...")
    
    try:
        weaver = SmartWeaver3D(
            pattern_key=args.key, 
            border_style=args.border_style,
            border_top=args.border_top,
            border_bottom=args.border_bottom,
            border_left=args.border_left,
            border_right=args.border_right,
            show_markers=args.show_markers
        )
        result_img = weaver.render()

        if args.scale != 1.0:
            new_size = (int(result_img.width * args.scale), int(result_img.height * args.scale))
            result_img = result_img.resize(new_size, Image.Resampling.LANCZOS)
        
        suffix = "_with_markers" if args.show_markers else ""
        output_name = f"woven_output_{args.key}_{args.border_style}{suffix}.png"
        result_img.save(output_name)
        print(f"[+] Đã lưu: {output_name}")
        
    except Exception as e:
        print(f"[-] Lỗi: {e}")
        import traceback
        traceback.print_exc()
