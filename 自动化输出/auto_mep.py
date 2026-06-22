import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import os
import sys
import re

# --- Configuration ---
INPUT_PDF = r"C:\Users\apple\Desktop\成功\试验原图.pdf"
HVAC_OUTPUT_PNG = r"C:\Users\apple\Desktop\成功\空调新风示意图.png"
FLOOR_HEATING_PNG = r"C:\Users\apple\Desktop\成功\地暖示意图.png"

HVAC_COLOR_MAP = {
    "新风": (224, 246, 204),  # green
    "排风": (230, 215, 255),  # lavender
    "回风": (255, 240, 170),  # yellow
}
FLOOR_HEATING_COLOR = (255, 210, 210)  # pink/red tint

ROOM_SEVERITY = {
    "living room": ("新风", "hvac", 55),
    "lounge": ("新风", "hvac", 40),
    "kitchen": ("排风", "hvac", 40),
    "dining room": ("新风", "hvac", 35),
    "master bedroom": ("新风", "hvac", 40),
    "bedroom 1": ("新风", "hvac", 30),
    "bedroom 2": ("新风", "hvac", 30),
    "bedroom": ("新风", "hvac", 35),
    "bathroom": ("排风", "hvac", 30),
    "bath": ("排风", "hvac", 30),
    "shower": ("排风", "floor_heating", 30),
    "toilet": ("排风", "hvac", 20),
    "laundry": ("排风", "hvac", 25),
    "utility": ("排风", "hvac", 20),
    "storage": ("新风", "hvac", 20),
    "hallway": ("新风", "hvac", 15),
    "entryway": ("新风", "hvac", 15),
    "foyer": ("新风", "hvac", 15),
    "corridor": ("新风", "hvac", 15),
    "stair": ("新风", "hvac", 15),
    "staircase": ("新风", "hvac", 15),
}

def load_pdf_as_image(pdf_path, max_side=1600):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    rect = page.rect
    scale = max_side / max(rect.width, rect.height)
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img

def get_font(size=20):
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for font_path in candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def ocr_boxes(img):
    try:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except Exception:
        return []
    n = len(data["text"])
    results = []
    for i in range(n):
        txt = data["text"][i].strip()
        if txt and int(data["conf"][i]) > 40:
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            results.append({"text": txt, "x": x, "y": y, "w": w, "h": h})
    return results

def match_room_label(text):
    t = text.lower()
    for keyword in ROOM_SEVERITY:
        if keyword in t:
            return keyword
    return None

def bbox_contains_word(word_box, all_words):
    wx, wy = word_box["x"], word_box["y"]
    cx, cy = wx + word_box["w"] / 2, wy + word_box["h"] / 2
    for other in all_words:
        if other is word_box:
            continue
        ox, oy = other["x"], other["y"]
        if abs(ox + other["w"]/2 - cx) < 400 and abs(oy + other["h"]/2 - cy) < 400:
            return True
    return False

def group_room_boxes(matched_words):
    groups = []
    used = set()
    for i, w in enumerate(matched_words):
        if i in used:
            continue
        g = [w]
        used.add(i)
        for j, w2 in enumerate(matched_words):
            if j in used:
                continue
            if abs(w["x"] - w2["x"]) < 200 and abs(w["y"] - w2["y"]) < 200:
                g.append(w2)
                used.add(j)
        groups.append(g)
    return groups

def annotate(img, matched_rooms, mode):
    annotated = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = get_font(18)
    label_font = get_font(24)

    seen_labels = set()
    for room in matched_rooms:
        word = room["word"]
        room_type = room["room_type"]
        label = room_type.title()
        if label in seen_labels:
            continue
        seen_labels.add(label)

        # Match in severity map
        info = ROOM_SEVERITY.get(room_type)
        if info is None:
            continue
        cat, systems, load_w = info

        # Get bounding box from OCR word cluster
        group = room["group"]
        min_x = min(w["x"] for w in group)
        min_y = min(w["y"] for w in group)
        max_x = max(w["x"] + w["w"] for w in group)
        max_y = max(w["y"] + w["h"] for w in group)

        pad = 40
        fill_rect = [min_x - pad, min_y - pad, max_x + pad, max_y + pad]

        if mode == "hvac":
            color = HVAC_COLOR_MAP.get(cat, (200, 200, 200))
            draw.rectangle(fill_rect, fill=(*color, 100))
            draw.rectangle(fill_rect, outline=(0, 0, 0, 120), width=1)
            tag = f"{label} | {cat} | {load_w}W/m²"
        else:
            if "卫生间" in word or "bath" in word.lower() or "shower" in word.lower():
                draw.rectangle(fill_rect, fill=(*FLOOR_HEATING_COLOR, 120))
                draw.rectangle(fill_rect, outline=(180, 60, 60, 120), width=1)
                tag = f"{label} | 电地暖"
            else:
                draw.rectangle(fill_rect, fill=(*FLOOR_HEATING_COLOR, 90))
                draw.rectangle(fill_rect, outline=(0, 0, 0, 120), width=1)
                tag = f"{label} | 水地暖"

        tx = min_x - pad
        ty = max(min_y - pad - 28, 5)
        draw.text((tx, ty), tag, fill=(20, 20, 20, 255), font=label_font)

    annotated = Image.alpha_composite(annotated, overlay).convert("RGB")
    return annotated

