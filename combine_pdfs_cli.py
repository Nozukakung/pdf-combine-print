#!/usr/bin/env python3
import os
import sys
import glob
import shutil
import subprocess
import tempfile
import argparse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader

A4_W, A4_H = A4
HALF_W = A4_W / 2
HALF_H = A4_H / 2
MARGIN = 8

def _detect_printer():
    try:
        result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if line.startswith("printer "):
                    return line.split()[1]
    except Exception:
        pass
    return None

def get_slots_positions(slots_per_page):
    """Calculate positions for different layouts (2, 4, 6, 8 pages per sheet)"""
    if slots_per_page == 2:
        # Top & bottom halves
        return [(0, HALF_H, A4_W, HALF_H), (0, 0, A4_W, HALF_H)]
    elif slots_per_page == 4:
        # 2x2 grid
        return [
            (0, HALF_H, HALF_W, HALF_H),
            (HALF_W, HALF_H, HALF_W, HALF_H),
            (0, 0, HALF_W, HALF_H),
            (HALF_W, 0, HALF_W, HALF_H),
        ]
    elif slots_per_page == 6:
        # 3 rows x 2 cols
        third_h = A4_H / 3
        return [
            (0, 2*third_h, HALF_W, third_h),
            (HALF_W, 2*third_h, HALF_W, third_h),
            (0, third_h, HALF_W, third_h),
            (HALF_W, third_h, HALF_W, third_h),
            (0, 0, HALF_W, third_h),
            (HALF_W, 0, HALF_W, third_h),
        ]
    elif slots_per_page == 8:
        # 4 rows x 2 cols
        quarter_h = A4_H / 4
        return [
            (0, 3*quarter_h, HALF_W, quarter_h),
            (HALF_W, 3*quarter_h, HALF_W, quarter_h),
            (0, 2*quarter_h, HALF_W, quarter_h),
            (HALF_W, 2*quarter_h, HALF_W, quarter_h),
            (0, quarter_h, HALF_W, quarter_h),
            (HALF_W, quarter_h, HALF_W, quarter_h),
            (0, 0, HALF_W, quarter_h),
            (HALF_W, 0, HALF_W, quarter_h),
        ]
    else:
        # Default: 4 pages
        return get_slots_positions(4)

def combine_pdfs(input_pdfs, output_pdf, slots_per_page=4, resolution=300, auto_print=False, printer_name=None):
    temp_dir = tempfile.mkdtemp(prefix="pdf_combine_")
    try:
        # 1. Convert all PDFs to PNG
        print(f"⌛ แปลง PDF เป็นรูปภาพ {resolution} DPI...")
        png_files = []
        for i, pdf_path in enumerate(input_pdfs):
            if not os.path.exists(pdf_path):
                print(f"⚠️ ไม่พบไฟล์: {pdf_path} (ข้าม)")
                continue
            prefix = os.path.join(temp_dir, f"pdf_{i:03d}")
            subprocess.run(["pdftoppm", "-png", "-r", str(resolution), pdf_path, prefix], capture_output=True, check=True)
            found = sorted(glob.glob(f"{prefix}-*.png"))
            png_files.extend(found)
            print(f"  ✅ {os.path.basename(pdf_path)} → {len(found)} หน้า")

        if not png_files:
            print("❌ ไม่มีหน้า PDF ที่แปลงสำเร็จ")
            return False

        total = len(png_files)
        sheets = -(-total // slots_per_page)  # ceiling division
        print(f"\n🎨 จัดเรียง {total} หน้า ลง A4 {sheets} แผ่น ({slots_per_page} หน้า/แผ่น)")

        # 2. Compose A4 sheets
        c = rl_canvas.Canvas(output_pdf, pagesize=A4)
        slots = get_slots_positions(slots_per_page)

        for idx, png_path in enumerate(png_files):
            slot_idx = idx % slots_per_page
            if idx > 0 and slot_idx == 0:
                c.showPage()

            area_x, area_y, area_w, area_h = slots[slot_idx]

            # Border
            c.setStrokeColorRGB(0.85, 0.85, 0.85)
            c.setLineWidth(0.5)
            c.rect(area_x + 2, area_y + 2, area_w - 4, area_h - 4)

            # Scale image to fit
            img = ImageReader(png_path)
            iw, ih = img.getSize()
            aw = area_w - 2 * MARGIN
            ah = area_h - 2 * MARGIN
            scale = min(aw / iw, ah / ih)
            dw, dh = iw * scale, ih * scale
            x = area_x + MARGIN + (aw - dw) / 2
            y = area_y + MARGIN + (ah - dh) / 2

            c.drawImage(png_path, x, y, width=dw, height=dh)

        c.save()
        size_kb = os.path.getsize(output_pdf) // 1024
        print(f"✅ บันทึก: {output_pdf} ({size_kb} KB)")

        # 3. Print
        if auto_print:
            if not printer_name:
                printer_name = _detect_printer()
            if not printer_name:
                print("❌ ไม่พบเครื่องพิมพ์ในระบบ")
                return False
            print(f"🖨 สั่งปริ้นไปที่ {printer_name}...")
            result = subprocess.run(["lp", "-d", printer_name, output_pdf], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"✅ ส่งไฟล์ไปปริ้นสำเร็จ!")
            else:
                print(f"❌ ปริ้นไม่สำเร็จ: {result.stderr}")

        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(
        description="📦 PDF Combine & Print — รวม PDF หลายไฟล์จัดลง A4 แล้วปริ้น")
    parser.add_argument("files", nargs="*", help="ไฟล์ PDF ที่ต้องการรวม (หลายไฟล์)")
    parser.add_argument("-o", "--output", default="combined_output.pdf", help="ชื่อไฟล์ปลายทาง (default: combined_output.pdf)")
    parser.add_argument("-p", "--print", action="store_true", help="สั่งปริ้นทันทีหลังรวม")
    parser.add_argument("-d", "--printer", default=None, help="ชื่อเครื่องพิมพ์ (auto-detect ถ้าไม่ใส่)")
    parser.add_argument("-r", "--resolution", type=int, default=300, help="ความละเอียด DPI (default: 300)")
    parser.add_argument("-n", "--pages", type=int, default=4, choices=[2,4,6,8], help="จำนวนหน้าต่อแผ่น A4 (default: 4)")

    args = parser.parse_args()

    # If no files specified, find all PDFs in Downloads
    if not args.files:
        downloads_dir = os.path.expanduser("~/Downloads")
        if os.path.exists(downloads_dir):
            all_pdfs = glob.glob(os.path.join(downloads_dir, "*.pdf"))
            # Exclude combined_output.pdf
            args.files = [p for p in all_pdfs if "combined" not in os.path.basename(p).lower()]
        if not args.files:
            print("❌ ไม่พบไฟล์ PDF ใน ~/Downloads")
            parser.print_help()
            sys.exit(1)
        print(f"💡 ไม่ได้ระบุไฟล์ → ดึงไฟล์ PDF ทั้งหมดจาก Downloads ({len(args.files)} ไฟล์)")

    print(f"📋 ไฟล์นำเข้า: {len(args.files)} ไฟล์")
    for f in args.files:
        print(f"   • {os.path.basename(f)}")
    print()

    ok = combine_pdfs(
        args.files, args.output,
        slots_per_page=args.pages,
        resolution=args.resolution,
        auto_print=args.print,
        printer_name=args.printer
    )
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
