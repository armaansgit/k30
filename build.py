#!/usr/bin/env python3
"""
Site builder — converts markdown files to HTML.

Usage:  python3 build.py

Put .md files in src/ folder:
    src/my-post.md                  (simple post)
    src/my-post/index.md + images   (post with images)

Supports: markdown, LaTeX math ($..$ and $$..$$), images.
"""

import os, re, shutil, time
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
SRC = ROOT / "src"
POSTS_DIR = ROOT / "posts"
KREADS_SRC = ROOT / "src" / "kreads"
INFO_KREADS_DIR = ROOT / "info" / "kreads"
SITE_TITLE = '<img src="/maple_leaf.png" alt="Maple leaf" class="site-logo">'
SITE_TITLE_TEXT = "🍁"

KATEX_HEAD = (
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">\n'
    '    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>\n'
    '    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"\n'
    "        onload=\"renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]});\"></script>"
)


def template(title, content, back, use_katex=True, body_class=""):
    katex = f"\n    {KATEX_HEAD}" if use_katex else ""
    v = int(time.time())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <link rel="stylesheet" href="/style.css?v={v}">{katex}
</head>
<body class="{body_class}">
    <main>
{content}
    </main>
    <footer>
        <a href="{back}"><i>../</i></a>
        <div id="clock-container"></div>
    </footer>
    <script>
        const patterns = ['mor_0503.jpg', 'mor_0702.jpg', 'mor_0233.jpg', 'mor_0413.jpg', 'mor_0414.jpg', 'mor_0411.jpg', 'mor_1208.jpg', 'mor_1114.jpg', 'mor_0912.jpg', 'ind_0215.jpg', 'ind_0235.jpg', 'ind_0417.jpg', 'ind_0415.jpg'];
        const randomPattern = patterns[Math.floor(Math.random() * patterns.length)];
        const sidePatternEl = document.getElementById('home-image');
        if (sidePatternEl) {{
            sidePatternEl.style.backgroundImage = "url('/" + randomPattern + "')";
        }}
        
        function updateClock() {{
            const timeStr = new Date().toLocaleTimeString('en-US');
            const el = document.getElementById('clock-container');
            if (el) el.innerText = timeStr;
        }}
        setInterval(updateClock, 1000);
        updateClock();
    </script>
</body>
</html>"""


def protect_math(text):
    """Replace math with placeholders so markdown doesn't mangle them."""
    store = []
    def save(m):
        store.append(m.group(0))
        return f"MATHPLACEHOLDER{len(store)-1}END"
    # display math first ($$...$$)
    text = re.sub(r'\$\$[\s\S]+?\$\$', save, text)
    # inline math ($...$)
    text = re.sub(r'(?<!\$)\$(?!\s)([^\n$]+?)(?<!\s)\$(?!\$)', save, text)
    return text, store


def restore_math(html, store):
    for i, orig in enumerate(store):
        html = html.replace(f"MATHPLACEHOLDER{i}END", orig)
    return html


def get_title(text):
    """Extract title from first # heading."""
    m = re.match(r'^#\s+(.+)', text, re.MULTILINE)
    return m.group(1).strip() if m else "Untitled"


def find_posts():
    """Find all .md source files. Prefix filenames with 01-, 02- etc to control order."""
    posts = []
    if not SRC.exists():
        return posts
    for item in sorted(SRC.iterdir()):
        if item.suffix == ".md":
            slug = re.sub(r'^\d+-', '', item.stem)  # strip number prefix
            posts.append((slug, item, item.parent))
        elif item.is_dir():
            md = item / "index.md"
            if md.exists():
                slug = re.sub(r'^\d+-', '', item.name)  # strip number prefix
                posts.append((slug, md, item))
    return posts


def build_post(slug, md_path, src_dir):
    """Convert one markdown file to HTML."""
    raw = md_path.read_text(encoding="utf-8")
    title = get_title(raw)

    # protect math from markdown processing
    text, math_store = protect_math(raw)

    # convert markdown to html
    html_body = markdown.markdown(text, extensions=["fenced_code", "tables"])

    # restore math
    html_body = restore_math(html_body, math_store)

    # make title italic
    html_body = re.sub(r'<h1>(.*?)</h1>', r'<h1><em>\1</em></h1>', html_body, count=1)

    has_math = len(math_store) > 0
    page = template(title, f"        {html_body}", "/posts/", use_katex=has_math)

    # write output
    out_dir = POSTS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page, encoding="utf-8")

    # copy images and other files (not .md)
    if src_dir != SRC:  # folder-based post
        for f in src_dir.iterdir():
            if f.suffix != ".md":
                shutil.copy2(f, out_dir / f.name)

    return slug, title, md_path.stat().st_mtime


def build_posts_index(posts):
    """Generate posts/index.html."""
    total = len(posts)
    links = "\n".join(
        f'        <a href="/posts/{slug}/">{total - i}. <i>{title}</i></a>' for i, (slug, title, _) in enumerate(posts)
    )
    content = f"        <h1>Posts</h1>\n{links}"
    page = template("Posts", content, "/", use_katex=False)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    (POSTS_DIR / "index.html").write_text(page, encoding="utf-8")


