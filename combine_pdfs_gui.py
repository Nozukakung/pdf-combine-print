#!/usr/bin/env python3
"""
📦 PDF Combine & Print — รวมหลาย PDF แล้วปริ้น 4 หน้า/แผ่น A4
GUI สำหรับลูกพี่ ใช้ Tkinter เลือกไฟล์แล้วกดปริ้นได้เลย
"""
import os
import sys
import glob
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader

A4_W, A4_H = A4
HALF_W = A4_W / 2
HALF_H = A4_H / 2
MARGIN = 8

def _detect_printer():
    """ตรวจหาเครื่องพิมพ์ที่ต่อกับเครื่องอัตโนมัติ"""
    try:
        result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if line.startswith("printer "):
                    return line.split()[1]
    except Exception:
        pass
    return None

PRINTER = _detect_printer()

class PDFCombineApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📦 PDF Combine & Print")
        self.root.geometry("750x600")
        self.root.configure(bg="#1e1e2e")

        self.files = []  # list of (path, page_count)

        self._build_ui()

    def _get_printer_name(self):
        """ตรวจหาชื่อเครื่องพิมพ์อัตโนมัติจากระบบ ถ้าไม่เจอให้ fallback ไป default"""
        if PRINTER:
            return PRINTER
        try:
            result = subprocess.run(["lpstat", "-d"], capture_output=True, text=True, timeout=5)
            if "system default destination:" in result.stdout:
                return result.stdout.split(":")[1].strip()
        except Exception:
            pass
        return None

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"),
                        foreground="#cdd6f4", background="#1e1e2e")
        style.configure("Sub.TLabel", font=("Segoe UI", 10),
                        foreground="#a6adc8", background="#1e1e2e")
        style.configure("Treeview", font=("Segoe UI", 10),
                        background="#313244", foreground="#cdd6f4",
                        fieldbackground="#313244", rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                        foreground="#cdd6f4", background="#45475a")
        style.configure("Add.TButton", font=("Segoe UI", 11, "bold"),
                        foreground="#1e1e2e", background="#a6e3a1")
        style.configure("Print.TButton", font=("Segoe UI", 12, "bold"),
                        foreground="#1e1e2e", background="#89b4fa")
        style.configure("Clear.TButton", font=("Segoe UI", 10),
                        foreground="#f38ba8", background="#313244")
        style.configure("Move.TButton", font=("Segoe UI", 9),
                        foreground="#cdd6f4", background="#45475a")
        style.configure("Status.TLabel", font=("Segoe UI", 9),
                        foreground="#a6adc8", background="#1e1e2e")

        # --- Header ---
        header = tk.Frame(root, bg="#1e1e2e")
        header.pack(fill="x", padx=20, pady=(15, 5))
        ttk.Label(header, text="📦 PDF Combine & Print",
                  style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="เลือกไฟล์ PDF หลายไฟล์ แล้วกดรวม + ปริ้น",
                  style="Sub.TLabel").pack(side="left", padx=15)

        # --- File list ---
        list_frame = tk.Frame(root, bg="#1e1e2e")
        list_frame.pack(fill="both", expand=True, padx=20, pady=5)

        cols = ("filename", "pages", "path")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                                 selectmode="extended")
        self.tree.heading("filename", text="📄 ชื่อไฟล์")
        self.tree.heading("pages", text="หน้า")
        self.tree.heading("path", text="ที่อยู่")
        self.tree.column("filename", width=250, minwidth=150)
        self.tree.column("pages", width=60, minwidth=40, anchor="center")
        self.tree.column("path", width=380, minwidth=200)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Button bar ---
        btn_frame = tk.Frame(root, bg="#1e1e2e")
        btn_frame.pack(fill="x", padx=20, pady=10)

        self.add_btn = ttk.Button(btn_frame, text="➕ เพิ่มไฟล์ PDF",
                                  style="Add.TButton", command=self.add_files)
        self.add_btn.pack(side="left", padx=(0, 8))

        self.remove_btn = ttk.Button(btn_frame, text="🗑 ลบไฟล์ที่เลือก",
                                     style="Clear.TButton",
                                     command=self.remove_selected)
        self.remove_btn.pack(side="left", padx=(0, 8))

        self.move_up_btn = ttk.Button(btn_frame, text="⬆",
                                      style="Move.TButton", command=self.move_up)
        self.move_up_btn.pack(side="left", padx=(0, 3))

        self.move_down_btn = ttk.Button(btn_frame, text="⬇",
                                        style="Move.TButton",
                                        command=self.move_down)
        self.move_down_btn.pack(side="left", padx=(0, 8))

        self.clear_btn = ttk.Button(btn_frame, text="ล้างทั้งหมด",
                                    style="Clear.TButton",
                                    command=self.clear_all)
        self.clear_btn.pack(side="left", padx=(0, 20))

        self.combine_btn = ttk.Button(btn_frame, text="📄 รวม PDF",
                                      style="Add.TButton",
                                      command=self.combine_only)
        self.combine_btn.pack(side="left", padx=(0, 8))

        self.print_btn = ttk.Button(btn_frame, text="🖨 รวม + ปริ้น",
                                    style="Print.TButton",
                                    command=self.combine_and_print)
        self.print_btn.pack(side="right")

        # --- Info bar ---
        printer_txt = f" ({PRINTER})" if PRINTER else ""
        base_txt = f"เลือกไฟล์ PDF ได้หลายไฟล์ → กดเพิ่ม → เรียงลำดับ → รวม/ปริ้น\nเครื่องพิมพ์ที่พบ: {printer_txt}" if PRINTER else "เลือกไฟล์ PDF ได้หลายไฟล์ → กดเพิ่ม → เรียงลำดับ → รวม/ปริ้น\n❌ ไม่พบเครื่องพิมพ์ ตรวจสอบการเชื่อมต่อ"
        self.info_var = tk.StringVar(value=base_txt)
        ttk.Label(root, textvariable=self.info_var,
                  style="Status.TLabel").pack(fill="x", padx=20, pady=(0, 15))

        self.total_pages = 0
        self._update_info()

    # --- File management ---
    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="เลือกไฟล์ PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        for p in paths:
            if any(f[0] == p for f in self.files):
                continue
            try:
                reader = PdfReader(p)
                count = len(reader.pages)
            except Exception:
                count = 0
            self.files.append((p, count))
            self.tree.insert("", "end", values=(
                os.path.basename(p), count, p))
        self._update_info()

    def remove_selected(self):
        selected = self.tree.selection()
        sel_paths = set(self.tree.item(s)["values"][2] for s in selected)
        for s in selected:
            self.tree.delete(s)
        self.files = [f for f in self.files if f[0] not in sel_paths]
        self._update_info()

    def move_up(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        idx = self.tree.index(item)
        if idx == 0:
            return
        vals = self.tree.item(item, "values")
        self.tree.delete(item)
        prev = self.tree.get_children()[idx - 1]
        self.tree.move(item, prev, "above")
        self.files[idx - 1], self.files[idx] = self.files[idx], self.files[idx - 1]
        self._update_info()

    def move_down(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        idx = self.tree.index(item)
        if idx >= len(self.files) - 1:
            return
        vals = self.tree.item(item, "values")
        self.tree.delete(item)
        nxt = self.tree.get_children()[idx + 1]
        self.tree.move(item, nxt, "below")
        self.files[idx + 1], self.files[idx] = self.files[idx], self.files[idx + 1]
        self._update_info()

    def clear_all(self):
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        self._update_info()

    def _update_info(self):
        total = sum(f[1] for f in self.files)
        sheets = (total + 3) // 4 if total > 0 else 0
        printer_txt = f" 🖨 {PRINTER}" if PRINTER else " ❌ ไม่พบเครื่องพิมพ์"
        self.info_var.set(
            f"📋 {len(self.files)} ไฟล์ / {total} หน้า / ใช้ A4 {sheets} แผ่น (4 หน้า/แผ่น){printer_txt}"
        )

    # --- Combine PDF ---
    def combine_only(self):
        if not self.files:
            messagebox.showwarning("ยังไม่มีไฟล์", "กรุณาเพิ่มไฟล์ PDF ก่อน")
            return
        out = filedialog.asksaveasfilename(
            title="บันทึกไฟล์ PDF ที่รวมแล้ว",
            defaultextension=".pdf",
            initialfile="combined_output.pdf",
            initialdir="/home/jakkrit/Downloads",
            filetypes=[("PDF", "*.pdf")])
        if not out:
            return
        self._run_combine(out, auto_print=False)

    def combine_and_print(self):
        if not self.files:
            messagebox.showwarning("ยังไม่มีไฟล์", "กรุณาเพิ่มไฟล์ PDF ก่อน")
            return
        out = "/home/jakkrit/Downloads/combined_output.pdf"
        self._run_combine(out, auto_print=True)

    def _run_combine(self, output_pdf, auto_print=False):
        self.info_var.set("⏳ กำลังรวมไฟล์...")
        self.root.update_idletasks()
        threading.Thread(
            target=self._combine_worker,
            args=(output_pdf, auto_print),
            daemon=True
        ).start()

    def _combine_worker(self, output_pdf, auto_print):
        temp_dir = tempfile.mkdtemp(prefix="pdf_combine_")
        try:
            # 1. Convert all PDFs to PNG
            self.root.after(0, lambda: self.info_var.set(
                "⏳ แปลง PDF เป็นรูปภาพ 300 DPI..."))
            png_files = []
            for i, (pdf_path, _) in enumerate(self.files):
                prefix = os.path.join(temp_dir, f"pdf_{i:03d}")
                subprocess.run([
                    "pdftoppm", "-png", "-r", "300", pdf_path, prefix
                ], capture_output=True, check=True)
                found = sorted(glob.glob(f"{prefix}-*.png"))
                png_files.extend(found)
                self.root.after(0, lambda p=os.path.basename(pdf_path), c=len(found):
                    self.info_var.set(f"  ✅ แปลง {p} → {c} หน้า"))

            if not png_files:
                self.root.after(0, lambda: messagebox.showerror(
                    "ผิดพลาด", "แปลง PDF ไม่สำเร็จ"))
                return

            total = len(png_files)
            sheets = (total + 3) // 4

            # 2. Compose A4 sheets
            self.root.after(0, lambda: self.info_var.set(
                f"🎨 กำลังจัดเรียง {total} หน้า ลง A4 {sheets} แผ่น..."))

            c = rl_canvas.Canvas(output_pdf, pagesize=A4)
            for idx, png_path in enumerate(png_files):
                grid_pos = idx % 4
                if idx > 0 and grid_pos == 0:
                    c.showPage()

                col = grid_pos % 2
                row = grid_pos // 2
                area_x = col * HALF_W
                area_y = HALF_H if row == 0 else 0

                # Light border
                c.setStrokeColorRGB(0.85, 0.85, 0.85)
                c.setLineWidth(0.5)
                c.rect(area_x + 2, area_y + 2, HALF_W - 4, HALF_H - 4)

                # Load & scale
                img = ImageReader(png_path)
                iw, ih = img.getSize()
                aw = HALF_W - 2 * MARGIN
                ah = HALF_H - 2 * MARGIN
                scale = min(aw / iw, ah / ih)
                dw, dh = iw * scale, ih * scale
                x = area_x + MARGIN + (aw - dw) / 2
                y = area_y + MARGIN + (ah - dh) / 2

                c.drawImage(png_path, x, y, width=dw, height=dh)

            c.save()

            # 3. Print
            printer_name = self._get_printer_name()
            if auto_print:
                if not printer_name:
                    self.root.after(0, lambda: (
                        self.info_var.set("⚠️ ไม่พบเครื่องพิมพ์ที่เปิดใช้งานในระบบ"),
                        messagebox.showerror("ไม่พบเครื่องพิมพ์", 
                            "ไม่พบเครื่องพิมพ์ใดๆ ในระบบปฏิบัติการ Linux ของคุณ\n"
                            "กรุณาตรวจสอบว่าเปิดเครื่องพิมพ์และเชื่อมต่ออยู่")
                    ))
                    return

                self.root.after(0, lambda: self.info_var.set(
                    f"🖨 สั่งปริ้นไปที่ {printer_name}..."))
                result = subprocess.run(
                    ["lp", "-d", printer_name, output_pdf],
                    capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.root.after(0, lambda: (
                        self.info_var.set(
                            f"✅ ปริ้นสำเร็จ! {total} หน้า / {sheets} แผ่น A4 (พิมพ์ผ่าน {printer_name})"),
                        messagebox.showinfo("สำเร็จ!",
                            f"ส่งไฟล์ไปปริ้นที่ {printer_name} เรียบร้อย\n"
                            f"📄 {total} หน้า จัดลง A4 {sheets} แผ่น\n"
                            f"💾 ไฟล์: {output_pdf}")
                    ))
                else:
                    self.root.after(0, lambda r=result.stderr: (
                        self.info_var.set(f"⚠️ ปริ้นไม่สำเร็จผ่าน {printer_name}"),
                        messagebox.showwarning("ปริ้นไม่สำเร็จ",
                            f"ล้มเหลว: {r}\n\n"
                            f"แต่ไฟล์รวมอยู่ที่:\n{output_pdf}\n\n"
                            f"ลองสั่งเอง: lp -d {printer_name} {output_pdf}")
                    ))
            else:
                self.root.after(0, lambda: (
                    self.info_var.set(
                        f"✅ รวมเสร็จ! {total} หน้า / {sheets} แผ่น A4 → {output_pdf}"),
                    messagebox.showinfo("สำเร็จ!",
                        f"รวม PDF เรียบร้อย\n"
                        f"📄 {total} หน้า จัดลง A4 {sheets} แผ่น\n"
                        f"💾 ไฟล์: {output_pdf}")
                ))
        except Exception as e:
            self.root.after(0, lambda err=str(e): (
                self.info_var.set(f"❌ เกิดข้อผิดพลาด: {err}"),
                messagebox.showerror("ผิดพลาด", f"เกิดข้อผิดพลาด:\n{err}")
            ))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFCombineApp(root)
    root.mainloop()
