# PDF Combine & Print

 combines multiple PDF files onto A4 sheets (2-up or 4-up) and prints them.

## Features

- **GUI Mode**: Tkinter interface with drag-and-drop ordering
- **CLI Mode**: Command-line interface for automation
- **Auto-detects printers** via `lpstat`
- **Supports multiple PDFs** with arbitrary page counts
- **High-resolution output** (300 DPI default)
- **Flexible layouts**: 2, 4, 6, or 8 pages per A4 sheet

## Requirements

```bash
# Ubuntu/Debian
sudo apt install python3 python3-tk poppler-utils

# Python packages
pip install reportlab PyPDF2 Pillow
```

## Usage

### GUI Mode
```bash
python3 combine_pdfs_gui.py
```

### CLI Mode
```bash
# Combine multiple PDFs (4 pages per sheet, default)
python3 combine_pdfs_cli.py -o output.pdf file1.pdf file2.pdf file3.pdf

# Print immediately after combining
python3 combine_pdfs_cli.py -o output.pdf -p file1.pdf file2.pdf

# Use 2 pages per sheet (larger output)
python3 combine_pdfs_cli.py -o output.pdf -n 2 file1.pdf file2.pdf

# Specify printer explicitly
python3 combine_pdfs_cli.py -o output.pdf -p -d E510-series file1.pdf file2.pdf

# Auto-detect all PDFs in ~/Downloads and combine
python3 combine_pdfs_cli.py
```

## Installation

### Linux Desktop (KDE/GNOME)
1. Copy `pdf-combine-print.desktop` to `~/.local/share/applications/`
2. Make it executable: `chmod +x ~/.local/share/applications/pdf-combine-print.desktop`
3. Copy icon: `cp icons/pdf-combine-print.png ~/.local/share/icons/`

### Dependencies
- `pdftoppm` from `poppler-utils`
- Python packages: `reportlab`, `PyPDF2`, `Pillow`, `tkinter`

## Project Structure

```
pdf-combine-print/
├── README.md
├── LICENSE
├── combine_pdfs_gui.py      # GUI application (Tkinter)
├── combine_pdfs_cli.py      # CLI application
├── pdf-combine-print.desktop  # Linux desktop integration
├── icons/
│   ├── pdf-combine-print.png
│   └── hicolor/             # Multiple icon sizes
└── screenshots/             # Application screenshots
```

## License

MIT License - see [LICENSE](LICENSE) for details.
