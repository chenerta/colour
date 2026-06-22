# -*- coding: utf-8 -*-
"""
暖通示意图生成 v4 —— 基于PDF文字位置的可靠坐标
方法：
1. 用PyMuPDF提取PDF中的房间名文字位置（可靠的PDF坐标）
2. 用image_y = pdf_y * SCALE 转换到图片坐标（已验证正确）
3. 从文字中心向四周扩展，结合墙体线条确定房间边界
"""
import fitz
from PIL import Image, ImageDraw, ImageFont
import os

PDF_PATH = r"C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf"
OUT_DIR  = r"C:\Users\apple\Desktop\湖滨壹号_自动化输出"
SCALE = 2.0

# 房间名关键词（中文）
ROOM_KEYWORDS = [
    "客厅", "餐厅", "厨房", "卫生间", "卧室", "书房", "影音室",
    "品茶区", "娱乐区", "休闲区", "楼梯厅", "楼梯间", "衣帽间",
    "鞋帽间", "储藏间", "设备间", "阳台", "露台", "庭院", "花园",
    "车库", "酒柜", "手工区", "钢琴区", "走廊", "健身",
]

# 图框样板文字（过滤用）
BOILERPLATE = [
    "圖稱", "TITLE", "工程名稱", "PROJECT", "日期", "DATE",
    "編號", "JOB", "單位", "UNIT", "比例", "SCALE",
    "設計", "DESIGNED", "繪圖", "DRAWN", "核准", "APPROVED",
    "圖面修正", "REVISIONS", "圖號", "DRAWING", "頁數", "NUMBER",
    "版權所有", "請尊重智慧財產權", "凌傑內建築設計有限公司",
    "TEL:", "E-MAIL:", "ADD:", "浙江省", "云水山庄", "厘米", "A3",
]

# 英文→中文功能映射
ENG_MAP = {
    "BEDROOM": "卧室", "BATHROOM": "卫生间", "KITCHEN": "厨房",
    "CLOAKROOM": "衣帽间", "STAIRWELL": "楼梯厅", "STAIR": "楼梯间",
    "GARAGE": "车库", "GARDEN": "花园", "DRAWINGROOM": "客厅",
    "PLAY AREA": "娱乐区", "MOVEROOM": "影音室", "STORAGE": "储藏间",
    "BALCONY": "阳台", "STUDY": "书房", "LOUNGE": "休闲区",
    "RESTAURANT": "餐厅", "PATIO": "露台",
}

# 房间功能→暖通方案
AC_RULES = {
    "客厅":     ("公共核心区", "风管机", "8.5kW", (66, 133, 244, 100)),
    "休闲区":   ("公共核心区", "风管机", "8.5kW", (66, 133, 244, 100)),
    "餐厅":     ("公共核心区", "风管机", "6.5kW", (66, 133, 244, 100)),
    "品茶区":   ("公共核心区", "风管机", "5.0kW", (66, 133, 244, 95)),
    "娱乐区":   ("公共核心区", "风管机", "5.0kW", (66, 133, 244, 95)),
    "钢琴区":   ("公共核心区", "风管机", "3.5kW", (66, 133, 244, 90)),
    "厨房":     ("厨房专用区", "厨房空调", "3.5kW", (255, 152, 0, 100)),
    "卫生间":   ("卫浴区", "卫浴空调", "1.5kW", (0, 188, 212, 110)),
    "主卧":     ("私密休息区", "风管机", "5.0kW", (76, 175, 80, 100)),
    "卧室":     ("私密休息区", "分体挂机", "3.5kW", (76, 175, 80, 100)),
    "书房":     ("私密休息区", "分体挂机", "2.5kW", (76, 175, 80, 95)),
    "影音室":   ("专用区", "专用空调", "4.0kW", (156, 39, 176, 100)),
    "衣帽间":   ("过渡区", "与卧室共享", "-", (139, 195, 74, 70)),
    "鞋帽间":   ("过渡区", "与客厅共享", "-", (139, 195, 74, 70)),
    "楼梯厅":   ("过渡区", "共享", "-", (158, 158, 158, 70)),
    "楼梯间":   ("过渡区", "共享", "-", (158, 158, 158, 70)),
    "储藏间":   ("设备区", "不设空调", "-", (200, 200, 200, 60)),
    "设备间":   ("设备区", "不设空调", "-", (200, 200, 200, 60)),
    "庭院":     ("户外区", "不设空调", "-", (200, 200, 200, 50)),
    "花园":     ("户外区", "不设空调", "-", (200, 200, 200, 50)),
    "车库":     ("设备区", "不设空调", "-", (200, 200, 200, 60)),
    "酒柜":     ("过渡区", "-", "-", (180, 180, 180, 50)),
    "手工区":   ("公共核心区", "风管机", "3.5kW", (66, 133, 244, 90)),
    "走廊":     ("过渡区", "-", "-", (158, 158, 158, 50)),
    "阳台":     ("户外区", "不设空调", "-", (200, 200, 200, 40)),
    "露台":     ("户外区", "不设空调", "-", (200, 200, 200, 40)),
    "健身":     ("公共核心区", "风管机", "3.5kW", (66, 133, 244, 90)),
}

