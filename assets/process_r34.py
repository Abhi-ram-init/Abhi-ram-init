from PIL import Image, ImageOps, ImageDraw

def process_image():
    # 1. Open the original image
    img_path = r"C:\Users\Abhiram\.gemini\antigravity\brain\a3f158f3-d8b8-408b-9d1f-ec13fff26bf2\gtr_r34_bw_1781158143306.png"
    img = Image.open(img_path).convert("RGB")
    
    # 2. Invert colors (white background becomes black, black lines become white)
    inverted = ImageOps.invert(img)
    inverted.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\gtr_r34_inverted.png")
    
    # 3. Make the black background transparent
    inverted = inverted.convert("RGBA")
    data = inverted.getdata()
    
    new_data = []
    # If the pixel is close to black, make it fully transparent
    for item in data:
        # item is (R, G, B, A)
        # We consider pixels with values < 50 to be background
        if item[0] < 50 and item[1] < 50 and item[2] < 50:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append(item)
            
    inverted.putdata(new_data)
    inverted.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\gtr_r34_transparent.png")
    
    # 4. Overlay a grid so we can find the exact wheel coordinates
    grid_img = inverted.copy()
    draw = ImageDraw.Draw(grid_img)
    width, height = grid_img.size
    
    for x in range(0, width, 50):
        draw.line([(x, 0), (x, height)], fill=(255, 0, 0, 128), width=1)
        draw.text((x+2, 2), str(x), fill=(255, 0, 0, 255))
        
    for y in range(0, height, 50):
        draw.line([(0, y), (width, y)], fill=(0, 255, 0, 128), width=1)
        draw.text((2, y+2), str(y), fill=(0, 255, 0, 255))
        
    grid_img.save(r"e:\PROGRAMMING\GITHUB\Abhi-ram-init\assets\gtr_r34_grid.png")
    print(f"Size: {width}x{height}")
    print("Images saved to assets directory!")

if __name__ == "__main__":
    process_image()
