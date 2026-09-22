# PDF Combine & Print

รวมหลายไฟล์ PDF จัดเรียงลงบนกระดาษ A4 (2, 4, 6 หรือ 8 หน้าต่อแผ่น) และสั่งพิมพ์ได้ทันที รองรับทั้ง **Windows** และ **Linux** (Cross-platform)

## Features

- **Cross-Platform**: รองรับการใช้งานทั้งบน Windows และ Linux
- **GUI Mode**: อินเทอร์เฟซ Tkinter ธีม Catppuccin Mocha พร้อมพรีวิวก่อนพิมพ์
- **CLI Mode**: ทำงานผ่าน Command Line สำหรับการทำงานอัตโนมัติ (Automation)
- **Auto-detects Printers**: ตรวจหาเครื่องพิมพ์เริ่มต้นอัตโนมัติ (Windows Print Spooler / Linux CUPS)
- **High Performance**: แปลงและจัดเรียงหน้า PDF ความละเอียดสูง (300 DPI) ด้วย **PyMuPDF**
- **Flexible Layouts**: จัดลงกระดาษ A4 ได้ทั้ง 2, 4, 6 หรือ 8 หน้าต่อแผ่น

---

## Requirements & Installation

### Windows (Native)

1. ติดตั้ง **Python 3.10+** (ติ๊กเลือก *Add python.exe to PATH*)
2. ติดตั้ง Python packages:
   ```cmd
   pip install reportlab PyPDF2 Pillow pymupdf
   ```
3. (ตัวเลือก) สร้างทางลัดบน Desktop:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\create_shortcut.ps1
   ```

### Linux (Ubuntu / Debian)

1. ติดตั้งแพ็กเกจระบบ:
   ```bash
   sudo apt install python3 python3-tk python3-pip cups-client
   ```
2. ติดตั้ง Python packages:
   ```bash
   pip install reportlab PyPDF2 Pillow pymupdf
   ```
3. (ตัวเลือก) ติดตั้ง Desktop Entry:
   ```bash
   cp pdf-combine-print.desktop ~/.local/share/applications/
   chmod +x ~/.local/share/applications/pdf-combine-print.desktop
   cp icons/pdf-combine-print.png ~/.local/share/icons/
   ```

---

## Usage

### GUI Mode (หน้าต่างโปรแกรม)
```bash
python combine_pdfs_gui.py
```
*(บน Windows สามารถเปิดผ่านทางลัด **PDF Combine & Print** บนหน้าจอ Desktop ได้เลย)*

### CLI Mode (Command Line)
```bash
# รวมไฟล์ PDF หลายไฟล์ (ค่าเริ่มต้น: 4 หน้าต่อแผ่น A4)
python combine_pdfs_cli.py -o output.pdf file1.pdf file2.pdf file3.pdf

# รวมแล้วสั่งพิมพ์ทันที
python combine_pdfs_cli.py -o output.pdf -p file1.pdf file2.pdf

# กำหนดจำนวนหน้าต่อแผ่น (เช่น 2 หน้าต่อแผ่น)
python combine_pdfs_cli.py -o output.pdf -n 2 file1.pdf file2.pdf

# ระบุชื่อเครื่องพิมพ์เอง
python combine_pdfs_cli.py -o output.pdf -p -d "Canon E510 series Printer" file1.pdf file2.pdf

# ค้นหาไฟล์ PDF ทั้งหมดใน Downloads แล้วรวมอัตโนมัติ
python combine_pdfs_cli.py
```

---

## Project Structure

```
pdf-combine-print/
├── README.md
├── LICENSE
├── combine_pdfs_gui.py      # GUI application (Tkinter)
├── combine_pdfs_cli.py      # CLI application
├── pdf_renderer.py          # PDF rendering engine (PyMuPDF / fallback pdftoppm)
├── printer_utils.py         # Cross-platform printer detection & printing
├── create_shortcut.ps1      # Windows desktop shortcut generator
├── pdf-combine-print.desktop# Linux desktop integration
├── icons/
│   ├── pdf-combine-print.png
│   ├── pdf-combine-print.ico
│   └── hicolor/             # Multiple icon sizes
└── screenshots/             # Application screenshots
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.
