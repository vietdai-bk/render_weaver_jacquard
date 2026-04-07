import json
import numpy as np
import argparse
from PIL import Image, ImageFilter

class SmartWeaver3D:
    def __init__(self, pattern_key, library_file="pattern_library.json"):
        self.library_file = library_file
        self.pattern_key = pattern_key
        self.cell_size = 15 
        
        with open(self.library_file, 'r', encoding='utf-8') as f:
            pattern_data = json.load(f)[self.pattern_key]
            
        self.pattern_matrix = np.array(pattern_data["matrix"])
        self.mat_h_cells, self.mat_w_cells = self.pattern_matrix.shape
        
        self.color_map = {int(k): np.array(v) for k, v in pattern_data["color_map"].items()}
        self.default_bg = self.color_map.get(0, np.array([235, 215, 170]))

    def _get_color_at(self, r, c):
        r = max(0, min(int(r), self.mat_h_cells - 1))
        c = max(0, min(int(c), self.mat_w_cells - 1))
        val = self.pattern_matrix[r, c]
        return self.color_map.get(val, self.default_bg)

    def render(self):
        h_px, w_px = self.mat_h_cells * self.cell_size, self.mat_w_cells * self.cell_size
        out = np.zeros((h_px, w_px, 3), dtype=np.float32)
        
        yy, xx = np.mgrid[0:self.cell_size, 0:self.cell_size]
        center = (self.cell_size - 1) / 2.0
        
        norm_dist_y = np.abs(yy - center) / (self.cell_size / 2.0)
        height_y = np.cos(norm_dist_y * np.pi / 2.0)
        ao = np.power(height_y, 0.7) 
        fiber_grain = 0.88 + 0.12 * np.sin(yy * 3.0) 

        warp_spacing = 8  
        warp_width = 4    
        warp_start = (self.cell_size - warp_width) // 2
        warp_end = warp_start + warp_width
        
        warp_center_dist = np.abs(xx - center) / (warp_width / 2.0)
        warp_mask = (xx >= warp_start) & (xx < warp_end)
        warp_shade = 0.3 + 0.7 * np.cos(np.clip(warp_center_dist, 0, 1) * np.pi / 2.0)
        warp_color_base = np.array([225, 215, 195], dtype=np.float32) 

        block_width_px = warp_spacing * self.cell_size
        block_center_px = block_width_px / 2.0

        for i in range(self.mat_h_cells):
            for j in range(self.mat_w_cells):
                y0, x0 = i * self.cell_size, j * self.cell_size
                j_block_center = (j // warp_spacing) * warp_spacing + (warp_spacing // 2)
                target_color = self._get_color_at(i, j_block_center)
                
                is_pattern = not np.array_equal(target_color, self.default_bg)
                color = target_color.astype(np.float32)
                
                x_in_block = (j % warp_spacing) * self.cell_size + xx
                norm_dist_x_block = np.abs(x_in_block - block_center_px) / block_center_px
                height_x = 1.0 - 0.2 * np.power(norm_dist_x_block, 4)
                
                shade = (0.2 * (height_y * height_x) + 0.8 * ao) 
                spec = np.power(height_y, 6) * 18 * height_x 
                noise = np.random.uniform(0.96, 1.04, (self.cell_size, self.cell_size)) 
                
                base_tile = (color * shade[:,:,None] * fiber_grain[:,:,None] * noise[:,:,None]) + spec[:,:,None]
                
                if (j % warp_spacing == 0):
                    warp_on_top = False if is_pattern else ((i + (j // warp_spacing)) % 2 == 1)
                    if warp_on_top:
                        shadowed_base = (color * shade[:,:,None] * fiber_grain[:,:,None] * noise[:,:,None]) * 0.3
                        warp_pixels = warp_color_base * warp_shade[:,:,None] * noise[:,:,None]
                        tile = np.where(warp_mask[:,:,None], warp_pixels, shadowed_base)
                    else:
                        tile = base_tile + (np.exp(-((xx - center)**2) / 8.0) * 25.0)[:,:,None]
                else:
                    tile = base_tile
                
                out[y0:y0+self.cell_size, x0:x0+self.cell_size] = tile
                
        img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=2))
        return img

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", type=str, required=True)
    args = parser.parse_args()

    weaver = SmartWeaver3D(pattern_key=args.key)
    weaver.render().save(f"realistic_jacquard_{args.key}.png")
    print(f"Finished: realistic_jacquard_{args.key}.png")
      
## python weaver_render.py --key ete