HEAT_RULES = {
    "客厅":     ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 90)),
    "休闲区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 90)),
    "餐厅":     ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 90)),
    "品茶区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 85)),
    "娱乐区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 85)),
    "钢琴区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 85)),
    "主卧":     ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 100)),
    "卧室":     ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 100)),
    "书房":     ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 90)),
    "影音室":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 85)),
    "卫生间":   ("电地暖-卫浴", "发热电缆", "100mm", (255, 87, 34, 110)),
    "楼梯厅":   ("水地暖-楼梯", "PE-RT管", "200mm", (121, 85, 72, 80)),
    "楼梯间":   ("水地暖-楼梯", "PE-RT管", "200mm", (121, 85, 72, 80)),
    "衣帽间":   ("水地暖-过渡区", "PE-RT管", "200mm", (142, 68, 173, 70)),
    "鞋帽间":   ("水地暖-过渡区", "PE-RT管", "200mm", (142, 68, 173, 70)),
    "厨房":     ("无地暖", "-", "-", (189, 189, 189, 60)),
    "储藏间":   ("无地暖", "-", "-", (189, 189, 189, 50)),
    "设备间":   ("无地暖", "-", "-", (189, 189, 189, 50)),
    "庭院":     ("无地暖", "-", "-", (189, 189, 189, 40)),
    "花园":     ("无地暖", "-", "-", (189, 189, 189, 40)),
    "车库":     ("无地暖", "-", "-", (189, 189, 189, 50)),
    "酒柜":     ("无地暖", "-", "-", (189, 189, 189, 40)),
    "手工区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 85)),
    "走廊":     ("水地暖-过渡区", "PE-RT管", "200mm", (142, 68, 173, 50)),
    "阳台":     ("无地暖", "-", "-", (189, 189, 189, 30)),
    "露台":     ("无地暖", "-", "-", (189, 189, 189, 30)),
    "健身":     ("无地暖", "-", "-", (189, 189, 189, 40)),
}

# ============================================================
# 工具函数
# ============================================================
def get_font(size):
    for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        if os.path.exists(fp):
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()

def is_boilerplate(text):
    return any(bp in text for bp in BOILERPLATE)

def match_room(text):
    """从文字中匹配房间功能类型"""
    for kw in ROOM_KEYWORDS:
        if kw in text:
            return kw
    text_upper = text.upper().strip()
    for eng, cn in ENG_MAP.items():
        if eng in text_upper:
            return cn
    return None

def find_walls(page):
    """提取PDF中的主要墙体线条（长直线）"""
    walls_h = []  # 水平墙: (x0, y, x1)
    walls_v = []  # 垂直墙: (y0, x, y1)
    for d in page.get_drawings():
        for item in d["items"]:
            if item[0] == "l":
                x0, y0, x1, y1 = item[1].x, item[1].y, item[2].x, item[2].y
                if abs(y0 - y1) < 2 and abs(x1 - x0) > 60:
                    walls_h.append((min(x0,x1), y0, max(x0,x1)))
                if abs(x0 - x1) < 2 and abs(y1 - y0) > 60:
                    walls_v.append((min(y0,y1), x0, max(y0,y1)))
    return walls_h, walls_v

def estimate_boundary(cx, cy, room_type, walls_h, walls_v, pw, ph):
    """从文字中心估算房间边界，用墙体收紧"""
    # 默认扩展（PDF坐标，单位pt）
    expand = {
        "客厅": 200, "休闲区": 180, "餐厅": 150, "厨房": 120,
        "卫生间": 100, "卧室": 160, "主卧": 180, "书房": 130,
        "影音室": 160, "娱乐区": 170, "品茶区": 140, "楼梯厅": 140,
        "楼梯间": 140, "衣帽间": 110, "鞋帽间": 90, "储藏间": 100,
        "设备间": 90, "庭院": 200, "花园": 200, "车库": 200,
        "酒柜": 60, "手工区": 130, "钢琴区": 110, "走廊": 100,
        "阳台": 120, "露台": 120, "健身": 120,
    }
    ex = expand.get(room_type, 140)
    
    left, right = cx - ex, cx + ex
    bottom, top = cy - ex * 0.8, cy + ex * 0.8
    
    # 用墙体收紧（在PDF坐标系中搜索）
    for wy, wx0, wx1 in walls_h:  # 水平墙
        if wx0 < cx < wx1 and abs(wy - cy) < ex * 1.2:
            if wy > cy and wy < top:
                top = wy
            elif wy < cy and wy > bottom:
                bottom = wy
    
    for wx, wy0, wy1 in walls_v:  # 垂直墙
        if wy0 < cy < wy1 and abs(wx - cx) < ex * 1.2:
            if wx > cx and wx < right:
                right = wx
            elif wx < cx and wx > left:
                left = wx
    
    # 确保最小尺寸
    if right - left < 60:
        left, right = cx - 40, cx + 40
    if top - bottom < 60:
        bottom, top = cy - 40, cy + 40
    
    return (left, bottom, right, top)

