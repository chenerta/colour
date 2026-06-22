"""
工序1（重做）：用PDF的可靠数据确定房间边界
步骤：
1. 提取PDF文字位置 → 确定每个房间名在哪
2. 提取PDF墙体线条 → 确定房间的边界
3. 把文字+墙体画在渲染图上，人工验证
"""
import fitz
from PIL import Image, ImageDraw, ImageFont

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

doc = fitz.open(pdf_path)
page = doc[3]  # 第4页 = 1F首层

# ===== 步骤1：提取所有文字和位置 =====
print("=== 步骤1：房间名标签 ===")
blocks = page.get_text('dict')['blocks']
room_labels = []
all_texts = []
for b in blocks:
    if 'lines' in b:
        for line in b['lines']:
            for span in line['spans']:
                t = span['text'].strip()
                if t and len(t) > 1:
                    x0, y0, x1, y1 = span['bbox']
                    cx = (x0 + x1) / 2
                    cy = (y0 + y1) / 2
                    all_texts.append((t, cx, cy, x0, y0, x1, y1))

# 过滤出房间名标签（中文2-4个字）
room_keywords = ['厨房', '卫生间', '餐厅', '庭院', '花园', '休闲', '楼梯', '酒柜', 
                 '客厅', '卧室', '书房', '影音', '品茶', '娱乐', '车库', '鞋帽', '衣帽',
                 '储藏', '设备', '手工', '琴房', '阳台', '露台', '主卫', '主卧']
for t, cx, cy, x0, y0, x1, y1 in all_texts:
    for kw in room_keywords:
        if kw in t and 'TITLE' not in t and 'PROJECT' not in t:
            room_labels.append((t, cx, cy, x0, y0, x1, y1))
            print(f"  房间: '{t}' 位置: PDF({cx:.0f},{cy:.0f})")
            break

# ===== 步骤2：提取PDF路径（墙体线条）=====
print("\n=== 步骤2：墙体线条 ===")
paths = page.get_drawings()
print(f"  总路径数: {len(paths)}")

# 收集所有线段
h_lines = []  # 水平线
v_lines = []  # 垂直线
all_lines = []
for p in paths:
    for item in p["items"]:
        if item[0] == "l":  # line
            x0, y0 = item[1].x, item[1].y
            x1, y1 = item[2].x, item[2].y
            length = ((x1-x0)**2 + (y1-y0)**2) ** 0.5
            if length > 30:  # 只要长线段（墙体）
                all_lines.append((x0, y0, x1, y1, length))
                if abs(y0 - y1) < 2:  # 水平
                    h_lines.append((x0, y0, x1, y1))
                elif abs(x0 - x1) < 2:  # 垂直
                    v_lines.append((x0, y0, x1, y1))

print(f"  长线段(>30pt): {len(all_lines)}")
print(f"  水平墙线: {len(h_lines)}")
print(f"  垂直墙线: {len(v_lines)}")

# ===== 步骤3：在渲染图上画出所有信息 =====
img = Image.open(f'{out_dir}/1F_page4.png')
pw, ph = page.rect.width, page.rect.height
scale_x = img.width / pw
scale_y = img.height / ph
print(f"\n=== 坐标映射 ===")
print(f"  PDF尺寸: {pw:.0f}x{ph:.0f}")
print(f"  图片尺寸: {img.width}x{img.height}")
print(f"  scale_x={scale_x:.2f}, scale_y={scale_y:.2f}")

draw = ImageDraw.Draw(img)

# 画所有墙体线条（灰色细线）
for x0, y0, x1, y1 in h_lines + v_lines:
    ix0, iy0 = int(x0 * scale_x), int(y0 * scale_y)
    ix1, iy1 = int(x1 * scale_x), int(y1 * scale_y)
    draw.line([(ix0, iy0), (ix1, iy1)], fill='#888888', width=1)

# 画房间名标签位置（红色十字+文字）
try:
    font = ImageFont.truetype("arial.ttf", 14)
    font_big = ImageFont.truetype("arial.ttf", 20)
except:
    font = ImageFont.load_default()
    font_big = font

for name, cx, cy, x0, y0, x1, y1 in room_labels:
    ix, iy = int(cx * scale_x), int(cy * scale_y)
    # 红色十字标记
    draw.line([(ix-15, iy), (ix+15, iy)], fill='red', width=2)
    draw.line([(ix, iy-15), (ix, iy+15)], fill='red', width=2)
    draw.text((ix+5, iy-20), name, fill='red', font=font)

out = f'{out_dir}/1F_step1_walls_and_labels.png'
img.save(out)
print(f"\n工序1输出: {out}")
print("图上：灰色线条=墙体，红色十字=房间名标签位置")

doc.close()
