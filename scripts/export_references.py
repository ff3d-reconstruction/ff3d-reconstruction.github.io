"""Export the numbered bibliography and cited-section links for the website."""
import argparse
import html
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from export_data import citation_numbers, field, safe_link

HEADING = re.compile(r"^\\(section|subsection|subsubsection)\{([^{}]+)\}", re.M)
CITE = re.compile(r"\\cite(?:\s*\[[^]]+\])?\s*\{([^{}]+)\}")
TABLE_CITE = re.compile(r"\\LitRowRef\{[^{}]+\}\{([^{}]+)\}")
ACCENTS = {'"': "\u0308", "'": "\u0301", "c": "\u0327"}


def plain_latex(value):
    for old, new in ((r"\ss", "ß"), (r"\circ", "°"), (r"\pi^3", "π³"),
                     (r"\mu", "μ"), (r"\pi", "π"), (r"\Omega", "Ω"), (r"\&", "&"), (r"\%", "%")):
        value = value.replace(old, new)
    value = re.sub(r'\\(["\x27c])\s*(?:\{([A-Za-z])\}|([A-Za-z]))',
                   lambda m: unicodedata.normalize("NFC", (m[2] or m[3]) + ACCENTS[m[1]]), value)
    value = value.replace("~", " ").replace("---", "—").replace("--", "–")
    return " ".join(value.translate(str.maketrans("", "", "{}$")).split())


def section_citations(paper, numbered):
    main = (paper / "main.tex").read_text(encoding="utf-8-sig")
    chapters = {}
    sections = defaultdict(set)
    counters = [0, 0, 0]
    for file in re.findall(r"^\\input\{(sections/[^}]+)\}", main, re.M):
        text = (paper / f"{file}.tex").read_text(encoding="utf-8-sig")
        text = re.sub(r"(?<!\\)%.*", "", text)
        headings = list(HEADING.finditer(text))
        for i, hit in enumerate(headings):
            rank = ("section", "subsection", "subsubsection").index(hit[1])
            counters[rank] += 1
            counters[rank + 1:] = [0] * (2 - rank)
            if rank == 0:
                chapters[str(counters[0])] = plain_latex(hit[2])
            body_end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            body = text[hit.end():body_end]
            keys = {key.strip() for match in CITE.findall(body) + TABLE_CITE.findall(body)
                    for key in match.split(",")}
            numbers = {numbered[key] for key in keys if key in numbered}
            for depth in range(rank + 1):
                section = ".".join(str(n) for n in counters[:depth + 1])
                sections[section].update(numbers)
    return chapters, sections


def bibliography(paper, numbered, chapters, sections):
    source = (paper / "references.bib").read_text(encoding="utf-8-sig")
    entries = {key: (kind, body) for kind, key, body in re.findall(
        r"^@(\w+)\{([^,]+),\s*(.*?)(?=^\})", source, re.M | re.S)}
    printed = (paper / "build/main.bbl").read_text(encoding="utf-8-sig")
    printed = printed.split(r"\end{thebibliography}", 1)[0]
    parts = re.split(r"\\bibitem\{([^}]+)\}", printed)
    formatted = dict(zip(parts[1::2], parts[2::2]))
    if set(formatted) != set(numbered) or not set(numbered).issubset(entries):
        raise ValueError("The compiled bibliography and citation labels do not match")
    cards, bibtex = [], []
    for key, number in sorted(numbered.items(), key=lambda pair: pair[1]):
        kind, body = entries[key]
        raw = formatted[key]
        doi = field(body, "doi")
        bbl_href = re.search(r"\\url\{([^}]+)\}", raw)
        url = safe_link("https://doi.org/" + doi) if doi else safe_link(field(body, "url"))
        if not url and bbl_href:
            url = safe_link(bbl_href[1])
        pieces = raw.replace(r"\urlprefix", "").split(r"\newblock")
        if len(pieces) < 3:
            raise ValueError(f"Unexpected bibliography format: {key}")
        authors, title = (plain_latex(piece) for piece in pieces[:2])
        venue_parts = [re.sub(r"\\url\{[^}]+\}", "", part).lstrip(" ,") for part in pieces[2:]]
        venue = plain_latex(" ".join(venue_parts))
        if not authors or not title or not venue or any("\\" in s for s in (authors,title,venue)):
            raise ValueError(f"Incomplete or unconverted reference: {key}")
        assigned = " ".join(chapter for chapter in chapters if number in sections[chapter])
        source_link = (' <a class="text-link" href="' + html.escape(url,quote=True)
                       + '" target="_blank" rel="noopener noreferrer">Source record</a>') if url else ""
        cards.append(f'<li id="ref-{number}" class="reference-entry" data-chapters="{assigned}" tabindex="-1">'
                     f'<span class="reference-id">[{number}]</span><div>'
                     f'<h2>{html.escape(title.rstrip("."))}</h2><p>{html.escape(authors)}</p>'
                     f'<p>{html.escape(venue)}{source_link}</p></div></li>')
        bibtex.append(f"@{kind}{{{key},\n  {body.rstrip()}\n}}")
    return cards, "\n\n".join(bibtex) + "\n"


