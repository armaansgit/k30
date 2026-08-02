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
SITE_TITLE = "🍁"

KATEX_HEAD = (
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">\n'
    '    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>\n'
    '    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"\n'
    "        onload=\"renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]});\"></script>"
)


def template(title, content, back, use_katex=True):
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
<body>
    <main>
{content}
    </main>
    <footer>
        <a href="{back}"><i>../</i></a>
        <div id="clock-container"></div>
    </footer>
    <script>
        const quotes = {{
            late: [
                "Another day burned. Are you closer to your dream, or just closer to the grave?",
                "You are running out of time on this earth. Why are you wasting tonight?",
                "They sleep because they earned it. You're awake because you're terrified of being average. Act like it."
            ],
            morning: [
                "You woke up. Congratulations. Now prove you deserve to be breathing.",
                "Are you going to waste another 24 hours lying to yourself about your potential?",
                "Someone out there is working right now with half your talent and twice your discipline."
            ],
            noon: [
                "Half the day is gone. If you died today, would you be proud of what you left behind?",
                "Comfort is killing you slowly. Are you feeding your stomach or your purpose?",
                "Stop negotiating with your weakness. Do the fucking work."
            ],
            afternoon: [
                "You want to quit because you're tired. That's why no one will remember your name.",
                "Watching the clock doesn't change the fact that you're underperforming.",
                "Is this the maximum effort of your life? Pathetic. Dig deeper."
            ],
            evening: [
                "The day is ending, but your mediocrity remains. Fix it.",
                "Did you earn the right to sleep tonight, or did you just survive another day?",
                "Look in the mirror. Does the person looking back respect you? Be honest."
            ]
        }};
        
        const patterns = ['mor_0503.jpg', 'mor_0702.jpg', 'mor_0233.jpg', 'mor_0413.jpg', 'mor_0414.jpg', 'mor_0411.jpg'];
        const randomPattern = patterns[Math.floor(Math.random() * patterns.length)];
        const sidePatternEl = document.getElementById('home-image');
        if (sidePatternEl) {{
            sidePatternEl.style.backgroundImage = "url('/" + randomPattern + "')";
        }}
        
        let lastHour = -1;
        let currentQuote = '';
        
        function updateClock() {{
            const now = new Date();
            const h = now.getHours();
            
            if (h !== lastHour) {{
                let pool = [];
                if (h < 5) pool = quotes.late;
                else if (h < 12) pool = quotes.morning;
                else if (h < 14) pool = quotes.noon;
                else if (h < 18) pool = quotes.afternoon;
                else pool = quotes.evening;
                
                currentQuote = pool[Math.floor(Math.random() * pool.length)];
                lastHour = h;
            }}
            
            const timeStr = now.toLocaleTimeString('en-US');
            const el = document.getElementById('clock-container');
            if (el) el.innerText = timeStr + " — " + currentQuote;
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

    page = template(SITE_TITLE, content, "/", use_katex=False)
    # custom footer for homepage
    footer_html = "\n        ".join(footer_links)
    page = page.replace(
        '<a href="/"><i>../</i></a>',
        footer_html
    )
    (ROOT / "index.html").write_text(page, encoding="utf-8")


def main():
    # clean generated posts
    if POSTS_DIR.exists():
        shutil.rmtree(POSTS_DIR)

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

    # build index pages
    build_posts_index(posts)
    build_homepage(posts)

    print(f"\n  done — {len(posts)} post(s) built")


if __name__ == "__main__":
    main()
