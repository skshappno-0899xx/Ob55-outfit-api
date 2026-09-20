from flask import Flask, request, jsonify, Response
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os

app = Flask(__name__)

API_KEY = "shappno"
BACKGROUND_FILENAME = "outfit.png"
CANVAS_SIZE = (1536, 1231)

def fetch_player_info(uid: str):
    try:
        url = f"http://info-ob55-shappnooo.vercel.app/shappno?uid={uid}"
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def fetch_image(url):
    try:
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content)).convert("RGBA")
        return None
    except:
        return None

def make_circular_image(img, target_diameter, border_color=(255, 215, 0, 255), border_width=5):
    inner_diameter = target_diameter - (border_width * 2)
    img = img.resize((inner_diameter, inner_diameter), Image.LANCZOS)
    mask = Image.new('L', (inner_diameter, inner_diameter), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, inner_diameter, inner_diameter), fill=255)
    circular_img = Image.new('RGBA', (inner_diameter, inner_diameter), (0, 0, 0, 0))
    circular_img.paste(img, (0, 0), mask)
    border = Image.new('RGBA', (target_diameter, target_diameter), (0, 0, 0, 0))
    draw = ImageDraw.Draw(border)
    draw.ellipse((0, 0, target_diameter-1, target_diameter-1), outline=border_color, width=border_width)
    final_img = Image.new('RGBA', (target_diameter, target_diameter), (0, 0, 0, 0))
    paste_offset = (target_diameter - inner_diameter) // 2
    final_img.paste(circular_img, (paste_offset, paste_offset))
    final_img = Image.alpha_composite(final_img, border)
    return final_img

@app.route('/shappno-outfit', methods=['GET'])
def outfit_image():
    uid = request.args.get('uid')
    key = request.args.get('key')

    if key != API_KEY:
        return jsonify({'error': 'Invalid API key'}), 401
    if not uid:
        return jsonify({'error': 'Missing uid'}), 400

    data = fetch_player_info(uid)
    if not data:
        return jsonify({'error': 'Player not found'}), 404

    # --- Extract IDs from API ---
    clothes = data.get("profileInfo", {}).get("clothes", [])
    weapon_skins = data.get("basicInfo", {}).get("weaponSkinShows", [])
    pet_skin_id = data.get("petInfo", {}).get("skinId", None)

    # Slot positions (SIZE বড় করা হয়েছে, এখন 270px)
    slot_positions = [
        # বাম দিকের (Outer)
        {"x": 185, "y": 190, "size": 270}, # 1
        {"x": 185, "y": 520, "size": 270}, # 2
        {"x": 185, "y": 845, "size": 270}, # 3
        
        # বাম দিকের (Inner)
        {"x": 390, "y": 355, "size": 270}, # 4
        {"x": 390, "y": 685, "size": 270}, # 5
        
        # ডান দিকের (Outer)
        {"x": 1351, "y": 190, "size": 270}, # 6
        {"x": 1351, "y": 520, "size": 270}, # 7
        {"x": 1351, "y": 845, "size": 270}, # 8
        
        # ডান দিকের (Inner)
        {"x": 1146, "y": 355, "size": 270}, # 9
        {"x": 1146, "y": 685, "size": 270}, # 10
    ]

    # --- Logic for each slot ---
    # 0-5 = clothes (যদি না থাকে সাদা)
    # 6-8 = ganskin (weaponSkinShows)
    # 9 = pet (petInfo.skinId)

    items_to_show = []

    # Slot 0-5: Clothes
    for i in range(6):
        if i < len(clothes):
            items_to_show.append(str(clothes[i]))
        else:
            items_to_show.append(None)  # white

    # Slot 6-8: Ganskin (weapon skin)
    for i in range(3):
        if i < len(weapon_skins):
            items_to_show.append(str(weapon_skins[i]))
        else:
            items_to_show.append(None)

    # Slot 9: Pet
    items_to_show.append(str(pet_skin_id) if pet_skin_id else None)

    # Load background
    bg_path = os.path.join(os.path.dirname(__file__), BACKGROUND_FILENAME)
    if not os.path.exists(bg_path):
        return jsonify({'error': 'Background image not found'}), 500
    
    bg = Image.open(bg_path).convert("RGBA")
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 255))
    canvas.paste(bg, (0, 0))

    # Draw items (only if not None)
    for i, slot in enumerate(slot_positions):
        item_id = items_to_show[i]
        if item_id is None:
            continue  # white background

        img = fetch_image(f"https://iconapi.wasmer.app/{item_id}")
        if img:
            diameter = int(slot["size"])
            circular_img = make_circular_image(img, diameter, border_color=(255, 215, 0, 200), border_width=5)
            paste_x = int(slot["x"] - (diameter / 2))
            paste_y = int(slot["y"] - (diameter / 2))
            canvas.paste(circular_img, (paste_x, paste_y), circular_img)

    # Nickname
    try:
        draw = ImageDraw.Draw(canvas)
        nickname = data.get("basicInfo", {}).get("nickname", "SHAPPN0 INF0")
        font = ImageFont.load_default()  # no arial needed
        text_bbox = draw.textbbox((0, 0), nickname, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (CANVAS_SIZE[0] - text_width) // 2
        text_y = 470
        draw.text((text_x+3, text_y+3), nickname, fill=(0,0,0,200), font=font)
        draw.text((text_x, text_y), nickname, fill=(255, 215, 0, 255), font=font)
    except:
        pass

    output = BytesIO()
    canvas.save(output, format='PNG', quality=95)
    output.seek(0)
    return Response(output.getvalue(), mimetype='image/png')

# Vercel / Production entry point
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5009, debug=True)