def reference_page(chapters, cards):
    options = "".join(f'<option value="{n}">§{n} {html.escape(title)}</option>'
                      for n,title in chapters.items())
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="The numbered bibliography for the Feed-Forward 3D Scene Reconstruction survey.">
  <meta name="theme-color" content="#ffffff">
  <title>References · Feed-Forward 3D Survey</title>
  <link rel="stylesheet" href="site.css">
  <script type="module" src="references.mjs"></script>
</head>
<body id="top">
  <header class="site-header">
    <div class="wrap header-inner">
      <a class="wordmark" href="index.html"><span class="mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span> Feed-Forward 3D <span class="wordmark-kind">Survey</span></a>
      <nav aria-label="Main navigation"><a href="chapters.html">Chapters</a><a href="index.html#methods">Methods</a><a href="index.html#datasets">Datasets</a><a href="index.html#results">Results</a></nav>
    </div>
  </header>
  <main class="wrap guide references-guide">
    <h1>References</h1>
    <p>Browse the {len(cards)} references in the survey. The numbers follow the English manuscript. Select a chapter to see the works cited there.</p>
    <div class="controls reference-controls">
      <label class="search-label">Search references<input id="reference-query" type="search" placeholder="Title, author, year, or reference number" autocomplete="off"></label>
      <label>Chapter<select id="reference-chapter"><option value="">All chapters</option>{options}</select></label>
      <a class="button" href="data/references.bib" download>Download BibTeX</a>
    </div>
    <p id="reference-count" class="muted" role="status">{len(cards)} references</p>
    <ol class="reference-list">
      {chr(10).join(cards)}
    </ol>
  </main>
  <footer class="site-footer"><div class="wrap"><span>Feed-Forward 3D Scene Reconstruction · Survey companion</span><a href="#top">Back to top</a></div></footer>
</body>
</html>
"""


def add_chapter_links(file, sections):
    source = file.read_text(encoding="utf-8")
    source = re.sub(r'<details class="chapter-citations">.*?</details>', "", source, flags=re.S)

    def insert(match):
        n = match[2].replace("-", ".")
        numbers = sorted(sections[n])
        if not numbers:
            return match[0]
        links = " ".join(f'<a href="references.html#ref-{value}">[{value}]</a>' for value in numbers)
        extra = f'<details class="chapter-citations"><summary>Cited references ({len(numbers)})</summary><p>{links}</p></details>'
        return match[1] + extra + "</section>"

    source, count = re.subn(r'(<section id="section-([\d-]+)"[^>]*>.*?)</section>',
                            insert, source, flags=re.S)
    if not count:
        raise ValueError("No chapter guide entries available")
    file.write_text(source, encoding="utf-8")
    return count


def export(paper, dist):
    numbers = citation_numbers(paper / "build/main.aux")
    chapters, sections = section_citations(paper, numbers)
    cards, bibtex = bibliography(paper, numbers, chapters, sections)
    (dist / "references.html").write_text(reference_page(chapters, cards), encoding="utf-8")
    (dist / "data/references.bib").write_text(bibtex, encoding="utf-8")
    guide_entries = add_chapter_links(dist / "chapters.html", sections)
    print(f"{len(cards)} numbered references, {guide_entries} chapter guide entries checked.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("english_manuscript", type=Path)
    parser.add_argument("dist", type=Path)
    args = parser.parse_args()
    export(args.english_manuscript, args.dist)
