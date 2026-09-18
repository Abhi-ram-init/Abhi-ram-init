from PIL import Image, ImageDraw

def perfect_crop():
    # Load original un-inverted R34 image
    img = Image.open(r"C:\Users\Abhiram\.gemini\antigravity\brain\a3f158f3-d8b8-408b-9d1f-ec13fff26bf2\gtr_r34_bw_1781158143306.png").convert("RGBA")
    
    # Search box for the rear wheel
    box = (140, 470, 310, 640)
    region = img.crop(box)
    pixels = region.load()
    width, height = region.size
    
    min_x, max_x = width, 0
    min_y, max_y = height, 0
    
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if r < 100 and g < 100 and b < 100:  # black pixel
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
                
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    radius = min(max_x - cx, max_y - cy)
    
    abs_cx = 140 + cx
    abs_cy = 470 + cy
    
    int_radius = int(radius)
    perfect_box = (abs_cx - int_radius, abs_cy - int_radius, abs_cx + int_radius, abs_cy + int_radius)
    perfect_wheel = img.crop(perfect_box)
    
    mask = Image.new("L", (int_radius*2, int_radius*2), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, int_radius*2, int_radius*2), fill=255)
    
    final_wheel = Image.new("RGBA", perfect_wheel.size, (0,0,0,0))
    final_wheel.paste(perfect_wheel, (0,0), mask)
    final_wheel.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\wheel_r34_perfect.png")

    # Inverted body image
    body = Image.open(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\gtr_r34_transparent.png").convert("RGBA")
    draw_body = ImageDraw.Draw(body)
    
    # Search box for the front wheel
    box_f = (690, 470, 860, 640)
    region_f = img.crop(box_f)
    pixels_f = region_f.load()
    min_x_f, max_x_f = region_f.width, 0
    for y in range(region_f.height):
        for x in range(region_f.width):
            r, g, b, a = pixels_f[x, y]
            if r < 100 and g < 100 and b < 100:
                if x < min_x_f: min_x_f = x
                if x > max_x_f: max_x_f = x
                
    cx_f = (min_x_f + max_x_f) / 2.0
    abs_cx_f = 690 + cx_f
    
    # Erase wheels from body using transparent circles
    draw_body.ellipse((abs_cx - int_radius, abs_cy - int_radius, abs_cx + int_radius, abs_cy + int_radius), fill=(0,0,0,0))
    draw_body.ellipse((abs_cx_f - int_radius, abs_cy - int_radius, abs_cx_f + int_radius, abs_cy + int_radius), fill=(0,0,0,0))
    body.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\car_body_r34_perfect.png")
    
    with open(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\perfect_coords.txt", "w") as f:
        f.write(f"{abs_cx},{abs_cy},{abs_cx_f}")
        
    print(f"Perfect coords: rear_x={abs_cx}, front_x={abs_cx_f}, y={abs_cy}")

if __name__ == '__main__':
    perfect_crop()
