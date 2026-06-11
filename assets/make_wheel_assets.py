from PIL import Image, ImageDraw

def make_assets():
    img = Image.open(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\gtr_r34_transparent.png").convert("RGBA")
    
    # From the image we can see:
    # Rear wheel RIM center is approximately at: x=228, y=567
    # Front wheel RIM center is approximately at: x=800, y=567
    # The actual wheel (just rim + tyre, not the fender) radius is about 75px
    
    # Scan tightly INSIDE the wheel arch only
    def find_rim_center(x_start, x_end, y_start, y_end):
        pixels = img.load()
        # Collect all dark non-transparent pixels (the lines making the wheel)
        xs, ys = [], []
        for y in range(y_start, y_end):
            for x in range(x_start, x_end):
                r, g, b, a = pixels[x, y]
                if a > 100 and r < 180 and g < 180 and b < 180:
                    xs.append(x)
                    ys.append(y)
        if not xs:
            return None
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        rx = (max(xs) - min(xs)) / 2.0
        ry = (max(ys) - min(ys)) / 2.0
        r = min(rx, ry)  # use smaller span = actual wheel
        print(f"  span x:[{min(xs)}-{max(xs)}] y:[{min(ys)}-{max(ys)}]")
        print(f"  center=({cx:.1f},{cy:.1f}) tight_radius={r:.1f}")
        return cx, cy, r
    
    # Tight scan region — just the wheel arch area
    print("Rear wheel (tight scan):")
    rear = find_rim_center(155, 325, 495, 645)
    print("Front wheel (tight scan):")
    front = find_rim_center(725, 895, 495, 645)
    
    r_cx, r_cy, r_r = rear
    f_cx, f_cy, f_r = front
    radius = int(min(r_r, f_r))
    print(f"\nRadius: {radius}")
    
    def crop_wheel_circle(cx, cy, radius):
        icx, icy = int(round(cx)), int(round(cy))
        region = img.crop((icx - radius, icy - radius, icx + radius, icy + radius))
        
        # Anti-aliased circular mask
        big = radius * 2 * 4
        mask_big = Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask_big).ellipse((0, 0, big, big), fill=255)
        mask = mask_big.resize((radius*2, radius*2), Image.Resampling.LANCZOS)
        
        out = Image.new("RGBA", (radius*2, radius*2), (0,0,0,0))
        out.paste(region, (0,0), mask)
        return out
    
    # Save wheel
    wheel = crop_wheel_circle(r_cx, r_cy, radius)
    wheel.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\wheel_final.png")
    print("Saved wheel_final.png")
    
    # Erase wheels from body
    body = img.copy()
    d = ImageDraw.Draw(body)
    ir_cx, ir_cy = int(round(r_cx)), int(round(r_cy))
    if_cx, if_cy = int(round(f_cx)), int(round(f_cy))
    d.ellipse((ir_cx-radius, ir_cy-radius, ir_cx+radius, ir_cy+radius), fill=(0,0,0,0))
    d.ellipse((if_cx-radius, if_cy-radius, if_cx+radius, if_cy+radius), fill=(0,0,0,0))
    body.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\car_body_final.png")
    print("Saved car_body_final.png")
    
    print(f"\nCoords for main.py:")
    print(f"  rear_cx={r_cx}, rear_cy={r_cy}, front_cx={f_cx}, front_cy={f_cy}")

if __name__ == "__main__":
    make_assets()
