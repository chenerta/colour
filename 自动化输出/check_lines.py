# -*- coding: utf-8 -*-
"""
诊断：PDF里有多少种线条？粗细分布如何？
找出真正的墙体线条（粗线）vs 家具/标注线（细线）
"""
import fitz
import numpy as np

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
doc = fitz.open(pdf_path)
page = doc[3]

paths = page.get_drawings()

# 统计线条宽度
widths = []
lines_by_width = {}  # width -> [(x0,y0,x1,y1), ...]

for p in paths:
    w = p.get('width', 0)
    if w not in lines_by_width:
        lines_by_width[w] = []
    for item in p["items"]:
        if item[0] == "l":
            x0,y0 = item[1].x, item[1].y
            x1,y1 = item[2].x, item[2].y
            L = ((x1-x0)**2+(y1-y0)**2)**0.5
            widths.append((w, L))
            lines_by_width[w].append((x0,y0,x1,y1,L))

print("=== 线条宽度分布 ===")
width_counts = {}
for w, L in widths:
    if w not in width_counts:
        width_counts[w] = {'count': 0, 'total_len': 0, 'min_len': 9999, 'max_len': 0}
    width_counts[w]['count'] += 1
    width_counts[w]['total_len'] += L
    width_counts[w]['min_len'] = min(width_counts[w]['min_len'], L)
    width_counts[w]['max_len'] = max(width_counts[w]['max_len'], L)

for w in sorted(width_counts.keys()):
    info = width_counts[w]
    print(f"  宽度 {w:.2f}: {info['count']} 条, 总长 {info['total_len']:.0f}, 长度范围 {info['min_len']:.0f}-{info['max_len']:.0f}")

# 最常见的宽度
print("\n=== 按数量排序的宽度 ===")
sorted_widths = sorted(width_counts.items(), key=lambda x: -x[1]['count'])
for w, info in sorted_widths[:10]:
    print(f"  宽度 {w:.2f}: {info['count']} 条")

doc.close()
