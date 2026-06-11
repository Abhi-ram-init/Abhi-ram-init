from PIL import Image

def find_center():
    img_path = r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\gtr_r34_transparent.png"
    img = Image.open(img_path).convert("L")  # Grayscale
    
    # We know the front wheel is roughly around x: 700-850, y: 480-630
    box = (700, 480, 850, 630)
    wheel_region = img.crop(box)
    
    pixels = wheel_region.load()
    width, height = wheel_region.size
    
    x_indices = []
    y_indices = []
    
    for y in range(height):
        for x in range(width):
            if pixels[x, y] > 50:
                x_indices.append(x)
                y_indices.append(y)
    
    if len(x_indices) > 0:
        cx_rel = sum(x_indices) / len(x_indices)
        cy_rel = sum(y_indices) / len(y_indices)
        
        # Absolute center
        cx = 700 + cx_rel
        cy = 480 + cy_rel
        
        # Find the bounding box of the white pixels to find a precise center
        min_x, max_x = min(x_indices), max(x_indices)
        min_y, max_y = min(y_indices), max(y_indices)
        
        cx_box = 700 + (min_x + max_x) / 2.0
        cy_box = 480 + (min_y + max_y) / 2.0
        
        print(f"Center of mass: ({cx:.2f}, {cy:.2f})")
        print(f"Bounding box center: ({cx_box:.2f}, {cy_box:.2f})")
        
        radius = (max_x - min_x) / 2.0
        print(f"Radius: {radius:.2f}")

if __name__ == "__main__":
    find_center()
