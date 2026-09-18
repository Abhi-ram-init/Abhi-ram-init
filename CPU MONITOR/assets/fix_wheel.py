from PIL import Image

def fix_wheel_center():
    # Load the solid wheel
    img_path = r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\wheel_r34_solid.png"
    img = Image.open(img_path).convert("RGBA")
    
    pixels = img.load()
    width, height = img.size
    
    # Find all "black" pixels (the rims/tires)
    # The image has white background, transparent edges, and black rims.
    x_coords = []
    y_coords = []
    
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 128:  # Not transparent
                if r < 100 and g < 100 and b < 100:  # Dark pixel
                    x_coords.append(x)
                    y_coords.append(y)
                    
    if not x_coords:
        print("No black pixels found!")
        return
        
    cx = sum(x_coords) / len(x_coords)
    cy = sum(y_coords) / len(y_coords)
    
    print(f"Current center of mass of rims: ({cx:.2f}, {cy:.2f})")
    print(f"Image geometric center: ({width/2}, {height/2})")
    
    # Calculate offset
    dx = cx - (width / 2)
    dy = cy - (height / 2)
    print(f"Offset: dx={dx:.2f}, dy={dy:.2f}")
    
    # To fix it, we shift the image by -dx, -dy
    # We can do this by pasting the image onto a new transparent background
    fixed_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shift_x = int(round(-dx))
    shift_y = int(round(-dy))
    
    fixed_img.paste(img, (shift_x, shift_y))
    
    fixed_img.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\wheel_r34_solid_fixed.png")
    print("Saved fixed wheel to wheel_r34_solid_fixed.png")

if __name__ == "__main__":
    fix_wheel_center()
