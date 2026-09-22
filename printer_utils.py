import os
import sys
import shutil
import subprocess
import json

def get_printers():
    """
    ตรวจหาเครื่องพิมพ์ทั้งหมดที่มีในระบบ
    รองรับทั้ง Native Windows (win32print / PowerShell) และ Linux (CUPS)
    คืนค่า (printers_list, default_printer)
    """
    printers = []
    default_printer = None

    # 1. Native Windows ผ่าน win32print (เร็ว แม่นยำที่สุด)
    try:
        import win32print
        raw_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        printers = [p[2] for p in raw_printers]
        try:
            default_printer = win32print.GetDefaultPrinter()
        except Exception:
            if printers:
                default_printer = printers[0]
        if printers:
            return printers, default_printer
    except Exception:
        pass

    # 2. Windows ผ่าน PowerShell (fallback สำหรับ WSL หรือกรณีไม่มี win32print)
    if sys.platform == "win32" or shutil.which("powershell.exe"):
        try:
            ps_bin = "powershell.exe" if shutil.which("powershell.exe") else "powershell"
            ps_script = "Get-CimInstance Win32_Printer | Select-Object Name, Default | ConvertTo-Json"
            res = subprocess.run(
                [ps_bin, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=6
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    name = item.get("Name")
                    if name:
                        printers.append(name)
                        if item.get("Default"):
                            default_printer = name
                if printers:
                    if not default_printer:
                        default_printer = printers[0]
                    return printers, default_printer
        except Exception:
            pass

    # 3. Native Linux ผ่าน CUPS
    if shutil.which("lpstat"):
        try:
            res = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.strip().split("\n"):
                    if line.startswith("printer "):
                        printers.append(line.split()[1])
            res_d = subprocess.run(["lpstat", "-d"], capture_output=True, text=True, timeout=5)
            if "system default destination:" in res_d.stdout:
                default_printer = res_d.stdout.split(":")[1].strip()
            elif printers:
                default_printer = printers[0]
        except Exception:
            pass

    return printers, default_printer


def _print_windows_gdi(pdf_path, printer_name):
    """
    พิมพ์บน Windows โดยตรงผ่าน Windows GDI (win32ui / win32print)
    คมชัดสูง ตรงตามขนาดหน้ากระดาษ A4 ไม่ติด Infinite Page Loop
    """
    import tempfile
    from PIL import Image, ImageWin
    import win32print
    import win32ui
    import win32con
    from pdf_renderer import pdf_to_pngs

    temp_dir = tempfile.mkdtemp(prefix="win_gdi_print_")
    try:
        # แปลงหน้า PDF เป็นภาพ 300 DPI
        png_list = pdf_to_pngs(pdf_path, temp_dir, prefix_name="page", dpi=300)
        if not png_list:
            return False, "ไม่สามารถอ่านและแปลงหน้า PDF ได้"

        hprinter = win32print.OpenPrinter(printer_name)
        try:
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            
            # ขนาดพื้นที่พิมพ์ของเครื่องพิมพ์
            printable_w = hdc.GetDeviceCaps(win32con.HORZRES)
            printable_h = hdc.GetDeviceCaps(win32con.VERTRES)

            hdc.StartDoc(os.path.basename(pdf_path))

            for png_file in png_list:
                hdc.StartPage()
                with Image.open(png_file) as img:
                    # ปรับ scale ภาพให้พอดีกับกระดาษ
                    iw, ih = img.size
                    scale = min(printable_w / iw, printable_h / ih)
                    dw = int(iw * scale)
                    dh = int(ih * scale)
                    x = (printable_w - dw) // 2
                    y = (printable_h - dh) // 2

                    dib = ImageWin.Dib(img)
                    dib.draw(hdc.GetHandleOutput(), (x, y, x + dw, y + dh))

                hdc.EndPage()

            hdc.EndDoc()
            hdc.DeleteDC()
            return True, "ส่งพิมพ์สำเร็จ"
        finally:
            win32print.ClosePrinter(hprinter)
    except Exception as e:
        return False, f"Windows GDI Print error: {e}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def send_to_printer(pdf_path, printer_name):
    """
    สั่งพิมพ์ไฟล์ PDF
    รองรับทั้ง Native Windows (GDI), WSL, และ CUPS (lp)
    """
    abs_pdf = os.path.abspath(pdf_path)

    # 1. ถ้าอยู่บน Windows แท้ๆ ให้ใช้ Windows GDI Printing (win32ui / win32print)
    if sys.platform == "win32":
        try:
            ok, msg = _print_windows_gdi(abs_pdf, printer_name)
            if ok:
                return True, msg
        except Exception as e:
            pass

        # Fallback 1: Adobe / Windows shell verb 'printto'
        try:
            import win32api
            win32api.ShellExecute(0, "printto", abs_pdf, f'"{printer_name}"', ".", 0)
            return True, "ส่งพิมพ์ผ่าน Windows Shell สำเร็จ"
        except Exception:
            pass

    # 2. ถ้าเป็น WSL -> สั่งพิมพ์ผ่าน PowerShell บน Windows
    if shutil.which("powershell.exe") and sys.platform != "win32":
        try:
            w_path = subprocess.run(
                ["wslpath", "-w", abs_pdf],
                capture_output=True, text=True, check=True
            ).stdout.strip()
        except Exception:
            w_path = abs_pdf

        escaped_pdf = w_path.replace("'", "''")
        escaped_printer = printer_name.replace("'", "''")
        fallback_script = f'''
        Start-Process -FilePath '{escaped_pdf}' -Verb PrintTo -ArgumentList '"{escaped_printer}"' -PassThru | Wait-Process -Timeout 15
        '''
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", fallback_script],
            capture_output=True, text=True, timeout=30
        )
        if res.returncode == 0:
            return True, "ส่งพิมพ์สำเร็จ"
        return False, res.stderr or "เกิดข้อผิดพลาดในการสั่งพิมพ์ผ่าน PowerShell"

    # 3. Native Linux CUPS
    if shutil.which("lp"):
        res = subprocess.run(["lp", "-d", printer_name, pdf_path], capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            return True, "ส่งพิมพ์สำเร็จ"
        return False, res.stderr or "คำสั่ง lp ล้มเหลว"

    return False, "ไม่พบคำสั่งสำหรับส่งพิมพ์ในระบบ"


if __name__ == "__main__":
    p_list, p_def = get_printers()
    print("Printers found:", p_list)
    print("Default printer:", p_def)