def pdf_to_img(bbox_pdf):
    """PDF坐标→图片坐标（已验证：不需要翻转y轴）"""
    x0, y0, x1, y1 = bbox_pdf
    return (x0 * SCALE, y0 * SCALE, x1 * SCALE, y1 * SCALE)

# ============================================================
# 绘图
# ============================================================
def draw_overlay(base_img, rooms, title, legend_items):
    canvas = base_img.copy().convert("RGBA")
    w, h = canvas.size
    font_title = get_font(20)
    font_label = get_font(14)
    font_small = get_font(11)
    
    for name, info in rooms.items():
        bbox_img = info["bbox_img"]
        rule = info["rule"]
        zone_name, equip, load, color = rule
        
        x0, y0, x1, y1 = bbox_img
        if x1 - x0 < 20 or y1 - y0 < 20:
            continue
        
        # 填充
        overlay = Image.new("RGBA", canvas.size, (0,0,0,0))
        ImageDraw.Draw(overlay).rectangle(bbox_img, fill=color)
        canvas = Image.alpha_composite(canvas, overlay)
        draw = ImageDraw.Draw(canvas)
        draw.rectangle(bbox_img, outline=color[:3], width=2)
        
        # 房间名
        cx, cy = (x0+x1)/2, (y0+y1)/2
        bb = font_label.getbbox(name)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        lx, ly = cx-tw/2-4, cy-th/2-12
        draw.rectangle([lx,ly,lx+tw+8,ly+th+4], fill=(255,255,255,230), outline=(80,80,80), width=1)
        draw.text((lx+4, ly+2), name, fill=(0,0,0), font=font_label)
        
        # 设备
        if equip and equip != "-":
            elabel = f"{equip} {load}" if load != "-" else equip
            eb = font_small.getbbox(elabel)
            ew, eh = eb[2]-eb[0], eb[3]-eb[1]
            ex, ey = cx-ew/2, ly+th+10
            if ex < x0+4: ex = x0+4
            if ey+eh > y1-4: ey = y1-eh-4
            draw.rectangle([ex-4,ey-2,ex+ew+4,ey+eh+2], fill=color[:3]+(220,))
            draw.text((ex, ey), elabel, fill=(255,255,255), font=font_small)
    
    result = canvas.convert("RGB")
    draw = ImageDraw.Draw(result)
    draw.rectangle([10,8,440,42], fill=(30,30,30))
    draw.text((15,14), title, fill=(255,255,255), font=font_title)
    
    lx, ly = w-300, 8
    lh = len(legend_items)*26+36
    draw.rectangle([lx,ly,w-8,ly+lh], fill=(255,255,255,230))
    draw.rectangle([lx,ly,w-8,ly+lh], outline=(100,100,100), width=1)
    draw.text((lx+8,ly+8), "图例:", fill=(0,0,0), font=font_label)
    for i,(n,c,d) in enumerate(legend_items):
        yy = ly+32+i*26
        draw.rectangle([lx+8,yy,lx+26,yy+18], fill=c+(220,))
        draw.rectangle([lx+8,yy,lx+26,yy+18], outline=(0,0,0), width=1)
        draw.text((lx+30,yy+1), f"{n}: {d}", fill=(0,0,0), font=font_small)
    
    return result

# ============================================================
# 主流程
# ============================================================
AC_LEGEND = [
    ("公共核心区", (66,133,244), "风管机 3.5-8.5kW"),
    ("私密休息区", (76,175,80), "分体/风管机 2.5-5kW"),
    ("厨房专用区", (255,152,0), "厨房空调 3.5kW"),
    ("卫浴区", (0,188,212), "卫浴空调 1.5kW"),
    ("专用区", (156,39,176), "专用空调 4kW"),
    ("过渡区", (158,158,158), "与相邻区域共享"),
    ("设备区", (200,200,200), "不设空调"),
]
HEAT_LEGEND = [
    ("水地暖-公共区", (103,58,183), "PE-RT管 200mm"),
    ("水地暖-休息区", (156,39,176), "PE-RT管 150mm"),
    ("水地暖-楼梯", (121,85,72), "PE-RT管 200mm"),
    ("水地暖-过渡区", (142,68,173), "PE-RT管 200mm"),
    ("电地暖-卫浴", (255,87,34), "发热电缆 100mm"),
    ("无地暖", (189,189,189), "不铺设"),
]

