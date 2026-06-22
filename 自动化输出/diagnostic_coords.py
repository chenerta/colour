# -*- coding: utf-8 -*-
"""
诊断：确定PDF坐标到图片坐标的正确转换方式
在渲染图上画出PDF文字位置的两种可能转换，看哪个对
"""
import fitz
from PIL import Image, ImageDraw, ImageFont
import os

PDF_PATH = r"C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf"
OUT_DIR  = r"C:\Users\apple\Desktop\湖滨壹号_自动化输出"
SCALE = 2.0

def get_font(size):
    for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                continue
    return ImageFont.load_default()

doc = fitz.open(PDF_PATH)

# 只检查第6页(B2)
page_idx = 5
page = doc.load_page(page_idx)
rect = page.rect
page_h = rect.height  # 842

print(f"PDF页面: {rect.width}x{rect.height}pt")

# 提取房间名文字
texts = []
for block in page.get_text("dict")["blocks"]:
    if "lines" in block:
        for line in block["lines"]:
            for span in line["spans"]:
                txt = span["text"].strip()
                if txt and any(kw in txt for kw in ["娱乐区", "钢琴区", "客厅", "卫生间", "鞋帽间", "车库", "楼梯"]):
                    texts.append({"text": txt, "bbox": list(span["bbox"])})

# 渲染图片
mat = fitz.Matrix(SCALE, SCALE)
pix = page.get_pixmap(matrix=mat)
img_path = os.path.join(OUT_DIR, f"page_{page_idx+1}.png")
pix.save(img_path)
img = Image.open(img_path).convert("RGBA")
w, h = img.size
print(f"图片: {w}x{h}")

# 画两种转换方式的标记
font = get_font(12)

# 方式A: image_y = pdf_y * scale（不翻转）
# 方式B: image_y = (page_h - pdf_y) * scale（翻转）

for t in texts:
    txt = t["text"]
    bbox = t["bbox"]
    pdf_cx = (bbox[0] + bbox[2]) / 2
    pdf_cy = (bbox[1] + bbox[3]) / 2
    
    # 方式A
    ax = pdf_cx * SCALE
    ay = pdf_cy * SCALE
    
    # 方式B
    bx = pdf_cx * SCALE
    by = (page_h - pdf_cy) * SCALE
    
    print(f"  {txt}: PDF({pdf_cx:.0f},{pdf_cy:.0f}) → A({ax:.0f},{ay:.0f}) B({bx:.0f},{by:.0f})")
    
    # 画方式A标记（红色圆点）
    draw = ImageDraw.Draw(img)
    r = 15
    draw.ellipse([ax-r, ay-r, ax+r, ay+r], fill=(255, 0, 0, 200), outline=(255, 0, 0), width=2)
    draw.text((ax+r+5, ay-8), f"A:{txt}", fill=(255, 0, 0), font=font)
    
    # 画方式B标记（蓝色圆点）
    draw.ellipse([bx-r, by-r, bx+r, by+r], fill=(0, 0, 255, 200), outline=(0, 0, 255), width=2)
    draw.text((bx+r+5, by-8), f"B:{txt}", fill=(0, 0, 255), font=font)

# 图例
draw = ImageDraw.Draw(img)
draw.rectangle([10, 10, 500, 70], fill=(255, 255, 255, 220))
draw.text((15, 15), "红色=方式A(pdf_y*2) 蓝色=方式B((842-pdf_y)*2)", fill=(0,0,0), font=get_font(16))
draw.text((15, 40), "看哪个颜色的点在房间文字上 → 那个转换方式是对的", fill=(100,100,100), font=get_font(14))

out = img.convert("RGB")
out_path = os.path.join(OUT_DIR, "DIAGNOSTIC_B2.png")
out.save(out_path, quality=95)
print(f"\n✅ 诊断图: {out_path}")
doc.close()
