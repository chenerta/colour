"""
工序3v2：用PDF填充区域找墙体，反推房间边界
思路：墙体是填充的黑色矩形，房间是墙体之间的空白区域
"""
import fitz

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
doc = fitz.open(pdf_path)
page = doc[3]  # 1F

# --- 分析路径类型 ---
paths = page.get_drawings()
rects = []  # 填充矩形
lines = []  # 线段

for p in paths:
    fill = p.get('fill')
    color = p.get('color')
    for item in p["items"]:
        if item[0] == "re":  # 矩形
            r = item[1]
            rects.append({
                'x0': r.x0, 'y0': r.y0, 'x1': r.x1, 'y1': r.y1,
                'fill': fill, 'color': color,
                'w': r.width, 'h': r.height
            })
        elif item[0] == "l":  # 线段
            x0, y0 = item[1].x, item[1].y
            x1, y1 = item[2].x, item[2].y
            lines.append((x0, y0, x1, y1))

print(f"矩形数: {len(rects)}, 线段数: {len(lines)}")

# 分析矩形的尺寸分布
if rects:
    widths = [r['w'] for r in rects]
    heights = [r['h'] for r in rects]
    print(f"\n矩形宽度范围: {min(widths):.1f} ~ {max(widths):.1f}")
    print(f"矩形高度范围: {min(heights):.1f} ~ {max(heights):.1f}")
    
    # 找出墙体矩形（通常很细长：宽>高很多或高>宽很多）
    wall_rects = []
    for r in rects:
        w, h = r['w'], r['h']
        # 墙体特征：宽度很小（竖墙）或高度很小（横墙）
        if (w < 15 and h > 30) or (h < 15 and w > 30):
            wall_rects.append(r)
    
    print(f"\n可能的墙体矩形: {len(wall_rects)}")
    
    # 打印前20个墙体矩形
    for r in wall_rects[:20]:
        print(f"  ({r['x0']:.0f},{r['y0']:.0f})-({r['x1']:.0f},{r['y1']:.0f}) 尺寸={r['w']:.0f}x{r['h']:.0f} fill={r['fill']}")

# 也看看小矩形（可能是填充图案）
small_rects = [r for r in rects if r['w'] < 20 and r['h'] < 20]
print(f"\n小矩形(<20x20): {len(small_rects)}")
if small_rects:
    for r in small_rects[:10]:
        print(f"  ({r['x0']:.0f},{r['y0']:.0f}) 尺寸={r['w']:.0f}x{r['h']:.0f}")

doc.close()