FLOOR_PLAN_KW = ["平面布置图", "平面图", "布置图"]

print("="*60)
print("暖通示意图生成 v4（PDF文字坐标 + 墙体线条）")
print("="*60)

doc = fitz.open(PDF_PATH)

for pi in range(doc.page_count):
    page = doc.load_page(pi)
    rect = page.rect
    pw, ph = rect.width, rect.height
    
    # 提取文字
    all_texts = []
    for block in page.get_text("dict")["blocks"]:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    txt = span["text"].strip()
                    if txt:
                        all_texts.append({"text": txt, "bbox": list(span["bbox"]), "font": span["font"]})
    
    # 判断是否为平面图
    full_text = " ".join(t["text"] for t in all_texts)
    if not any(kw in full_text for kw in FLOOR_PLAN_KW):
        print(f"\n第{pi+1}页: 跳过（非平面图）")
        continue
    
    # 提取房间名（只取中文标签，避免重复）
    rooms_raw = {}
    for t in all_texts:
        txt = t["text"]
        if is_boilerplate(txt):
            continue
        room_type = match_room(txt)
        if not room_type:
            continue
        font = t.get("font", "")
        is_cn = any(f in font for f in ["SimSun", "SimHei", "SimKai", "FangSong"])
        if is_cn and txt not in rooms_raw:
            rooms_raw[txt] = {"bbox_pdf": t["bbox"], "room_type": room_type}
    
    if not rooms_raw:
        print(f"\n第{pi+1}页: 跳过（无房间名）")
        continue
    
    # 提取墙体
    walls_h, walls_v = find_walls(page)
    
    # 获取页面标题
    page_title = ""
    for t in all_texts:
        if "平面" in t["text"] and "布置" in t["text"]:
            page_title = t["text"]
            break
    if not page_title:
        page_title = f"第{pi+1}页"
    
    print(f"\n{'='*50}")
    print(f"第{pi+1}页: {page_title}")
    print(f"  房间: {len(rooms_raw)}个, 墙体: H{len(walls_h)}+V{len(walls_v)}")
    
    # 为每个房间估算边界
    ac_rooms = {}
    heat_rooms = {}
    for name, info in rooms_raw.items():
        bbox = info["bbox_pdf"]
        cx = (bbox[0]+bbox[2])/2
        cy = (bbox[1]+bbox[3])/2
        room_type = info["room_type"]
        
        boundary_pdf = estimate_boundary(cx, cy, room_type, walls_h, walls_v, pw, ph)
        boundary_img = pdf_to_img(boundary_pdf)
        
        print(f"    {name}({room_type}): PDF({cx:.0f},{cy:.0f}) → 边界{boundary_img}")
        
        if room_type in AC_RULES:
            ac_rooms[name] = {"bbox_img": boundary_img, "rule": AC_RULES[room_type]}
        if room_type in HEAT_RULES:
            heat_rooms[name] = {"bbox_img": boundary_img, "rule": HEAT_RULES[room_type]}
    
    # 渲染底图
    mat = fitz.Matrix(SCALE, SCALE)
    pix = page.get_pixmap(matrix=mat)
    base_path = os.path.join(OUT_DIR, f"page_{pi+1}.png")
    pix.save(base_path)
    base_img = Image.open(base_path)
    
    # 生成空调图
    if ac_rooms:
        ac_img = draw_overlay(base_img, ac_rooms, f"空调系统分区 - {page_title}", AC_LEGEND)
        ac_path = os.path.join(OUT_DIR, f"AC_{pi+1}.png")
        ac_img.save(ac_path, quality=95)
        print(f"  ✅ 空调图: {ac_path}")
    
    # 生成地暖图
    if heat_rooms:
        heat_img = draw_overlay(base_img, heat_rooms, f"地暖系统分区 - {page_title}", HEAT_LEGEND)
        heat_path = os.path.join(OUT_DIR, f"HEAT_{pi+1}.png")
        heat_img.save(heat_path, quality=95)
        print(f"  ✅ 地暖图: {heat_path}")

doc.close()
print(f"\n{'='*60}")
print(f"✅ 完成！目录: {OUT_DIR}")
