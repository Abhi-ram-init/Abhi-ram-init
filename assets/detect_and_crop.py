from PIL import Image, ImageDraw, ImageOps
import math

def process_and_crop():
    # Load original image
    img = Image.open('e:/PROGRAMMING/GITHUB/Abhi-ram-init/assets/gtr_original.png')
    img = img.convert("RGBA")
    width, height = img.size
    pixels = img.load()
    
    # 1. Make white background transparent
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # White background threshold
            if r > 245 and g > 245 and b > 245:
                pixels[x, y] = (0, 0, 0, 0)
                
    # 2. Detect wheels automatically
    # Scan lower half of the image for dark pixels
    y_min, y_max = int(height * 0.45), int(height * 0.75)
    mid_x = width // 2
    
    left_x, left_y = [], []
    right_x, right_y = [], []
    
    for y in range(y_min, y_max):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # Look for dark tire/rim pixels
            if r < 100 and g < 100 and b < 100 and a > 100:
                if x < mid_x:
                    left_x.append(x)
                    left_y.append(y)
                else:
                    right_x.append(x)
                    right_y.append(y)
                    
    left_x.sort()
    left_y.sort()
    right_x.sort()
    right_y.sort()
    
    wl_cx = left_x[len(left_x) // 2]
    wl_cy = left_y[len(left_y) // 2]
    wr_cx = right_x[len(right_x) // 2]
    wr_cy = right_y[len(right_y) // 2]
    
    print(f"Detected Front Wheel Center: ({wl_cx}, {wl_cy})")
    print(f"Detected Rear Wheel Center: ({wr_cx}, {wr_cy})")
    
    # Let's verify radius: standard R35 alloy wheel is around 11.5% of image width
    # 1024 * 0.115 = 118 pixels. Let's crop with radius = 112 to make sure it's snug
    r = 112
    
    # 3. Clean Bounding Box of the car body (non-transparent pixels)
    row_counts = []
    for y in range(height):
        count = sum(1 for x in range(width) if pixels[x, y][3] > 0)
        row_counts.append(count)
        
    col_counts = []
    for x in range(width):
        count = sum(1 for y in range(height) if pixels[x, y][3] > 0)
        col_counts.append(count)
        
    threshold = 5
    y_start = next(i for i, c in enumerate(row_counts) if c > threshold)
    y_end = len(row_counts) - next(i for i, c in enumerate(reversed(row_counts)) if c > threshold)
    x_start = next(i for i, c in enumerate(col_counts) if c > threshold)
    x_end = len(col_counts) - next(i for i, c in enumerate(reversed(col_counts)) if c > threshold)
    
    print(f"Clean Bounding Box: ({x_start}, {y_start}, {x_end}, {y_end})")
    print(f"Clean size: {x_end - x_start} x {y_end - y_start}")
    
    # 4. Extract Wheel
    # Crop front wheel from original transparent image
    wheel_box = (wl_cx - r, wl_cy - r, wl_cx + r, wl_cy + r)
    wheel_img = img.crop(wheel_box)
    
    # Circular mask for wheel
    mask = Image.new("L", (2 * r, 2 * r), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, 2 * r, 2 * r), fill=255)
    
    wheel_circle = Image.new("RGBA", (2 * r, 2 * r))
    wheel_circle.paste(wheel_img, (0, 0), mask=mask)
    
    # Convert wheel to B&W
    wheel_bw = ImageOps.grayscale(wheel_circle).convert("RGBA")
    wheel_bw.save('e:/PROGRAMMING/GITHUB/Abhi-ram-init/assets/wheel.png')
    print("Saved wheel.png")
    
    # 5. Create Car Body with shadowed wheel wells
    car_body = img.copy()
    draw_body = ImageDraw.Draw(car_body)
    shadow_color = (20, 20, 20, 255)
    draw_body.ellipse((wl_cx - r + 2, wl_cy - r + 2, wl_cx + r - 2, wl_cy + r - 2), fill=shadow_color)
    draw_body.ellipse((wr_cx - r + 2, wr_cy - r + 2, wr_cx + r - 2, wr_cy + r - 2), fill=shadow_color)
    
    car_body_clean = car_body.crop((x_start, y_start, x_end, y_end))
    car_body_bw = ImageOps.grayscale(car_body_clean).convert("RGBA")
    car_body_bw.save('e:/PROGRAMMING/GITHUB/Abhi-ram-init/assets/car_body.png')
    print("Saved car_body.png")
    
    # 6. Create Tray Icon
    tray_icon = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    aspect = car_body_bw.width / car_body_bw.height
    new_w = 32
    new_h = int(32 / aspect)
    car_resized = car_body_bw.resize((new_w, new_h), Image.Resampling.LANCZOS)
    tray_icon.paste(car_resized, (0, (32 - new_h) // 2))
    tray_icon.save('e:/PROGRAMMING/GITHUB/Abhi-ram-init/assets/tray_icon.png')
    print("Saved tray_icon.png")
    
    # Print the adjusted wheel centers for main.py configuration
    wl_cx_clean = wl_cx - x_start
    wl_cy_clean = wl_cy - y_start
    wr_cx_clean = wr_cx - x_start
    wr_cy_clean = wr_cy - y_start
    print("\n" + "="*50)
    print("COORDINATES FOR main.py:")
    print(f"Front Wheel Center: ({wl_cx_clean}, {wl_cy_clean})")
    print(f"Rear Wheel Center: ({wr_cx_clean}, {wr_cy_clean})")
    print(f"Original Bounding Box width: {x_end - x_start}")
    print("="*50)

if __name__ == '__main__':
    process_and_crop()
