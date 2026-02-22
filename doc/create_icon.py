from PIL import Image, ImageDraw
import os, subprocess, tempfile, shutil

# 3x5 pixel font for uppercase letters
FONT = {
    'A': ["010","101","111","101","101"],
    'B': ["110","101","110","101","110"],
    'C': ["011","100","100","100","011"],
    'D': ["110","101","101","101","110"],
    'E': ["111","100","110","100","111"],
    'F': ["111","100","110","100","100"],
    'G': ["011","100","101","101","011"],
    'H': ["101","101","111","101","101"],
    'I': ["111","010","010","010","111"],
    'J': ["001","001","001","101","010"],
    'K': ["101","101","110","101","101"],
    'L': ["100","100","100","100","111"],
    'M': ["10001","11011","10101","10001","10001"],
    'N': ["10001","11001","10101","10011","10001"],
    'O': ["010","101","101","101","010"],
    'P': ["110","101","110","100","100"],
    'Q': ["010","101","101","011","001"],
    'R': ["110","101","110","101","101"],
    'S': ["011","100","010","001","110"],
    'T': ["111","010","010","010","010"],
    'U': ["101","101","101","101","010"],
    'V': ["101","101","101","010","010"],
    'W': ["10001","10001","10101","10101","01010"],
    'X': ["101","101","010","101","101"],
    'Y': ["101","101","010","010","010"],
    'Z': ["111","001","010","100","111"],
}

def draw_text(img, text, start_x, start_y, color):
    """Draw pixel text. Returns width used."""
    x = start_x
    for ch in text:
        if ch == ' ':
            x += 2
            continue
        glyph = FONT.get(ch.upper())
        if not glyph:
            x += 4
            continue
        for row_i, row in enumerate(glyph):
            for col_i, bit in enumerate(row):
                if bit == '1':
                    px_x = x + col_i
                    px_y = start_y + row_i
                    if 0 <= px_x < img.width and 0 <= px_y < img.height:
                        img.putpixel((px_x, px_y), color)
        x += len(glyph[0]) + 1
    return x - start_x


def create_pixel_icon_base():
    """Create a 64x64 pixel art Claude Monitor icon."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Colors
    frame = (80, 80, 100, 255)
    frame_hi = (100, 100, 125, 255)
    screen_bg = (18, 20, 28, 255)
    claude_orange = (217, 119, 52, 255)
    claude_light = (240, 165, 100, 255)
    green = (80, 200, 120, 255)
    blue = (80, 140, 220, 255)
    white = (220, 220, 230, 255)
    dim = (120, 120, 140, 255)
    stand_col = (60, 60, 75, 255)

    def px(x, y, color):
        if 0 <= x < size and 0 <= y < size:
            img.putpixel((x, y), color)

    def px_rect(x, y, w, h, color):
        draw.rectangle([x, y, x+w-1, y+h-1], fill=color)

    # === Monitor frame ===
    px_rect(8, 5, 48, 2, frame_hi)    # top edge
    px_rect(6, 7, 2, 40, frame_hi)    # left edge
    px_rect(56, 7, 2, 40, frame_hi)   # right edge
    px_rect(8, 47, 48, 2, frame)      # bottom edge
    px_rect(8, 7, 48, 40, frame)      # fill

    # Screen area
    px_rect(10, 9, 44, 36, screen_bg)

    # === Claude sparkle (top-left) ===
    px_rect(13, 13, 3, 3, claude_orange)
    px(12, 14, claude_light)
    px(16, 14, claude_light)
    px(14, 11, claude_light)
    px(14, 16, claude_light)
    px(12, 12, claude_light)
    px(16, 12, claude_light)
    px(12, 16, claude_light)
    px(16, 16, claude_light)

    # === "CLAUDE" text ===
    draw_text(img, "CLAUDE", 19, 12, white)

    # === "MONITOR" text ===
    draw_text(img, "MONITOR", 12, 19, dim)

    # === Bar chart (usage visualization) ===
    bar_bottom = 43
    bar_x_start = 12
    bar_width = 3
    bar_gap = 2

    bars = [
        (14, claude_orange),
        (10, green),
        (17, blue),
        (7, claude_orange),
        (12, green),
        (19, claude_light),
        (9, blue),
        (15, claude_orange),
    ]

    x = bar_x_start
    for height, color in bars:
        px_rect(x, bar_bottom - height, bar_width, height, color)
        x += bar_width + bar_gap

    # Chart baseline
    px_rect(11, bar_bottom, 42, 1, dim)

    # === Monitor stand ===
    px_rect(26, 49, 12, 2, stand_col)
    px_rect(28, 51, 8, 2, stand_col)
    px_rect(22, 53, 20, 2, frame)
    px_rect(20, 55, 24, 2, frame_hi)

    return img


def create_icns(output_path):
    base = create_pixel_icon_base()

    iconset_dir = tempfile.mkdtemp(suffix='.iconset')

    entries = {
        'icon_16x16.png': 16,
        'icon_16x16@2x.png': 32,
        'icon_32x32.png': 32,
        'icon_32x32@2x.png': 64,
        'icon_128x128.png': 128,
        'icon_128x128@2x.png': 256,
        'icon_256x256.png': 256,
        'icon_256x256@2x.png': 512,
        'icon_512x512.png': 512,
        'icon_512x512@2x.png': 1024,
    }

    for name, s in entries.items():
        scaled = base.resize((s, s), Image.NEAREST)
        scaled.save(os.path.join(iconset_dir, name))

    subprocess.run(['iconutil', '-c', 'icns', iconset_dir, '-o', output_path], check=True)
    shutil.rmtree(iconset_dir)
    print(f"Created {output_path}")


if __name__ == '__main__':
    create_icns('/tmp/ClaudeMonitor.icns')
    # Also save preview
    img = create_pixel_icon_base()
    preview = img.resize((256, 256), Image.NEAREST)
    preview.save('/tmp/claude_monitor_preview.png')
    print("Preview saved")