def build_legend(size, mode):
    w, h = 300, size[1]
    legend = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(legend)
    font = get_font(20)
    title_font = get_font(24)

    y = 20
    if mode == "hvac":
        draw.text((20, y), "空调新风图例", fill=(0, 0, 0), font=title_font)
        y += 50
        for name, color in HVAC_COLOR_MAP.items():
            draw.rectangle([20, y, 60, y + 25], fill=color, outline=(0, 0, 0))
            draw.text((70, y), name, fill=(0, 0, 0), font=font)
            y += 40
        draw.text((20, y + 10), "说明：", fill=(0, 0, 0), font=title_font)
        y += 40
        lines = [
            "· 绿色 = 新风送风区域",
            "· 紫色 = 排风（厨房/卫生间）",
            "· 黄色 = 回风",
            "· 每区域标注负荷参考值",
        ]
        for line in lines:
            draw.text((20, y), line, fill=(0, 0, 0), font=font)
            y += 30
    else:
        draw.text((20, y), "地暖图例", fill=(0, 0, 0), font=title_font)
        y += 50
        draw.rectangle([20, y, 60, y + 25], fill=FLOOR_HEATING_COLOR, outline=(0, 0, 0))
        draw.text((70, y), "水地暖", fill=(0, 0, 0), font=font)
        y += 40
        draw.rectangle([20, y, 60, y + 25], fill=(255, 160, 160), outline=(180, 60, 60))
        draw.text((70, y), "电地暖（卫生间）", fill=(0, 0, 0), font=font)
        y += 40
        draw.text((20, y + 10), "说明：", fill=(0, 0, 0), font=title_font)
        y += 40
        lines = [
            "· 粉色区域 = 水地暖铺设",
            "· 红色区域 = 电地暖（淋浴区）",
            "· 门槛处设过门弯",
        ]
        for line in lines:
            draw.text((20, y), line, fill=(0, 0, 0), font=font)
            y += 30

    return legend

def side_by_side(img, legend):
    total_w = img.width + legend.width
    canvas = Image.new("RGB", (total_w, max(img.height, legend.height)), (255, 255, 255))
    canvas.paste(img, (0, 0))
    canvas.paste(legend, (img.width, 0))
    return canvas

def main():
    print("正在加载 PDF 图纸...")
    img = load_pdf_as_image(INPUT_PDF, max_side=1600)
    print(f"图纸尺寸: {img.size}")

    print("正在 OCR 识别文字...")
    words = ocr_boxes(img)
    print(f"识别到 {len(words)} 个文字区域")

    matched = []
    seen_types = set()
    for w in words:
        rt = match_room_label(w["text"])
        if rt and rt not in seen_types:
            seen_types.add(rt)
            group = [w]
            for w2 in words:
                if w2 is not w and match_room_label(w2["text"]) == rt:
                    if abs(w2["x"] - w["x"]) < 300 and abs(w2["y"] - w["y"]) < 300:
                        group.append(w2)
            matched.append({"word": w["text"], "room_type": rt, "group": group})

    print(f"匹配到 {len(matched)} 个房间标签:")
    for m in matched:
        print(f"  - {m['word']} -> {m['room_type']}")

    if not matched:
        print("\n⚠️ 未能自动识别房间标签，将使用示例布局生成示意图...")
        # Fallback: use grid-based demo layout
        matched_hvac = [
            {"word": "Living Room", "room_type": "living room", "group": [{"x": img.width//3, "y": img.height//2, "w": 1, "h": 1}]},
            {"word": "Master Bedroom", "room_type": "master bedroom", "group": [{"x": 2*img.width//3, "y": img.height//3, "w": 1, "h": 1}]},
            {"word": "Bedroom 1", "room_type": "bedroom 1", "group": [{"x": img.width//2, "y": 2*img.height//3, "w": 1, "h": 1}]},
            {"word": "Bedroom 2", "room_type": "bedroom 2", "group": [{"x": 2*img.width//3, "y": 2*img.height//3, "w": 1, "h": 1}]},
            {"word": "Kitchen", "room_type": "kitchen", "group": [{"x": img.width//4, "y": img.height//3, "w": 1, "h": 1}]},
            {"word": "Dining", "room_type": "dining room", "group": [{"x": img.width//4, "y": img.height//2, "w": 1, "h": 1}]},
            {"word": "Bathroom", "room_type": "bathroom", "group": [{"x": img.width//2, "y": img.height//3, "w": 1, "h": 1}]},
            {"word": "Hallway", "room_type": "hallway", "group": [{"x": img.width//2, "y": img.height//6, "w": 1, "h": 1}]},
        ]
        matched_floor = matched_hvac + [
            {"word": "Shower", "room_type": "shower", "group": [{"x": img.width//3, "y": 2*img.height//3, "w": 1, "h": 1}]}
        ]
    else:
        matched_hvac = matched
        matched_floor = matched + [{"word": "淋浴区", "room_type": "shower", "group": matched[-1]["group"]}]

    print("\n生成空调新风示意图...")
    hvac_img = annotate(img, matched_hvac, "hvac")
    hvac_legend = build_legend(hvac_img.size, "hvac")
    hvac_final = side_by_side(hvac_img, hvac_legend)
    hvac_final.save(HVAC_OUTPUT_PNG, quality=95)
    print(f"✓ 已保存: {HVAC_OUTPUT_PNG}")

    print("生成地暖示意图...")
    floor_img = annotate(img, matched_floor, "floor_heating")
    floor_legend = build_legend(floor_img.size, "floor_heating")
    floor_final = side_by_side(floor_img, floor_legend)
    floor_final.save(FLOOR_HEATING_PNG, quality=95)
    print(f"✓ 已保存: {FLOOR_HEATING_PNG}")

    print("\n✅ 完成！")

if __name__ == "__main__":
    main()
