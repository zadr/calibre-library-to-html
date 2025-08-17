#!/usr/bin/env python3
"""
Export books and metadata from Calibre library using calibredb command.
Generates books.json, metadata.js, and copies covers compatible with books.html viewer.
"""

import json
import os
import subprocess
import sys
import shutil
from pathlib import Path
import argparse
import re
from datetime import datetime

# Default path to calibredb on macOS
DEFAULT_CALIBREDB = "/Applications/calibre.app/Contents/ebook-viewer.app/Contents/MacOS/calibredb"

def find_calibredb(custom_path=None):
    """Find the calibredb executable."""
    if custom_path and os.path.exists(custom_path):
        return custom_path
    
    # Try default macOS path
    if os.path.exists(DEFAULT_CALIBREDB):
        return DEFAULT_CALIBREDB
    
    # Try to find in PATH
    result = shutil.which("calibredb")
    if result:
        return result
    
    print("Error: calibredb not found. Please install Calibre or specify the path.")
    print(f"Tried: {DEFAULT_CALIBREDB}")
    print("\nYou can:")
    print("1. Install Calibre from https://calibre-ebook.com/")
    print("2. Specify the path with --calibredb /path/to/calibredb")
    sys.exit(1)

def find_calibre_library():
    """Try to find the default Calibre library location."""
    home = Path.home()
    
    # Common Calibre library locations
    possible_locations = [
        home / "Calibre Library",
        home / "Documents" / "Calibre Library",
        home / "Books" / "Calibre Library",
        home / "calibre",
    ]
    
    for location in possible_locations:
        if location.exists() and (location / "metadata.db").exists():
            return str(location)
    
    return None

def run_calibredb(calibredb_path, args, library_path=None):
    """Run a calibredb command and return the output."""
    cmd = [calibredb_path] + args
    if library_path:
        cmd.extend(["--library-path", library_path])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running calibredb: {e}")
        print(f"Command: {' '.join(cmd)}")
        print(f"Error output: {e.stderr}")
        return None

def parse_fallback_format(output):
    """Fallback parser if JSON parsing fails."""
    print("Warning: JSON parsing failed, using fallback parser")
    return []

def export_single_book(calibredb_path, book_id, output_dir, library_path=None):
    """Export a single book with its files to a directory."""
    output = run_calibredb(
        calibredb_path,
        ["export", "--to-dir", str(output_dir), "--single-dir", str(book_id)],
        library_path
    )
    return output is not None

def get_all_books_metadata(calibredb_path, library_path=None):
    """Get metadata for all books using calibredb list with JSON output."""
    # Use JSON output format for better parsing
    # Request all standard fields plus custom ones
    fields = "id,title,authors,author_sort,tags,series,series_index,publisher,pubdate,rating,comments,isbn,languages,formats,cover,uuid,size,identifiers"
    
    output = run_calibredb(
        calibredb_path, 
        ["list", "--for-machine", "--fields", fields],
        library_path
    )
    
    if not output:
        return []
    
    try:
        books = json.loads(output)
        return books
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from calibredb: {e}")
        # Try alternate parsing if JSON fails
        return parse_fallback_format(output)

def process_book_metadata(book):
    """Process raw book metadata from calibredb into our format."""
    # Extract UUID from identifiers if available
    uuid = book.get('uuid', '')
    if not uuid and 'identifiers' in book:
        # Try to extract UUID from identifiers
        identifiers = book.get('identifiers', {})
        if isinstance(identifiers, dict):
            uuid = identifiers.get('uuid', '')
    
    if not uuid:
        # Generate a UUID based on book ID
        uuid = f"book-{book.get('id', 0)}"
    
    # Process authors
    authors = book.get('authors', '')
    if authors:
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split('&')]
        elif not isinstance(authors, list):
            authors = [str(authors)]
    else:
        authors = []
    
    # Process tags
    tags = book.get('tags', [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',') if t.strip()]
    elif not isinstance(tags, list):
        tags = []
    
    # Process date
    pubdate = book.get('pubdate', '')
    if pubdate:
        try:
            # Try to parse and reformat date
            if isinstance(pubdate, str) and 'T' in pubdate:
                dt = datetime.fromisoformat(pubdate.replace('Z', '+00:00'))
                pubdate = dt.strftime('%Y-%m-%d')
        except:
            pass
    
    # Get cover path - calibredb returns it as a full path
    cover_path = book.get('cover', '')
    
    # If cover path is not absolute or doesn't exist, try to find it
    if cover_path and not os.path.isabs(cover_path):
        # Cover path might be relative to library
        formats = book.get('formats', [])
        if formats and len(formats) > 0:
            # Get directory from first format path
            book_dir = os.path.dirname(formats[0])
            possible_cover = os.path.join(book_dir, 'cover.jpg')
            if os.path.exists(possible_cover):
                cover_path = possible_cover
            else:
                # Try with the given filename
                possible_cover = os.path.join(book_dir, cover_path)
                if os.path.exists(possible_cover):
                    cover_path = possible_cover
    
    return {
        'id': str(book.get('id', 0)),
        'uuid': uuid,
        'title': book.get('title', 'Unknown'),
        'authors': authors,
        'authors_sort': book.get('author_sort', ''),
        'tags': tags,
        'series': book.get('series', ''),
        'series_index': book.get('series_index', ''),
        'pubdate': pubdate,
        'publisher': book.get('publisher', ''),
        'language': book.get('languages', ''),
        'rating': book.get('rating', ''),
        'formats': book.get('formats', []),
        'cover': cover_path,
        'comments': book.get('comments', ''),
        'size': book.get('size', 0),
    }

