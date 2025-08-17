# Calibre Library Web Viewer

A lightweight web-based viewer for Calibre libraries with search, sort, and column management.

## Quick Start

```bash
# Export your Calibre library to output/ folder
python export_calibre_library.py

# Open in browser
open output/books.html
```

## Installation

1. Ensure [Calibre](https://calibre-ebook.com/) is installed
2. Clone or download these files:
   - `export_calibre_library.py`
   - `books.html`

## Usage

### Export from Calibre

```bash
# Auto-detect library and calibredb (exports to output/)
python export_calibre_library.py

# Specify library location
python export_calibre_library.py --library ~/MyBooks

# Export to specific directory
python export_calibre_library.py --output ./my-library

# Test with limited books
python export_calibre_library.py --limit 10
```

### View Library

Open `books.html` in any modern web browser. No server required.

## Files Generated

- `books.js` - Book data (JavaScript)
- `metadata.js` - Extended metadata  
- `covers/` - Cover images
- `books.html` - Viewer interface

## Requirements

- Python 3.6+
- Calibre (for calibredb command)
- A web browser

## License

MIT
