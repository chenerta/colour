# -*- coding: utf-8 -*-
"""检查每张渲染图的实际像素尺寸"""
from PIL import Image
import os

OUT_DIR = r"C:\Users\apple\Desktop\湖滨壹号_自动化输出"
for i in range(1, 7):
    p = os.path.join(OUT_DIR, f"page_{i}.png")
    if os.path.exists(p):
        img = Image.open(p)
        print(f"page_{i}.png: {img.size[0]}x{img.size[1]}")