def build_homepage(posts):
    """Generate index.html with recent posts."""
    recent = posts[:7]  # show 7 most recent on homepage
    total = len(posts)
    links = "\n".join(
        f'        <a href="/posts/{slug}/">{total - i}. <i>{title}</i></a>' for i, (slug, title, _) in enumerate(recent)
    )
    if links:
        content = f"""<div id="home-container">
            <div id="home-image"></div>
            <div>
                <h1>{SITE_TITLE}</h1>
{links}
            </div>
        </div>"""
    else:
        content = f"        <h1>{SITE_TITLE}</h1>"

    footer_links = []
    if posts:
        footer_links.append('<a href="/posts/"><i>v</i></a>')
    footer_links.append('<a href="/info/"><i>Info</i></a>')

    page = template(SITE_TITLE_TEXT, content, "/", use_katex=False, body_class="home")
    # custom footer for homepage
    footer_html = "\n        ".join(footer_links)
    page = page.replace(
        '<a href="/"><i>../</i></a>',
        footer_html
    )
    (ROOT / "index.html").write_text(page, encoding="utf-8")


def find_kreads():
    """Find books and chapters in src/kreads/. Returns dict of {book_slug: [(chapter_slug, md_path, src_dir), ...]}."""
    books = {}
    if not KREADS_SRC.exists():
        return books
    for item in sorted(KREADS_SRC.iterdir()):
        if item.is_dir():
            book_slug = item.name
            chapters = []
            for ch in sorted(item.iterdir()):
                if ch.suffix == ".md":
                    ch_slug = re.sub(r'^\d+-', '', ch.stem)
                    chapters.append((ch_slug, ch, ch.parent))
            books[book_slug] = chapters
    return books


def build_kread_chapter(book_slug, ch_slug, md_path, src_dir):
    raw = md_path.read_text(encoding="utf-8")
    title = get_title(raw)
    text, math_store = protect_math(raw)
    html_body = markdown.markdown(text, extensions=["fenced_code", "tables"])
    html_body = restore_math(html_body, math_store)
    html_body = re.sub(r'<h1>(.*?)</h1>', r'<h1><em>\1</em></h1>', html_body, count=1)
    
    has_math = len(math_store) > 0
    back_link = f"/info/kreads/{book_slug}/"
    page = template(title, f"        {html_body}", back_link, use_katex=has_math)
    
    out_dir = INFO_KREADS_DIR / book_slug / ch_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    
    return ch_slug, title


def copy_kread_assets(book_slug, src_dir):
    out_dir = INFO_KREADS_DIR / book_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in src_dir.iterdir():
        if f.suffix != ".md" and not f.is_dir():
            shutil.copy2(f, out_dir / f.name)


def build_kreads_indexes(books):
    INFO_KREADS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Build index for each book (listing chapters)
    for book_slug, chapters in books.items():
        links = "\n".join(
            f'        <a href="/info/kreads/{book_slug}/{ch_slug}/">{i+1}. <i>{title}</i></a><br>' for i, (ch_slug, title) in enumerate(chapters)
        )
        content = f"        <h1>{book_slug}</h1>\n        <p>-</p>\n{links}"
        page = template(book_slug, content, "/info/kreads/", use_katex=False)
        book_out = INFO_KREADS_DIR / book_slug
        book_out.mkdir(parents=True, exist_ok=True)
        (book_out / "index.html").write_text(page, encoding="utf-8")
        
    # 2. Build root kreads index (listing books)
    links = "\n".join(
        f'        <a href="/info/kreads/{book_slug}/"><i>{book_slug}</i></a><br>' for book_slug in books.keys()
    )
    content = f"""        <h1>kreads</h1>
        <p>-</p>
        
        <p>Reading List</p>
        Stray Reflections (1910) [x]<br>
        <br>
        
        <p>Book Notes</p>
{links}
        <br>
        
        <p>Favorite Authors</p>
        <i>Allama Iqbal</i><br>
        <i>Georg Wilhelm Friedrich Hegel</i><br>
        <i>Johann Wolfgang von Goethe</i><br>
        <i>Friedrich Nietzsche</i><br>"""
    page = template("kreads", content, "/info/", use_katex=False)
    (INFO_KREADS_DIR / "index.html").write_text(page, encoding="utf-8")


def main():
    # clean generated posts
    if POSTS_DIR.exists():
        shutil.rmtree(POSTS_DIR)
    if INFO_KREADS_DIR.exists():
        shutil.rmtree(INFO_KREADS_DIR)

    # find and build all posts
    sources = find_posts()
    posts = []
    for slug, md_path, src_dir in sources:
        slug, title, mtime = build_post(slug, md_path, src_dir)
        posts.append((slug, title, mtime))
        print(f"  built: {slug}")

    # order is controlled by filename prefixes (01-, 02-, etc.)
    # we want newest (highest prefix) first, so we reverse it
    posts.reverse()

    # build kreads
    kreads_books = find_kreads()
    built_books = {}
    for book_slug, chapters in kreads_books.items():
        built_chapters = []
        for ch_slug, md_path, src_dir in chapters:
            ch_slug, title = build_kread_chapter(book_slug, ch_slug, md_path, src_dir)
            built_chapters.append((ch_slug, title))
            print(f"  built kread: {book_slug}/{ch_slug}")
        if chapters:
            copy_kread_assets(book_slug, chapters[0][2])
        built_books[book_slug] = built_chapters
        
    build_kreads_indexes(built_books)

    # build index pages
    build_posts_index(posts)
    build_homepage(posts)

    print(f"\n  done — {len(posts)} post(s) built")


if __name__ == "__main__":
    main()
