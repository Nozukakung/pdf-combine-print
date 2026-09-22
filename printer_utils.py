import os
import sys
import shutil
import subprocess
import json

def get_printers():
    """
    ตรวจหาเครื่องพิมพ์ทั้งหมดที่มีในระบบ
    รองรับทั้ง Native Linux (CUPS) และ WSL -> Windows Printers
    คืนค่า (printers_list, default_printer)
    """
    printers = []
    default_printer = None

    # 1. ลองดึงจาก Windows ผ่าน PowerShell ถ้าอยู่ใน WSL หรือ Windows
    if shutil.which("powershell.exe"):
        try:
            ps_script = "Get-CimInstance Win32_Printer | Select-Object Name, Default | ConvertTo-Json"
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
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

    # 2. ถ้าไม่ใช่ WSL หรือดึงจาก Windows ไม่ได้ ให้ตรวจหาผ่าน CUPS (Linux เดิม)
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
    รองรับทั้ง Windows Printers (ผ่าน Ghostscript/PowerShell ใน WSL) และ CUPS (lp)
    """
    # ตรวจสอบว่าเป็น WSL / Windows หรือไม่
    if shutil.which("powershell.exe"):
        # แปลง path จาก /mnt/c/... เป็น C:\...
        try:
            w_path = subprocess.run(
                ["wslpath", "-w", os.path.abspath(pdf_path)],
                capture_output=True, text=True, check=True
            ).stdout.strip()
        except Exception:
            w_path = os.path.abspath(pdf_path)

        # วิธีที่ 1: ถ้ามี Ghostscript ให้แปลง PDF เป็นรูปชั่วคราวแล้วพิมพ์ผ่าน .NET PrintDocument
        # เพื่อความคมชัดสูงและตรงตามขนาด A4
        if shutil.which("gs"):
            import tempfile
            import glob
            temp_dir = tempfile.mkdtemp(prefix="win_print_")
            try:
                img_pattern = os.path.join(temp_dir, "page_%03d.png")
                gs_res = subprocess.run([
                    "gs", "-dNOPAUSE", "-dBATCH", "-sDEVICE=png16m",
                    "-r300", f"-sOutputFile={img_pattern}", pdf_path
                ], capture_output=True, text=True, timeout=60)

                # ดึง path ของภาพฝั่ง Windows
                w_temp_dir = subprocess.run(
                    ["wslpath", "-w", temp_dir],
                    capture_output=True, text=True, check=True
                ).stdout.strip()

                ps_print_script = f'''
                Add-Type -AssemblyName System.Drawing
                $doc = New-Object System.Drawing.Printing.PrintDocument
                $doc.PrinterSettings.PrinterName = "{printer_name}"
                $doc.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)
                
                $files = Get-ChildItem -Path "{w_temp_dir}" -Filter "page_*.png" | Sort-Object Name
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
                ps_res = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_print_script],
                    capture_output=True, text=True, timeout=60
                )
                if ps_res.returncode == 0:
                    return True, "ส่งพิมพ์สำเร็จ"
                else:
                    return False, ps_res.stderr or "เกิดข้อผิดพลาดในการส่งพิมพ์ผ่าน PowerShell"
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        # วิธีที่ 2: สำรอง ถ้าไม่มี gs ให้ใช้คำสั่ง Start-Process PrintTo บน Windows
        escaped_pdf = w_path.replace("'", "''")
        escaped_printer = printer_name.replace("'", "''")
        fallback_script = f'''
        Start-Process -FilePath '{escaped_pdf}' -Verb PrintTo -ArgumentList '"{escaped_printer}"' -PassThru | Wait-Process -Timeout 10
        '''
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", fallback_script],
            capture_output=True, text=True, timeout=30
        )
        if res.returncode == 0:
            return True, "ส่งพิมพ์สำเร็จ"
        return False, res.stderr or "เกิดข้อผิดพลาดในการสั่งพิมพ์"

    # สำหรับ Native Linux
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
