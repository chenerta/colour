from PIL import Image
img = Image.open('试验原图.png')
print(f'Size: {img.size}, Mode: {img.mode}')
