#!/usr/bin/env python3
"""
tile_contact_sheets.py
----------------------
Compone las 5 vistas de cada modular en una sola hoja de contacto con PIL.
"""

import os
import glob
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.expanduser("~/blender/buildings/renders/contact_sheets")
folders = sorted([d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d)) and d.startswith("10")])

for folder in folders:
    fdir = os.path.join(BASE_DIR, folder)
    v_south = os.path.join(fdir, "view_south.png")
    v_north = os.path.join(fdir, "view_north.png")
    v_west = os.path.join(fdir, "view_west.png")
    v_east = os.path.join(fdir, "view_east.png")
    v_top = os.path.join(fdir, "view_top.png")
    
    if not all(os.path.exists(p) for p in [v_south, v_north, v_west, v_east, v_top]):
        continue
        
    img_south = Image.open(v_south).convert("RGB")
    img_north = Image.open(v_north).convert("RGB")
    img_west = Image.open(v_west).convert("RGB")
    img_east = Image.open(v_east).convert("RGB")
    img_top = Image.open(v_top).convert("RGB")
    
    tile_w, tile_h = 512, 512
    sheet = Image.new("RGB", (tile_w * 3, tile_h * 2), (30, 30, 30))
    
    # Row 1: South (Front -Y), North (Back +Y), Top (+Z)
    sheet.paste(img_south, (0, 0))
    sheet.paste(img_north, (tile_w, 0))
    sheet.paste(img_top, (tile_w * 2, 0))
    
    # Row 2: West (-X), East (+X), Label card
    sheet.paste(img_west, (0, tile_h))
    sheet.paste(img_east, (tile_w, tile_h))
    
    draw = ImageDraw.Draw(sheet)
    # Add text labels on each quadrant
    labels = [
        ("SUR (-Y) [Frente]", 10, 10),
        ("NORTE (+Y) [Fondo]", tile_w + 10, 10),
        ("PLANTA (+Z)", tile_w * 2 + 10, 10),
        ("OESTE (-X) [Izquierda]", 10, tile_h + 10),
        ("ESTE (+X) [Derecha]", tile_w + 10, tile_h + 10),
    ]
    for text, lx, ly in labels:
        draw.rectangle([lx - 2, ly - 2, lx + 200, ly + 22], fill=(0, 0, 0, 180))
        draw.text((lx + 4, ly + 2), text, fill=(255, 255, 255))
        
    # Card in bottom right
    card_x, card_y = tile_w * 2, tile_h
    draw.rectangle([card_x, card_y, card_x + tile_w, card_y + tile_h], fill=(45, 45, 45))
    draw.text((card_x + 30, card_y + 40), f"LEGO {folder}", fill=(255, 220, 50))
    draw.text((card_x + 30, card_y + 80), f"Hoja de contacto", fill=(200, 200, 200))
    draw.text((card_x + 30, card_y + 120), "Vistas: Sur, Norte, Planta", fill=(180, 180, 180))
    draw.text((card_x + 30, card_y + 150), "Oeste, Este", fill=(180, 180, 180))
    
    out_path = os.path.join(BASE_DIR, f"{folder}_contact_sheet.png")
    sheet.save(out_path, "PNG")
    print(f"Saved {out_path}")
print("Contact sheets tiled successfully.")
