import os
import sys
import shutil
import subprocess
import json

def get_printers():
    """
    ตรวจหาเครื่องพิมพ์ทั้งหมดที่มีในระบบ
    รองรับทั้ง Native Windows, WSL -> Windows Printers, และ Native Linux (CUPS)
    คืนค่า (printers_list, default_printer)
    """
    printers = []
    default_printer = None

    # 1. รันบน Windows ตรงๆ หรือผ่าน PowerShell
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

    # 2. Native Linux ผ่าน CUPS
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


def send_to_printer(pdf_path, printer_name):
    """
    สั่งพิมพ์ไฟล์ PDF
    รองรับทั้ง Native Windows (.NET PrintDocument), WSL, และ CUPS (lp)
    """
    # 1. Native Windows หรือ WSL
    if sys.platform == "win32" or shutil.which("powershell.exe"):
        abs_pdf = os.path.abspath(pdf_path)
        if sys.platform != "win32":
            # WSL path -> Windows path
            try:
                w_path = subprocess.run(
                    ["wslpath", "-w", abs_pdf],
                    capture_output=True, text=True, check=True
                ).stdout.strip()
            except Exception:
                w_path = abs_pdf
        else:
            w_path = abs_pdf

        # สั่งพิมพ์โดยตรงผ่าน PowerShell .NET โดยแปลงหน้าด้วย pdf_renderer
        import tempfile
        from pdf_renderer import pdf_to_pngs

        temp_dir = tempfile.mkdtemp(prefix="win_print_")
        try:
            png_list = pdf_to_pngs(abs_pdf, temp_dir, prefix_name="print_page", dpi=300)
            if png_list:
                if sys.platform != "win32":
                    w_temp_dir = subprocess.run(
                        ["wslpath", "-w", temp_dir],
                        capture_output=True, text=True, check=True
                    ).stdout.strip()
                else:
                    w_temp_dir = temp_dir

                ps_print_script = f'''
                Add-Type -AssemblyName System.Drawing
                $doc = New-Object System.Drawing.Printing.PrintDocument
                $doc.PrinterSettings.PrinterName = "{printer_name}"
                $doc.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)
                
                $files = Get-ChildItem -Path "{w_temp_dir}" -Filter "print_page-*.png" | Sort-Object Name
                $i = 0

                $doc.add_PrintPage({{
                    param($sender, $e)
                    if ($i -lt $files.Count) {{
                        $img = [System.Drawing.Image]::FromFile($files[$i].FullName)
                        $e.Graphics.DrawImage($img, $e.PageBounds)
                        $img.Dispose()
                        $i++
                        $e.HasMorePages = ($i -lt $files.Count)
                    }} else {{
                        $e.HasMorePages = $false
                    }}
                }})

                $doc.Print()
                '''
                ps_bin = "powershell.exe" if shutil.which("powershell.exe") else "powershell"
                ps_res = subprocess.run(
                    [ps_bin, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_print_script],
                    capture_output=True, text=True, timeout=60
                )
                if ps_res.returncode == 0:
                    return True, "ส่งพิมพ์สำเร็จ"
                else:
                    return False, ps_res.stderr or "เกิดข้อผิดพลาดในการส่งพิมพ์ผ่าน Windows Print"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        # Fallback ถ้าแปลงภาพไม่ได้ ให้ใช้ PrintTo
        escaped_pdf = w_path.replace("'", "''")
        escaped_printer = printer_name.replace("'", "''")
        fallback_script = f'''
        Start-Process -FilePath '{escaped_pdf}' -Verb PrintTo -ArgumentList '"{escaped_printer}"' -PassThru | Wait-Process -Timeout 10
        '''
        ps_bin = "powershell.exe" if shutil.which("powershell.exe") else "powershell"
        res = subprocess.run(
            [ps_bin, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", fallback_script],
            capture_output=True, text=True, timeout=30
        )
        if res.returncode == 0:
            return True, "ส่งพิมพ์สำเร็จ"
        return False, res.stderr or "เกิดข้อผิดพลาดในการสั่งพิมพ์"

    # 2. Native Linux CUPS
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
