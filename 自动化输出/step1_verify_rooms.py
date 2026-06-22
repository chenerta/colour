"""
工序1：在原图上画出房间边界框，验证vision识别的坐标是否正确
只画边界线，不加任何暖通内容
"""
from PIL import Image, ImageDraw, ImageFont

img = Image.open(r'C:\Users\apple\Desktop\湖滨壹号_自动化输出\1F_page4.png')
draw = ImageDraw.Draw(img)

# vision识别的房间边界 (x_min, y_min, x_max, y_max) — 像素坐标
rooms = {
    '庭院花园': (96, 205, 332, 766),
    '休闲区':   (329, 224, 594, 751),
    '楼梯厅':   (591, 213, 753, 535),
    '酒柜':     (590, 501, 644, 536),
    '餐厅':     (329, 553, 668, 752),
    '厨房':     (750, 534, 865, 748),
    '卫生间':   (751, 240, 854, 380),
    '入口门厅': (863, 378, 945, 655),
}

# 每个房间不同颜色的边界线
colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#FF8800', '#8800FF']

try:
    font = ImageFont.truetype("arial.ttf", 16)
except:
    font = ImageFont.load_default()

for (name, (x0, y0, x1, y1)), color in zip(rooms.items(), colors):
    # 画2px粗的边界线
    draw.rectangle([x0, y0, x1, y1], outline=color, width=2)
    # 标注房间名
    draw.text((x0 + 3, y0 + 3), name, fill=color, font=font)

out = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出\1F_step1_verify.png'
img.save(out)
print(f'工序1完成: {out}')
print(f'请用vision检查边界框是否准确覆盖了每个房间')
