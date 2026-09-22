import os
import glob
import shutil
import subprocess

def pdf_to_pngs(pdf_path, output_dir, prefix_name="page", dpi=300):
    """
    แปลงทุกหน้าของ PDF เป็นไฟล์ภาพ PNG
    1. ลองใช้ PyMuPDF (เร็วมากและ Cross-platform 100% ไม่ต้องติดตั้งโปรแกรมภายนอก)
    2. Fallback ไปใช้ pdftoppm (ถ้ามีในระบบ Linux / poppler)
    คืนค่า list ของ path รูปภาพ PNG ที่เรียงลำดับแล้ว
    """
    png_files = []
    
    # วิธีที่ 1: PyMuPDF (Pure Python / Native C binding, ไม่ต้องพึ่งพา poppler-utils)
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=dpi)
            out_file = os.path.join(output_dir, f"{prefix_name}-{page_num+1:03d}.png")
            pix.save(out_file)
            png_files.append(out_file)
        doc.close()
        if png_files:
            return sorted(png_files)
    except Exception:
        pass

    # วิธีที่ 2: pdftoppm (Linux poppler-utils)
    if shutil.which("pdftoppm"):
        try:
            prefix = os.path.join(output_dir, prefix_name)
            subprocess.run([
                "pdftoppm", "-png", "-r", str(dpi), pdf_path, prefix
            ], capture_output=True, check=True)
            found = sorted(glob.glob(f"{prefix}-*.png"))
            if found:
                return found
        except Exception:
            pass

    return []
