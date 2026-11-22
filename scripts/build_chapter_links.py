"""Create the clickable chapter boxes and the companion chapter index."""
import argparse
import html
import re
from pathlib import Path

import fitz

SECTION = re.compile(r"\(\s*§\s*(\d+(?:\.\d+){0,2})\s*\)")
SUMMARIES = {
    "1": "Introduces the scope of feed-forward 3D reconstruction and the classification by prediction unit.",
    "2": "Describes the inputs, intermediate features, 3D representations, and scene assembly shared by reconstruction pipelines.",
    "2.1": "Covers visual observations, camera information, and other geometry used as input to the model.",
    "2.2": "Explains how image features are extracted and combined across views.",
    "2.3": "Describes how features produce scene geometry and renderable representations.",
    "2.4": "Explains how partial reconstructions are aligned and fused into a scene.",
    "3": "Covers models whose predictions correspond to elements of the input views, such as pixels or patches.",
    "3.1": "Defines view-indexed predictions and the main ways to organize their outputs.",
    "3.2": "Describes the observations and geometric priors used by view-indexed models.",
    "3.3": "Explains how models associate observations across views and fuse the resulting features.",
    "3.4": "Compares direct coordinate regression with position construction from given or predicted geometry.",
    "3.5": "Describes outputs such as depth, point maps, and primitive attributes, along with their training supervision.",
    "3.6": "Reviews confidence prediction, filtering, and local refinement.",
    "3.7": "Discusses how predictions from multiple views are combined and how long sequences are reconstructed incrementally.",
    "4": "Covers spatial queries, regular-grid indexing, irregular 3D sets, and combinations of prediction mechanisms.",
    "4.1": "Covers conditional fields evaluated at query points or along rays to recover geometry or appearance.",
    "4.2": "Covers predictions associated with cells of a regular grid, including grid fields and grid-anchored primitives.",
    "4.3": "Covers the construction, generation, and refinement of irregular sets of 3D scene elements.",
    "4.4": "Explains how a model can use more than one prediction mechanism within a pipeline.",
    "4.4.1": "Describes sequential designs in which an earlier prediction informs a later stage.",
    "4.4.2": "Describes models that produce complementary predictions through multiple branches.",
    "4.5": "Compares the four mechanisms and relates their suitability to the reconstruction task and input conditions.",
    "5": "Groups the evidence by dataset, metric, comparison setting, and evaluation task.",
    "5.1": "Introduces datasets and benchmarks by observation type and available reference data.",
    "5.2": "Defines metrics for geometry, depth, pose, image synthesis, and computational cost.",
    "5.3": "Specifies input settings, reference data, alignment, and timing conditions used in the experiments.",
    "5.4": "Reviews performance reported in the literature under its original benchmark settings.",
    "5.5": "Presents measured comparisons on DTU, RealEstate10K, ScanNet, and Matterport3D.",
    "5.5.1": "Compares three-view surface reconstruction on 15 DTU scans, with camera conditions identified explicitly.",
    "5.5.2": "Compares synthesis quality and cost for two or six input views on RealEstate10K.",
    "5.5.3": "Evaluates three-view geometry and pose and includes a separate paired FreeSplat synthesis comparison.",
    "5.5.4": "Evaluates panoramic synthesis, geometry, and pose on Matterport3D, including direct ERP and six-face inputs.",
    "6": "Connects the survey to practical applications, current limitations, and directions for further research.",
    "6.1": "Reviews application settings and the reconstruction capabilities they require.",
    "6.2": "Discusses camera geometry, missing geometry, temporal consistency, cost, and cross-domain generalization.",
    "6.3": "Organizes future research into five directions covering geometry, completion, scale, efficiency, and robustness.",
    "6.3.1": "Considers how geometric constraints can improve consistency across observations.",
    "6.3.2": "Addresses the recovery of geometry where input coverage is incomplete.",
    "6.3.3": "Considers the maintenance of coherent geometry over long sequences and large scenes.",
    "6.3.4": "Considers how to allocate computation according to the available observations and the task.",
    "6.3.5": "Addresses stable reconstruction under changes in data, imaging conditions, and scene content.",
    "7": "Summarizes the survey and the trade-offs revealed by the mechanisms and evaluations.",
}
RELATED = {
    "3": ("Browse view-indexed methods", "index.html?mechanism=I#methods"),
    "4.1": ("Browse spatial-query methods", "index.html?mechanism=II#methods"),
    "4.2": ("Browse regular-grid methods", "index.html?mechanism=III#methods"),
    "4.3": ("Browse irregular-set methods", "index.html?mechanism=IV#methods"),
    "5.1": ("Open dataset index", "index.html#datasets"),
    "5.2": ("Open the evaluation guide", "evaluation.html"),
    "5.3": ("Open the evaluation guide", "evaluation.html"),
    "5.5": ("Open measured results", "index.html#results"),
    "5.5.1": ("Open DTU results", "index.html?benchmark=DTU#results"),
    "5.5.2": ("Open RealEstate10K results", "index.html?benchmark=RealEstate10K#results"),
    "5.5.3": ("Open ScanNet results", "index.html?benchmark=ScanNet#results"),
    "5.5.4": ("Open Matterport3D results", "index.html?benchmark=Matterport3D#results"),
}


