# Feed-Forward 3D Scene Reconstruction — Survey Companion

An English-language static companion for the survey. It contains four prediction
mechanisms, 63 evaluated methods, 42 dataset entries and 77 measured configurations.

## Run locally

From this checkout:

    python -m http.server 8127 --directory dist

Open http://localhost:8127. The site uses browser-native HTML, CSS and JavaScript
with no build step.

## Contents

- dist/index.html shows the research outline, method and dataset indexes, measured
  results, and downloads.
- dist/evaluation.html explains the measurement groups and units.
- dist/chapters.html provides a target for each chapter and subsection in the
  outline. scripts/build_chapter_links.py rebuilds the figure hotspots and
  linked PDF from the vector outline. Invoke it with dist and the deployed
  site's origin so PDF links resolve to the chapter guide.
- dist/references.html lists the numbered manuscript references and includes
  a BibTeX download. After compiling the English manuscript, run
  scripts/export_references.py with its LaTeX directory and dist. This updates
  the bibliography, chapter filters, and chapter-guide links. Re-run
  scripts/export_data.py to refresh the corresponding method, dataset, and
  measurement reference numbers.
- dist/data/ contains a whitelisted result summary, dataset directory and exact
  scene/frame index manifest. Inputs and checkpoints are referenced through their
  author sources.
- scripts/export_data.py rebuilds the website data from the survey LaTeX and
  measurement files. Invoke it with the survey workspace root and this project's
  dist directory as the two positional arguments.

The result summary represents the measured runs in §5.5. F-scores are stored as
fractions, AUC values as percentages, times in seconds, and parameter counts as
counts. Click “Download this setup” for a CSV in the same units as the result table.
The exported project does not need the full survey workspace to run.

## Static hosting

The [published companion website](https://ff3d-reconstruction.github.io/) is served from the `gh-pages` branch.

Use dist as the publishing directory. For GitHub Pages, publish the dist contents
from a dedicated branch or upload this directory with the official Pages actions.
The site uses relative URLs. Replace the working title-only BibTeX with the final
author and publication record when it becomes available.

## License and attribution

The MIT license covers the website implementation. The survey diagrams, factual
measurement summary and cited third-party material keep their respective
provenance. See ATTRIBUTION.md for details.

DeepSeek drafted the table filter, sort, and CSV-export helper, which is integrated
and checked as dist/table-tools.mjs.
