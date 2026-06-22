# -*- coding: utf-8 -*-
"""第一步：读取PDF，提取页面信息和文字，渲染为图片"""
import fitz
import json
import os

PDF_PATH = r"C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf"
OUT_DIR  = r"C:\Users\apple\Desktop\湖滨壹号_自动化输出"
os.makedirs(OUT_DIR, exist_ok=True)

doc = fitz.open(PDF_PATH)
print(f"PDF页数: {doc.page_count}")

for i in range(doc.page_count):
    page = doc.load_page(i)
    rect = page.rect
    print(f"\n--- 第{i+1}页 ---")
    print(f"  尺寸: {rect.width:.0f} x {rect.height:.0f} pt")

    # 提取所有文字和位置
    text_instances = page.get_text("dict")["blocks"]
    all_texts = []
    for block in text_instances:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    txt = span["text"].strip()
                    if txt:
                        all_texts.append({
                            "text": txt,
                            "bbox": list(span["bbox"]),
                            "size": span["size"],
                            "font": span["font"]
                        })
    print(f"  文字块数: {len(all_texts)}")
    for t in all_texts[:30]:
        print(f"    [{t['bbox'][0]:.0f},{t['bbox'][1]:.0f},{t['bbox'][2]:.0f},{t['bbox'][3]:.0f}] {t['text']}")

    # 渲染为高清图片
    scale = 2.0  # 2倍分辨率
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    img_path = os.path.join(OUT_DIR, f"page_{i+1}.png")
    pix.save(img_path)
    print(f"  渲染图片: {img_path} ({pix.width}x{pix.height})")

    # 保存文字信息供后续使用
    info_path = os.path.join(OUT_DIR, f"page_{i+1}_texts.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(all_texts, f, ensure_ascii=False, indent=2)
    print(f"  文字信息: {info_path}")

doc.close()
print("\n✅ 第一步完成")
