# -*- coding: utf-8 -*-
"""单独测试B2层 —— 用vision最新给的坐标"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = r"C:\Users\apple\Desktop\湖滨壹号_自动化输出"

def get_font(size):
    for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                continue
    return ImageFont.load_default()

# B2层房间坐标（vision基于2382x1684给出）
B2_ROOMS = {
    "娱乐区":  {"bbox": (55, 230, 460, 720),   "type": "living"},
    "钢琴区":  {"bbox": (460, 230, 710, 420),   "type": "living"},
    "楼梯间":  {"bbox": (710, 230, 890, 420),   "type": "stairwell"},
    "卫生间":  {"bbox": (920, 230, 1140, 350),  "type": "bathroom"},
    "鞋帽间":  {"bbox": (1030, 460, 1170, 620), "type": "storage"},
    "客厅":    {"bbox": (710, 420, 1030, 720),  "type": "living"},
    "车库":    {"bbox": (1180, 230, 2320, 720), "type": "garage"},
}

# 空调规则
AC = {
    "living":    ("公共核心区", "风管机", "8.5kW", (66, 133, 244, 100)),
    "bathroom":  ("卫浴区", "卫浴空调", "1.5kW", (0, 188, 212, 110)),
    "stairwell": ("过渡区", "共享", "-", (158, 158, 158, 70)),
    "storage":   ("过渡区", "共享", "-", (139, 195, 74, 70)),
    "garage":    ("设备区", "不设空调", "-", (200, 200, 200, 60)),
}

# 加载底图
img = Image.open(os.path.join(OUT_DIR, "page_6.png")).convert("RGBA")
w, h = img.size
print(f"底图: {w}x{h}")

font_label = get_font(14)
font_small = get_font(11)
font_title = get_font(20)

# 叠加色块
for name, info in B2_ROOMS.items():
    bbox = info["bbox"]
    rule = AC[info["type"]]
    zone_name, equip, load, color = rule

    x0, y0, x1, y1 = bbox
    print(f"  {name}: ({x0},{y0},{x1},{y1}) → {zone_name}")

    # 填充
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle(bbox, fill=color)
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    draw.rectangle(bbox, outline=color[:3], width=2)

    # 房间名
    cx, cy = (x0+x1)/2, (y0+y1)/2
    bb = font_label.getbbox(name)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    lx = cx - tw/2 - 4
    ly = cy - th/2 - 12
    draw.rectangle([lx, ly, lx+tw+8, ly+th+4], fill=(255,255,255,230), outline=(80,80,80), width=1)
    draw.text((lx+4, ly+2), name, fill=(0,0,0), font=font_label)

    # 设备
    if equip and equip != "-":
        elabel = f"{equip} {load}" if load != "-" else equip
        eb = font_small.getbbox(elabel)
        ew, eh = eb[2]-eb[0], eb[3]-eb[1]
        ex, ey = cx-ew/2, ly+th+10
        draw.rectangle([ex-4, ey-2, ex+ew+4, ey+eh+2], fill=color[:3]+(220,))
        draw.text((ex, ey), elabel, fill=(255,255,255), font=font_small)

# 标题
result = img.convert("RGB")
draw = ImageDraw.Draw(result)
draw.rectangle([10, 8, 440, 42], fill=(30,30,30))
draw.text((15, 14), "空调系统分区示意图 - B2车库层", fill=(255,255,255), font=font_title)

# 保存
out_path = os.path.join(OUT_DIR, "空调示意图_B2_TEST.png")
result.save(out_path, quality=95)
print(f"\n✅ 已保存: {out_path}")
