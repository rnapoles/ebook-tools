#!/usr/bin/env python3
"""
md2epub.py — Convert a folder of Markdown files (and/or images) into a single EPUB e-book.

Each .md, .png, .jpg/.jpeg file in the input folder becomes one page/chapter,
combined and sorted together in alphabetical (natural) order. This lets you
interleave text chapters with full-page images (e.g. illustrations, comic
pages, scanned pages) just by naming files so they sort in the order you want
(e.g. 01-intro.md, 02-illustration.png, 03-chapter1.md ...).

- Markdown files: the first-level heading (# Title) is used as the chapter
  title if present; otherwise the filename (without extension) is used.
- Image files (.png, .jpg, .jpeg): rendered as a single full-page image with
  no extra chrome. The filename (without extension) is used as the title in
  the table of contents.

Dependencies:
    pip install markdown

Usage:
    python md2epub.py <input_folder> -o output.epub --title "My Book" --author "Jane Doe"

Examples:
    python md2epub.py ./chapters -o mybook.epub --title "The Great Novel" --author "A. Writer"
    python md2epub.py ./notes -o notes.epub
    python md2epub.py ./comic_pages -o comic.epub --title "My Comic"
"""

import argparse
import html
import os
import re
import sys
import uuid
import zipfile
from pathlib import Path

try:
    import markdown as md_lib
except ImportError:
    sys.exit(
        "Missing dependency 'markdown'. Install it with:\n"
        "    pip install markdown"
    )


def natural_sort_key(path: Path):
    """Sort like humans expect: chapter2 before chapter10."""
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", path.name)
    ]


