from PIL import Image

def analyze():
    img = Image.open('e:/PROGRAMMING/GITHUB/Abhi-ram-init/assets/gtr_original.png')
    img = img.convert("RGBA")
    width, height = img.size
    
    # Try different thresholds for white/off-white background removal
    for threshold in range(250, 210, -5):
        temp_img = img.copy()
        pixels = temp_img.load()
        
        # Mark background pixels transparent
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                if r > threshold and g > threshold and b > threshold:
                    pixels[x, y] = (0, 0, 0, 0)
                    
        # Check non-transparent bbox
        bbox = temp_img.getbbox()
        if bbox:
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            print(f"Threshold {threshold}: Bounding Box = {bbox}, Size = {w}x{h}")
            # If height is significantly smaller than 1024, we found the car boundary!
            if h < 800:
                print(f"--> Optimal threshold found: {threshold}!")
                break

if __name__ == '__main__':
    analyze()
