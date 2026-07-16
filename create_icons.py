#!/usr/bin/env python3
"""Generate a custom app icon for the project"""
from PIL import Image, ImageDraw, ImageFont

def generate_icons(output_dir):
    size = 256
    img = Image.new("RGBA", (size, size), (30, 30, 46, 255))
    draw = ImageDraw.Draw(img)

    margin = 20
    draw.rounded_rectangle(
        [margin, margin, size-margin, size-margin],
        radius=40,
        fill=(49, 50, 68, 255),
        outline=(136, 180, 250, 255),
        width=4
    )

    # A4 paper
    paper_w, paper_h = 80, 113
    px = (size - paper_w) // 2
    py = 45
    draw.rounded_rectangle(
        [px, py, px+paper_w, py+paper_h],
        radius=6,
        fill=(220, 224, 244, 255),
        outline=(166, 227, 161, 255),
        width=3
    )

    # 4 quadrants
    mx, my = px + paper_w//2, py + paper_h//2
    draw.line([px+5, my, px+paper_w-5, my], fill=(243, 139, 168, 255), width=2)
    draw.line([mx, py+5, mx, py+paper_h-5], fill=(243, 139, 168, 255), width=2)

    # Small blue squares
    sq = 12
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        sx = mx + dx * (paper_w//4)
        sy = my + dy * (paper_h//4)
        draw.rectangle([sx-sq//2, sy-sq//2, sx+sq//2, sy+sq//2],
                       fill=(136, 180, 250, 255), outline=None)

    # Printer icon
    pr_w, pr_h = 60, 40
    pr_x = (size - pr_w) // 2
    pr_y = py + paper_h + 20
    draw.rounded_rectangle(
        [pr_x, pr_y, pr_x+pr_w, pr_y+pr_h],
        radius=5,
        fill=(245, 224, 220, 255),
        outline=(243, 139, 168, 255),
        width=2
    )
    draw.rectangle([pr_x+pr_w//2-8, pr_y-12, pr_x+pr_w//2+8, pr_y],
                   fill=(220, 224, 244, 255), outline=None)

    # Save main icon
    img.save(os.path.join(output_dir, "pdf-combine-print.png"))

    # Save multi-size icons
    for s in [16, 24, 32, 48, 64, 128, 256]:
        dir_path = os.path.join(output_dir, "hicolor", f"{s}x{s}", "apps")
        os.makedirs(dir_path, exist_ok=True)
        img.resize((s, s), Image.Resampling.LANCZOS).save(os.path.join(dir_path, "pdf-combine-print.png"))

    print(f"✅ สร้างไอคอนสำเร็จ: {output_dir}")

if __name__ == "__main__":
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_dir = os.path.join(base_dir, "icons")
    generate_icons(icon_dir)