def export_all_books(calibredb_path, library_path=None, output_dir='.', 
                     export_covers=True, limit=None):
    """Export all books from the Calibre library."""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Auto-detect library if not specified
    if not library_path:
        library_path = find_calibre_library()
        if library_path:
            print(f"Auto-detected Calibre library at: {library_path}")
        else:
            print("Warning: Could not auto-detect Calibre library location.")
            print("Using calibredb default library.")
    
    # Get all books metadata
    print("Getting book metadata from Calibre...")
    raw_books = get_all_books_metadata(calibredb_path, library_path)
    
    if not raw_books:
        print("No books found in library")
        return
    
    print(f"Found {len(raw_books)} books in library")
    
    if limit:
        raw_books = raw_books[:limit]
        print(f"Limiting export to {limit} books")
    
    # Process books
    books_data = []
    metadata_dict = {}
    
    for i, raw_book in enumerate(raw_books, 1):
        print(f"Processing book {i}/{len(raw_books)}: {raw_book.get('title', 'Unknown')}")
        
        book = process_book_metadata(raw_book)
        books_data.append(book)
        
        # Create metadata entry
        uuid = book['uuid']
        metadata_dict[uuid] = {
            'title': book['title'],
            'creator': ', '.join(book['authors']),
            'description': book.get('comments', ''),
            'publisher': book.get('publisher', ''),
            'subject': book.get('tags', []),
            'date': book.get('pubdate', ''),
            'language': book.get('language', ''),
            'series': book.get('series', ''),
            'rating': book.get('rating', ''),
        }
    
    # Export covers if requested
    if export_covers:
        covers_dir = output_dir / "covers"
        covers_dir.mkdir(exist_ok=True)
        
        print("\nExporting covers...")
        copied = 0
        missing = 0
        
        for book in books_data:
            if book.get('cover') and os.path.exists(book['cover']):
                uuid = book['uuid']
                dest_path = covers_dir / f"{uuid}.jpg"
                
                try:
                    shutil.copy2(book['cover'], dest_path)
                    copied += 1
                    print(f"  ✓ {book['title']}")
                except Exception as e:
                    print(f"  ✗ Failed to copy cover for {book['title']}: {e}")
                    missing += 1
            else:
                missing += 1
        
        print(f"\nCovers: {copied} copied, {missing} missing/skipped")
    
    # Write books.js
    books_js_path = output_dir / "books.js"
    with open(books_js_path, 'w', encoding='utf-8') as f:
        f.write('// Book library data\n')
        f.write('const booksLibraryData = ')
        json.dump({'books': books_data}, f, indent=2, ensure_ascii=False)
        f.write(';\n')
    print(f"✓ Created {books_js_path}")
    
    # Write metadata.js
    metadata_js_path = output_dir / "metadata.js"
    with open(metadata_js_path, 'w', encoding='utf-8') as f:
        f.write('// Book metadata extracted from Calibre\n')
        f.write('const bookMetadata = ')
        json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
        f.write(';\n')
    print(f"✓ Created {metadata_js_path}")
    
    # Copy books.html viewer if it exists in the same directory as this script
    script_dir = Path(__file__).parent
    books_html_src = script_dir / "books.html"
    books_html_dst = output_dir / "books.html"
    
    if books_html_src.exists() and books_html_src != books_html_dst:
        try:
            shutil.copy2(books_html_src, books_html_dst)
            print(f"✓ Copied books.html viewer")
        except Exception as e:
            print(f"Warning: Could not copy books.html: {e}")
            print(f"  You may need to manually copy books.html to {output_dir}")
    elif not books_html_dst.exists():
        print(f"\n⚠️  Note: books.html viewer not found in script directory")
        print(f"  Copy books.html to {output_dir} to view the library")
    
    print(f"\n✅ Export complete!")
    print(f"   Books exported: {len(books_data)}")
    print(f"   Output directory: {output_dir.absolute()}")
    
    if books_html_dst.exists():
        print(f"\n📖 Open books.html in your browser to view the library:")
        print(f"   file://{books_html_dst.absolute()}")
    else:
        print(f"\n📖 Copy books.html to {output_dir} and open it to view the library")

def main():
    parser = argparse.ArgumentParser(
        description='Export books and metadata from Calibre library',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export from default Calibre library to output/ folder
  python export_calibre_library.py
  
  # Export from specific library
  python export_calibre_library.py --library ~/MyBooks
  
  # Export to specific directory
  python export_calibre_library.py --output ~/Desktop/my-library
  
  # Export without covers (faster)
  python export_calibre_library.py --no-covers
  
  # Test with first 10 books
  python export_calibre_library.py --limit 10
  
  # Use specific calibredb path
  python export_calibre_library.py --calibredb /usr/local/bin/calibredb
        """
    )
    parser.add_argument(
        '--calibredb', 
        help=f'Path to calibredb executable',
        default=None
    )
    parser.add_argument(
        '--library', '-l',
        help='Path to Calibre library (auto-detect if not specified)',
        default=None
    )
    parser.add_argument(
        '--output', '-o',
        help='Output directory (default: output/)',
        default='output'
    )
    parser.add_argument(
        '--no-covers',
        action='store_true',
        help='Skip exporting cover images'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of books to export (for testing)',
        default=None
    )
    
    args = parser.parse_args()
    
    # Find calibredb
    calibredb_path = find_calibredb(args.calibredb)
    print(f"Using calibredb at: {calibredb_path}")
    
    # Export books
    export_all_books(
        calibredb_path,
        library_path=args.library,
        output_dir=args.output,
        export_covers=not args.no_covers,
        limit=args.limit
    )

if __name__ == '__main__':
    main()