#!/usr/bin/env python3
"""Render a Swedish Ox morning brief from Markdown to the site's HTML style.

Usage:
  python3 render.py briefs/2026-11-04.md [--headline "Text for the index card"]
  python3 render.py --all            # render every briefs/*.md (idempotent)

Writes briefs/YYYY-MM-DD.html and inserts (or replaces) the card for that date
in index.html under <!-- ARCHIVE: newest first -->, keeping newest first, and
removes the "first edition coming" placeholder. Uses the `markdown` library if
installed, otherwise a built-in converter (headings, lists, bold, italics,
links, code, quotes, rules, paragraphs). Em-dashes are replaced automatically.
Headline: --headline, else a "<!-- rubrik: ... -->" line, else the first H1,
else the first paragraph.
"""
import argparse, datetime as dt, glob, html, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MARK = "<!-- ARCHIVE: newest first -->"
DAYS = ["måndag", "tisdag", "onsdag", "torsdag", "fredag", "lördag", "söndag"]
MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli",
          "augusti", "september", "oktober", "november", "december"]


def sv_date(d):
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


def no_dash(s):
    s = re.sub(r"\s*\u2014\s*", ", ", s)  # em-dash
    return s.replace("\u2015", "-")


def inline(t):
    codes = []
    def keep(m):
        codes.append(m.group(1)); return f"\x00{len(codes)-1}\x00"
    t = re.sub(r"`([^`]+)`", keep, t)
    t = html.escape(t, quote=False)
    t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img alt="\1" src="\2">', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"(?<![\"=>])(https?://[^\s<]+[^\s<.,;:)])", r'<a href="\1">\1</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{html.escape(codes[int(m.group(1))])}</code>", t)
    return t


def basic_md(src):
    out, para, stack = [], [], []  # stack of (indent, tag)
    lines = src.split("\n")
    i = 0
    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
    def close_lists(to=-1):
        while stack and stack[-1][0] > to:
            out.append(f"</li></{stack.pop()[1]}>")
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith("```"):
            flush(); close_lists(); buf = []; i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>"); i += 1; continue
        m_li = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", ln)
        if not ln.strip():
            flush(); i += 1; continue
        if m_li:
            flush()
            ind = len(m_li.group(1).expandtabs(4)); tag = "ol" if m_li.group(2)[0].isdigit() else "ul"
            if stack and ind > stack[-1][0]:
                out.append(f"<{tag}><li>"); stack.append((ind, tag))
            else:
                close_lists(ind)
                if stack and stack[-1][0] == ind and stack[-1][1] != tag:
                    out.append(f"</li></{stack.pop()[1]}>")
                if stack and stack[-1][0] == ind:
                    out.append("</li><li>")
                else:
                    out.append(f"<{tag}><li>"); stack.append((ind, tag))
            out.append(inline(m_li.group(3))); i += 1; continue
        if stack and lines[i].startswith((" ", "\t")):
            out.append(" " + inline(ln.strip())); i += 1; continue
        close_lists()
        m_h = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", ln)
        if m_h:
            flush(); n = len(m_h.group(1)); out.append(f"<h{n}>{inline(m_h.group(2))}</h{n}>")
        elif re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", ln):
            flush(); out.append("<hr>")
        elif ln.startswith(">"):
            flush(); buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip(">").strip()); i += 1
            out.append("<blockquote>" + basic_md("\n".join(buf)) + "</blockquote>"); continue
        elif ln.lstrip().startswith("<!--"):
            pass
        else:
            para.append(ln.strip())
        i += 1
    flush(); close_lists()
    return "\n".join(out)


def to_html(src):
    try:
        import markdown
        return markdown.markdown(src, extensions=["extra", "sane_lists"])
    except ImportError:
        return basic_md(src)


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


PAGE = """<!doctype html><html lang="sv"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ox morgonbrief, {date_long}</title><link rel="stylesheet" href="../style.css?v=1"></head><body><main>
<header class="topbar"><a class="brand" href="../">Ox morgonbrief</a><span class="date">{date_long}</span></header>
<article>
{body}
</article>
<a class="back" href="../">&larr; Alla utgåvor</a>
<footer>Ox morgonbrief, sammanställd av Datacentrrs och publicerad av Daily Brief.</footer>
</main></body></html>
"""


def render(md_path, headline=None):
    name = os.path.basename(md_path)
    m = re.match(r"^(\d{4}-\d{2}-\d{2})\.md$", name)
    if not m:
        sys.exit(f"Expected briefs/YYYY-MM-DD.md, got {md_path}")
    date = m.group(1); d = dt.date.fromisoformat(date); long = sv_date(d)
    with open(md_path, encoding="utf-8") as f:
        src = no_dash(f.read())
    if not headline:
        mr = re.search(r"<!--\s*rubrik:\s*(.*?)\s*-->", src, re.I)
        mh = re.search(r"^#\s+(.+)$", src, re.M)
        mp = re.search(r"^(?![#>\-*+\s<]|\d+[.)])(.+)$", src, re.M)
        headline = (mr and mr.group(1)) or (mh and mh.group(1)) or (mp and mp.group(1)) or f"Ox morgonbrief {date}"
        headline = strip_tags(inline(headline))
    headline = no_dash(headline)
    body = to_html(src)
    if not re.search(r"<h1[\s>]", body):
        body = f"<h1>Ox morgonbrief</h1>\n<p class=\"sub\">{html.escape(long)}</p>\n" + body
    out = os.path.join(ROOT, "briefs", f"{date}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(PAGE.format(date_long=html.escape(long), body=body))

    idx = os.path.join(ROOT, "index.html")
    with open(idx, encoding="utf-8") as f:
        page = f.read()
    page = re.sub(r'\s*<div class="placeholder"[^\n]*</div>', "", page)
    card = (f'<a class="bcard" href="briefs/{date}.html"><div class="d">{html.escape(long)}</div>'
            f'<div class="h">{html.escape(headline)}</div></a>')
    allcards = dict(re.findall(r'(?s)<a class="bcard" href="briefs/(\d{4}-\d{2}-\d{2})\.html">(.*?)</a>', page))
    page = re.sub(r'\n?<a class="bcard" href="briefs/\d{4}-\d{2}-\d{2}\.html">.*?</a>', "", page)
    allcards = {k: f'<a class="bcard" href="briefs/{k}.html">{v}</a>' for k, v in allcards.items()}
    allcards[date] = card
    block = "\n".join(allcards[k] for k in sorted(allcards, reverse=True))
    page = page.replace(MARK, MARK + "\n" + block, 1)
    with open(idx, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Rendered {out}\nCard: {long} | {headline}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Render Ox morgonbrief Markdown to HTML")
    ap.add_argument("md", nargs="?", help="briefs/YYYY-MM-DD.md")
    ap.add_argument("--headline", help="Card headline for the index")
    ap.add_argument("--all", action="store_true", help="Render all briefs/*.md")
    a = ap.parse_args()
    if a.all:
        for p in sorted(glob.glob(os.path.join(ROOT, "briefs", "*.md"))):
            render(p)
    elif a.md:
        render(a.md, a.headline)
    else:
        ap.print_help()