def extract_title(md_text: str, fallback: str) -> str:
    """Grab the first level-1 heading as a chapter title, else use fallback."""
    match = re.search(r"^\s*#\s+(.+)$", md_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback


def build_chapter_html(title: str, body_html: str) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="utf-8" />
<title>{html.escape(title)}</title>
<link rel="stylesheet" type="text/css" href="style.css" />
</head>
<body>
{body_html}
</body>
</html>"""

# <h1>{html.escape(title)}</h1>

def build_image_page_html(title: str, image_href: str) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="utf-8" />
<title>{html.escape(title)}</title>
<link rel="stylesheet" type="text/css" href="style.css" />
</head>
<body class="image-page">
<div class="image-page-wrap">
<img src="{image_href}" alt="{html.escape(title)}" />
</div>
</body>
</html>"""


IMAGE_EXTENSIONS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

DEFAULT_CSS = """
body { font-family: serif; line-height: 1.5; margin: 1em; }
h1 { text-align: center; margin-bottom: 1em; }
h2, h3, h4 { margin-top: 1.5em; }
p { text-indent: 1em; margin: 0 0 0.5em 0; }
img { max-width: 100%; }

body.image-page { margin: 0; padding: 0; }
.image-page-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  margin: 0;
  padding: 0;
}
.image-page-wrap img {
  max-width: 100%;
  max-height: 100vh;
  width: auto;
  height: auto;
}
"""


def build_epub(input_folder: Path, output_path: Path, title: str, author: str, language: str):
    source_files = sorted(
        [
            p
            for p in input_folder.iterdir()
            if p.suffix.lower() == ".md" or p.suffix.lower() in IMAGE_EXTENSIONS
        ],
        key=natural_sort_key,
    )
    if not source_files:
        sys.exit(f"No .md, .png, or .jpg/.jpeg files found in {input_folder}")

    book_uuid = str(uuid.uuid4())
    chapters = []  # list of (id, filename, title, html_text)
    image_assets = []  # list of (asset_id, href, media_type, raw_bytes)

    for i, src_path in enumerate(source_files, start=1):
        chap_id = f"chap{i:03d}"
        ext = src_path.suffix.lower()

        if ext == ".md":
            text = src_path.read_text(encoding="utf-8")
            chapter_title = extract_title(text, fallback=src_path.stem)
            body_html = md_lib.markdown(
                text, extensions=["extra", "toc", "tables", "fenced_code"]
            )
            filename = f"{chap_id}.xhtml"
            chapters.append((chap_id, filename, chapter_title, build_chapter_html(chapter_title, body_html)))
        else:
            media_type = IMAGE_EXTENSIONS[ext]
            chapter_title = src_path.stem
            filename = f"{chap_id}.xhtml"
            asset_id = f"img{i:03d}"
            asset_href = f"images/{asset_id}{ext}"
            image_assets.append((asset_id, asset_href, media_type, src_path.read_bytes()))
            chapters.append((chap_id, filename, chapter_title, build_image_page_html(chapter_title, asset_href)))

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as epub:
        # 1. mimetype must be first and stored uncompressed
        epub.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)

        # 2. META-INF/container.xml
        epub.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
        )

        # 3. CSS
        epub.writestr("OEBPS/style.css", DEFAULT_CSS)

        # 4. Chapter XHTML files
        for chap_id, filename, chapter_title, chapter_html in chapters:
            epub.writestr(f"OEBPS/{filename}", chapter_html)

        # 4b. Image assets
        for asset_id, asset_href, media_type, raw_bytes in image_assets:
            epub.writestr(f"OEBPS/{asset_href}", raw_bytes)

        # 5. Table of contents (nav.xhtml — EPUB3)
        nav_items = "\n".join(
            f'      <li><a href="{filename}">{html.escape(chapter_title)}</a></li>'
            for _, filename, chapter_title, _ in chapters
        )
        epub.writestr(
            "OEBPS/nav.xhtml",
            f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Table of Contents</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
{nav_items}
    </ol>
  </nav>
</body>
</html>""",
        )

        # 6. NCX (EPUB2 compatibility, some readers still want it)
        navpoints = "\n".join(
            f"""    <navPoint id="{chap_id}" playOrder="{i}">
      <navLabel><text>{html.escape(chapter_title)}</text></navLabel>
      <content src="{filename}"/>
    </navPoint>"""
            for i, (chap_id, filename, chapter_title, _) in enumerate(chapters, start=1)
        )
        epub.writestr(
            "OEBPS/toc.ncx",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{book_uuid}"/>
  </head>
  <docTitle><text>{html.escape(title)}</text></docTitle>
  <navMap>
{navpoints}
  </navMap>
</ncx>""",
        )

        # 7. content.opf (package manifest)
        manifest_items = "\n".join(
            f'    <item id="{chap_id}" href="{filename}" media-type="application/xhtml+xml"/>'
            for chap_id, filename, _, _ in chapters
        )
        image_manifest_items = "\n".join(
            f'    <item id="{asset_id}" href="{asset_href}" media-type="{media_type}"/>'
            for asset_id, asset_href, media_type, _ in image_assets
        )
        if image_manifest_items:
            manifest_items = f"{manifest_items}\n{image_manifest_items}"
        spine_items = "\n".join(
            f'    <itemref idref="{chap_id}"/>' for chap_id, _, _, _ in chapters
        )
        epub.writestr(
            "OEBPS/content.opf",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="BookId">urn:uuid:{book_uuid}</dc:identifier>
    <dc:title>{html.escape(title)}</dc:title>
    <dc:creator>{html.escape(author)}</dc:creator>
    <dc:language>{html.escape(language)}</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="css" href="style.css" media-type="text/css"/>
{manifest_items}
  </manifest>
  <spine toc="ncx">
{spine_items}
  </spine>
</package>""",
        )

    print(f"Wrote {output_path} ({len(chapters)} chapter(s)).")


def main():
    parser = argparse.ArgumentParser(description="Convert a folder of Markdown files into one EPUB.")
    parser.add_argument("input_folder", type=Path, help="Folder containing .md and/or .png, .jpg, .jpeg files")
    parser.add_argument("-o", "--output", type=Path, default=Path("output.epub"), help="Output .epub path")
    parser.add_argument("--title", default="Untitled", help="Book title")
    parser.add_argument("--author", default="Unknown", help="Book author")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    args = parser.parse_args()

    if not args.input_folder.is_dir():
        sys.exit(f"Not a folder: {args.input_folder}")

    build_epub(args.input_folder, args.output, args.title, args.author, args.language)


if __name__ == "__main__":
    main()