from PIL import Image, ImageDraw

def process():
    # The original R34 black and white image (not inverted)
    img_path = r"C:\Users\Abhiram\.gemini\antigravity\brain\a3f158f3-d8b8-408b-9d1f-ec13fff26bf2\gtr_r34_bw_1781158143306.png"
    img = Image.open(img_path).convert("RGBA")
    
    # Precise wheel coordinates
    r_cx, r_cy = 224, 554
    radius = 75
    
    # 1. Extract the wheel
    wheel = img.crop((r_cx - radius, r_cy - radius, r_cx + radius, r_cy + radius))
    
    # Apply circular mask to the wheel to ensure perfectly round edges
    mask = Image.new("L", (radius*2, radius*2), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, radius*2, radius*2), fill=255)
    
    wheel_masked = Image.new("RGBA", wheel.size, (0, 0, 0, 0))
    wheel_masked.paste(wheel, (0, 0), mask)
    
    # Save the original solid black-and-white wheel
    wheel_masked.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\wheel_r34_solid.png")
    print("Cropped original wheel in a circular way!")

if __name__ == "__main__":
    process()
