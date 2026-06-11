from PIL import Image, ImageDraw

def process():
    img_path = r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\gtr_r34_transparent.png"
    img = Image.open(img_path).convert("RGBA")
    
    # Wheel coordinates
    r_cx, r_cy = 224, 554
    f_cx, f_cy = 774, 554
    radius = 75
    
    # 1. Extract the rear wheel
    wheel = img.crop((r_cx - radius, r_cy - radius, r_cx + radius, r_cy + radius))
    
    # Apply circular mask to the wheel to ensure clean edges
    mask = Image.new("L", (radius*2, radius*2), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, radius*2, radius*2), fill=255)
    
    wheel_masked = Image.new("RGBA", wheel.size, (0, 0, 0, 0))
    wheel_masked.paste(wheel, (0, 0), mask)
    wheel_masked.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\wheel_r34.png")
    
    # 2. Erase the wheels from the car body
    car_body = img.copy()
    draw_body = ImageDraw.Draw(car_body)
    
    # Draw transparent circles where the wheels were
    draw_body.ellipse((r_cx - radius, r_cy - radius, r_cx + radius, r_cy + radius), fill=(0,0,0,0))
    draw_body.ellipse((f_cx - radius, f_cy - radius, f_cx + radius, f_cy + radius), fill=(0,0,0,0))
    
    # Optional: crop the car body to remove unnecessary top/bottom empty space
    # Bounding box of the car is approx: x: 30 to 970, y: 350 to 650
    # We will just save the whole 1024x1024 image for simplicity, and scale it in Tkinter
    car_body.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\car_body_r34.png")
    print("Cropping complete!")

if __name__ == "__main__":
    process()
