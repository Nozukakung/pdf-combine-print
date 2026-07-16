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
from PIL import Image, ImageTk

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

class PreviewWindow:
    """หน้าต่างพรีวิวก่อนปริ้น — แสดงทุกหน้าที่รวมแล้ว"""
    def __init__(self, parent, pdf_path, total_pages, sheets, printer_name, on_print_callback):
        self.pdf_path = pdf_path
        self.total_pages = total_pages
        self.sheets = sheets
        self.printer_name = printer_name
        self.on_print = on_print_callback
        self.images = []  # keep refs

        self.win = tk.Toplevel(parent)
        self.win.title(f"👁 พรีวิว — {total_pages} หน้า / {sheets} แผ่น A4")
        self.win.geometry("900x700")
        self.win.configure(bg="#1e1e2e")
        self.win.transient(parent)
        self.win.grab_set()

        self._build_ui()
        self._load_pages()

    def _build_ui(self):
        style = ttk.Style()
        style.configure("PreviewTitle.TLabel", font=("Segoe UI", 14, "bold"),
                        foreground="#cdd6f4", background="#1e1e2e")
        style.configure("PreviewInfo.TLabel", font=("Segoe UI", 10),
                        foreground="#a6adc8", background="#1e1e2e")
        style.configure("PreviewPrint.TButton", font=("Segoe UI", 12, "bold"),
                        foreground="#1e1e2e", background="#a6e3a1")
        style.configure("PreviewCancel.TButton", font=("Segoe UI", 10),
                        foreground="#f38ba8", background="#313244")

        # Header
        hdr = tk.Frame(self.win, bg="#1e1e2e")
        hdr.pack(fill="x", padx=15, pady=(10, 5))
        ttk.Label(hdr, text="👁 พรีวิวก่อนปริ้น",
                  style="PreviewTitle.TLabel").pack(side="left")
        ttk.Label(hdr, text=f"📄 {self.total_pages} หน้า / {self.sheets} แผ่น A4",
                  style="PreviewInfo.TLabel").pack(side="left", padx=15)

        # Scrollable canvas for pages
        container = tk.Frame(self.win, bg="#313244")
        container.pack(fill="both", expand=True, padx=15, pady=5)

        self.canvas = tk.Canvas(container, bg="#313244", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical",
                                        command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg="#313244")

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Mouse wheel scroll
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Button bar
        btn_frame = tk.Frame(self.win, bg="#1e1e2e")
        btn_frame.pack(fill="x", padx=15, pady=10)

        printer_txt = f" 🖨 พิมพ์ที่ {self.printer_name}" if self.printer_name else " ❌ ไม่พบเครื่องพิมพ์"
        ttk.Button(btn_frame, text=f"🖨 พิมพ์{printer_txt}",
                   style="PreviewPrint.TButton",
                   command=self._do_print).pack(side="right", padx=(8, 0))

        ttk.Button(btn_frame, text="💾 บันทึกอย่างเดียว",
                   style="PreviewPrint.TButton",
                   command=self._do_save).pack(side="right", padx=(8, 0))

        ttk.Button(btn_frame, text="✖ ปิด",
                   style="PreviewCancel.TButton",
                   command=self.win.destroy).pack(side="left")

    def _load_pages(self):
        """แปลง PDF เป็นรูปแล้วแสดงในหน้าต่าง"""
        temp_dir = tempfile.mkdtemp(prefix="preview_")
        try:
            subprocess.run([
                "pdftoppm", "-png", "-r", "200", self.pdf_path,
                os.path.join(temp_dir, "page")
            ], capture_output=True, check=True)

            pngs = sorted(glob.glob(os.path.join(temp_dir, "page-*.png")))
            max_w = 850  # max width in the scroll area

            for i, png_path in enumerate(pngs):
                # Page header
                hdr = tk.Frame(self.inner, bg="#45475a")
                hdr.pack(fill="x", padx=10, pady=(10 if i == 0 else 5, 2))
                tk.Label(hdr, text=f"  หน้าที่ {i+1}/{len(pngs)}",
                         fg="#cdd6f4", bg="#45475a",
                         font=("Segoe UI", 10, "bold")).pack(side="left")

                # Load image
                img = Image.open(png_path)
                w, h = img.size
                scale = min(max_w / w, 1.0)
                new_w, new_h = int(w * scale), int(h * scale)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.images.append(photo)  # prevent GC

                lbl = tk.Label(self.inner, image=photo, bg="#313244")
                lbl.pack(padx=10, pady=(0, 5))

            # Update scroll region
            self.inner.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _do_print(self):
        if not self.printer_name:
            messagebox.showerror("ไม่พบเครื่องพิมพ์",
                "ไม่พบเครื่องพิมพ์ในระบบ Linux\nกรุณาตรวจสอบการเชื่อมต่อ",
                parent=self.win)
            return
        self.on_print(self.pdf_path, self.printer_name)
        self.win.destroy()

    def _do_save(self):
        dest = filedialog.asksaveasfilename(
            title="บันทึกไฟล์ PDF",
            defaultextension=".pdf",
            initialfile="combined_output.pdf",
            initialdir="/home/jakkrit/Downloads",
            filetypes=[("PDF", "*.pdf")],
            parent=self.win)
        if dest:
            shutil.copy2(self.pdf_path, dest)
            messagebox.showinfo("บันทึกแล้ว", f"บันทึกไฟล์ที่:\n{dest}", parent=self.win)
            self.win.destroy()


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
        header = tk.Frame(self.root, bg="#1e1e2e")
        header.pack(fill="x", padx=20, pady=(15, 5))
        ttk.Label(header, text="📦 PDF Combine & Print",
                  style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="เลือกไฟล์ PDF หลายไฟล์ แล้วกดรวม + ปริ้น",
                  style="Sub.TLabel").pack(side="left", padx=15)

        # --- File list ---
        list_frame = tk.Frame(self.root, bg="#1e1e2e")
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
        btn_frame = tk.Frame(self.root, bg="#1e1e2e")
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

        self.print_btn = ttk.Button(btn_frame, text="👁 รวม + พรีวิว",
                                    style="Print.TButton",
                                    command=self.combine_and_preview)
        self.print_btn.pack(side="right")

        # --- Info bar ---
        printer_txt = f" ({PRINTER})" if PRINTER else ""
        base_txt = f"เลือกไฟล์ PDF → กดเพิ่ม → เรียงลำดับ → รวม/พรีวิว/ปริ้น\nเครื่องพิมพ์ที่พบ: {printer_txt}" if PRINTER else "เลือกไฟล์ PDF → กดเพิ่ม → เรียงลำดับ → รวม/พรีวิว/ปริ้น\n❌ ไม่พบเครื่องพิมพ์ ตรวจสอบการเชื่อมต่อ"
        self.info_var = tk.StringVar(value=base_txt)
        ttk.Label(self.root, textvariable=self.info_var,
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
        self._run_combine(out, show_preview=False)

    def combine_and_preview(self):
        """รวม PDF แล้วเปิดหน้าต่างพรีวิว"""
        if not self.files:
            messagebox.showwarning("ยังไม่มีไฟล์", "กรุณาเพิ่มไฟล์ PDF ก่อน")
            return
        out = os.path.join(tempfile.gettempdir(), "pdf_combine_preview.pdf")
        self._run_combine(out, show_preview=True)

    def _run_combine(self, output_pdf, show_preview=False):
        self.info_var.set("⏳ กำลังรวมไฟล์...")
        self.root.update_idletasks()
        threading.Thread(
            target=self._combine_worker,
            args=(output_pdf, show_preview),
            daemon=True
        ).start()

    def _combine_worker(self, output_pdf, show_preview):
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

                c.setStrokeColorRGB(0.85, 0.85, 0.85)
                c.setLineWidth(0.5)
                c.rect(area_x + 2, area_y + 2, HALF_W - 4, HALF_H - 4)

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

            if show_preview:
                # 3. Show preview window
                printer_name = self._get_printer_name()
                self.root.after(0, lambda: (
                    self.info_var.set(
                        f"✅ รวมเสร็จ! {total} หน้า / {sheets} แผ่น A4 — เปิดพรีวิว..."),
                    PreviewWindow(self.root, output_pdf, total, sheets,
                                  printer_name, self._print_file)
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

    def _print_file(self, pdf_path, printer_name):
        """สั่งปริ้นจริง"""
        self.info_var.set(f"🖨 สั่งปริ้นไปที่ {printer_name}...")
        self.root.update_idletasks()

        def _worker():
            try:
                result = subprocess.run(
                    ["lp", "-d", printer_name, pdf_path],
                    capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.root.after(0, lambda: (
                        self.info_var.set(f"✅ ปริ้นสำเร็จ! (พิมพ์ผ่าน {printer_name})"),
                        messagebox.showinfo("สำเร็จ!",
                            f"ส่งไฟล์ไปปริ้นที่ {printer_name} เรียบร้อย")
                    ))
                else:
                    self.root.after(0, lambda r=result.stderr: (
                        self.info_var.set(f"⚠️ ปริ้นไม่สำเร็จผ่าน {printer_name}"),
                        messagebox.showwarning("ปริ้นไม่สำเร็จ",
                            f"ล้มเหลว: {r}\n\nลองสั่งเอง: lp -d {printer_name} {pdf_path}")
                    ))
            except Exception as e:
                self.root.after(0, lambda: (
                    self.info_var.set(f"❌ ปริ้นไม่สำเร็จ: {e}"),
                    messagebox.showerror("ผิดพลาด", str(e))
                ))
        threading.Thread(target=_worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFCombineApp(root)
    root.mainloop()