def anchor(number):
    return "section-" + number.replace(".", "-")


def capture_boxes(page):
    pieces = SECTION.split(page.get_text())
    headings = {number: re.sub(r"-\s+", "-", " ".join(title.split()))
                for title, number in zip(pieces[::2], pieces[1::2])}
    rectangles = [shape["rect"] for shape in page.get_drawings()
                  if shape["type"] == "fs" and shape["rect"].height > 85
                  and shape["rect"].width > 120]
    result = {}
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            line_text = "".join(span["text"] for span in line["spans"])
            hit = SECTION.search(line_text)
            if not hit:
                continue
            center = (fitz.Rect(line["bbox"]).tl + fitz.Rect(line["bbox"]).br) / 2
            boxes = [rectangle for rectangle in rectangles if rectangle.contains(center)]
            if len(boxes) != 1 or hit[1] in result:
                raise ValueError("Ambiguous box for section " + hit[1])
            result[hit[1]] = (headings[hit[1]], boxes[0])
    if set(result) != set(SUMMARIES):
        raise ValueError("Missing or unrecognized figure sections")
    return dict(sorted(result.items(), key=lambda row: tuple(map(int, row[0].split(".")))))


def hotspots(records, bounds):
    for number, (title, rect) in records.items():
        x, y = 100 * rect.x0 / bounds.width, 100 * rect.y0 / bounds.height
        w = 100 * rect.width / bounds.width
        h = 100 * rect.height / bounds.height
        name = html.escape(f"§{number} {title}", quote=True)
        yield (f'<a class="map-link" href="chapters.html#{anchor(number)}" '
               f'aria-label="{name}" title="{name}" '
               f'style="--left:{x:.3f}%;--top:{y:.3f}%;--span:{w:.3f}%;--height:{h:.3f}%"></a>')


def guide(records):
    top_nav = "".join(f'<a href="#{anchor(n)}" title="{html.escape(title)}">§{n}</a>'
                      for n, (title, _) in records.items() if "." not in n)
    sections = []
    for n, (title, _) in records.items():
        depth = n.count(".")
        if depth == 0:
            if sections:
                sections.append("</article>")
            sections.append('<article class="chapter-block">')
        heading = depth + 2
        related = RELATED.get(n)
        action = f'<a class="text-link" href="{related[1]}">{related[0]}</a>' if related else ""
        sections.append(
            f'<section id="{anchor(n)}" class="chapter-entry level-{depth}">'
            f'<h{heading}><span>§{n}</span> {html.escape(title)}</h{heading}>'
            f'<p>{html.escape(SUMMARIES[n])}</p>{action}</section>'
        )
    sections.append("</article>")
    content = "\n      ".join(sections)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A chapter-by-chapter guide to the Feed-Forward 3D Scene Reconstruction survey.">
  <title>Chapter Guide · Feed-Forward 3D Survey</title>
  <link rel="stylesheet" href="site.css">
</head>
<body>
  <header class="site-header">
    <div class="wrap header-inner">
      <a class="wordmark" href="index.html">Feed-Forward 3D <span class="wordmark-kind">Survey</span></a>
      <nav aria-label="Main navigation"><a href="index.html#overview">Overview</a><a href="index.html#methods">Methods</a><a href="index.html#results">Results</a></nav>
    </div>
  </header>
  <main class="wrap guide chapter-guide">
    <h1>Chapter guide</h1>
    <p>Select a chapter below, or use the boxes in the <a href="index.html#survey-figure">survey outline</a>. The headings and numbering follow the paper.</p>
    <nav class="chapter-nav" aria-label="Chapters">{top_nav}</nav>
    <div class="chapter-content">
      {content}
    </div>
  </main>
</body>
</html>
"""


def build(dist, site_url):
    figure = dist / "media/survey-outline.pdf"
    mark = dist / "media/survey-outline-linked.pdf"
    with fitz.open(figure) as pdf:
        page = pdf[0]
        records = capture_boxes(page)
        overlay = "\n".join("            " + a for a in hotspots(records, page.rect))
        for number, (_, rect) in records.items():
            page.insert_link({"kind": fitz.LINK_URI, "from": rect,
                              "uri": site_url.rstrip("/") + "/chapters.html#" + anchor(number)})
        pdf.save(mark, garbage=4, deflate=True)
    with fitz.open(mark) as output:
        if len(output[0].get_links()) != len(records):
            raise ValueError("Missing PDF link regions")
    index = dist / "index.html"
    html_text = index.read_text(encoding="utf-8")
    start, end = "<!-- chapter-links:start -->", "<!-- chapter-links:end -->"
    pattern = re.escape(start) + r".*?" + re.escape(end)
    html_text, count = re.subn(pattern, start + "\n" + overlay + "\n            " + end, html_text, flags=re.S)
    if count != 1:
        raise ValueError("Cannot locate the chapter map")
    index.write_text(html_text, encoding="utf-8")
    (dist / "chapters.html").write_text(guide(records), encoding="utf-8")
    print(f"Created {len(records)} links for the image and PDF, with matching guide entries.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument("site_url", help="Origin of the deployed companion")
    args = parser.parse_args()
    build(args.dist, args.site_url)
