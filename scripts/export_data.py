"""Build the site datasets from the manuscript and measured result tables."""

import argparse
import ast
import csv
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

STUDY = "04_实验/数据清单/5.5_实验结果汇总"
MANUSCRIPT = "06_稿件/LaTeX"
PLOT = "05_图表/导出图片/5.5_实测配对图/绘图_质量与效率_4x4.py"
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}
SETTING_LABELS = {
    "G:calibrated": "3 views · known cameras",
    "G:rgb_no_pose": "3 views · unknown cameras",
    "N2": "2 views",
    "N6": "6 views",
    "A3": "3 views · geometry and pose",
    "A2-3": "3 views · FreeSplat",
    "A2-10": "10 views · FreeSplat",
    "P-G": "2 panoramas · geometry and pose",
    "P-NVS:native_erp": "Direct ERP input",
    "P-NVS:six_faces": "6-face adaptation",
}
METRIC_KEYS = (
    "accuracy_mm", "completeness_mm", "overall_mm", "accuracy_m", "completeness_m",
    "fscore_05m", "rotation_deg", "translation_deg", "auc_at_30_pct",
    "psnr_db", "ws_psnr_db", "ssim", "lpips", "gaussian_count",
    "depth_baseline_absrel", "depth_baseline_mae_m", "fusion_accuracy_m",
    "fusion_completeness_m", "fusion_fscore_05m", "median_total",
    "max_peak_allocated_gib", "system_params", "median_depth_prior_generation_s",
)
SOURCE_LABELS = {
    "G": "DTU",
    "N2": "RealEstate10K",
    "N6": "RealEstate10K",
    "A3": "ScanNet",
    "A2-3": "ScanNet",
    "A2-10": "ScanNet",
    "P-NVS": "Matterport3D",
    "P-G": "Matterport3D",
}


def export_csv(path, rows, keys):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def plain(value):
    value = value.replace(r"$\sim$", "≈").replace("$>$", ">")
    value = value.replace(r"\&", "&").replace(r"\pi^3", "π³").replace(r"\Omega", "Ω")
    value = value.replace(r"\textsuperscript{*}", "")
    for symbol in ("{", "}", "$"):
        value = value.replace(symbol, "")
    return " ".join(value.strip().split())


def key_name(value):
    return re.sub(r"[^a-z0-9π³ω]", "", plain(value).lower())


def safe_link(value):
    url = value.strip()
    parsed = urlsplit(url)
    return url if parsed.scheme in {"https", "http"} and parsed.hostname and "." in parsed.hostname else ""


def field(record, name):
    hit = re.search(r"^\s*" + name + r"\s*=\s*\{", record, re.M | re.I)
    if not hit:
        return ""
    level = 1
    for i in range(hit.end(), len(record)):
        if record[i] == "{":
            level += 1
        if record[i] == "}":
            level -= 1
        if level == 0:
            return record[hit.end():i].strip()
    raise ValueError(name)


def citation_numbers(aux_file):
    numbers = {key: int(number) for key, number in re.findall(
        r"^\\bibcite\{([^}]+)\}\{(\d+)\}",
        aux_file.read_text(encoding="utf-8-sig"), re.M,
    )}
    if sorted(numbers.values()) != list(range(1, len(numbers) + 1)) or not numbers:
        raise ValueError(f"Invalid or missing compiled citation numbers: {aux_file}")
    return numbers


def reference(bib, key, numbers):
    record = bib[key]
    doi = field(record, "doi")
    url = f"https://doi.org/{doi}" if doi else safe_link(field(record, "url"))
    return {
        "title": plain(field(record, "title")),
        "year": field(record, "year"),
        "venue": plain(field(record, "booktitle") or field(record, "journal")).removeprefix("the "),
        "paper": url,
        "reference_number": numbers[key],
    }


def method_classes(root):
    tree = ast.parse((root / PLOT).read_text(encoding="utf-8-sig"))
    entry = next(s for s in tree.body if isinstance(s, ast.Assign)
                 and any(isinstance(v, ast.Name) and v.id == "METHODS_BY_CLASS" for v in s.targets))
    by_group = ast.literal_eval(entry.value)
    found = {method: ROMAN[code] for code, methods in by_group.items() for method in methods}
    found.update(fus3d="III", panovggt="I", any3r="I", freesplat="IV", resplat="IV")
    return found


def methods_and_results(root, tex, bib, numbers):
    source = read_csv(root / STUDY / "主表_运行条件与指标.csv")
    chapter = tex.split("% BEGIN SECTION 5.5", 1)[1].split("% END SECTION 5.5", 1)[0]
    matches = re.findall(r"^\\LitClass\{lit\w+\}\{(.*?)\}\\LitRowRef\{lit\w+\}\{([^}]+)\}", chapter, re.M)
    cite = {key_name(label): key for label, key in matches}
    style = method_classes(root)
    display = {
        "pi3": "π³", "vggt-omega": "VGGT-Ω", "da3": "Depth Anything 3",
        "freesplat": "FreeSplat", "transplat": "TranSplat",
    }
    methods, results = {}, []
    for row in source:
        method = row["method"]
        setting, variant = row["setting"], row["variant"]
        name = display.get(method, row["method_name"])
        group = f"{setting}:{variant}" if setting in ("G", "P-NVS") else setting
        index = methods.setdefault(method, {
            "id": method,
            "name": name,
            "mechanism": style[method],
            "settings": [],
            "source": safe_link(row["author_source"]),
            **reference(bib, cite[key_name(name)], numbers),
        })
        dataset = SOURCE_LABELS[setting]
        label = f"{dataset} · {SETTING_LABELS[group]}"
        if label not in index["settings"]:
            index["settings"].append(label)
        if not index["paper"]:
            index["paper"] = index["source"]
        result = {
            "id": method, "name": name, "mechanism": style[method],
            "dataset": dataset, "group": group, "setup": SETTING_LABELS[group],
            "views": int(row["source_views"]), "targets": int(row["target_views"]),
            "samples": int(row["valid_samples"]),
            "reference_number": index["reference_number"],
        }
        for key in METRIC_KEYS:
            value = row[key].strip()
            if value:
                result[key] = float(value)
        results.append(result)
    assert len(methods) == 63 and len(results) == 77 and sum(r["samples"] for r in results) == 1025
    return sorted(methods.values(), key=lambda x: x["name"].casefold()), results


def datasets(tex, bib, numbers):
    table = tex.split(r"\label{tab:datasets-benchmarks}", 1)[1].split(r"\end{longtable}", 1)[0]
    current, rows = "", []
    for line in table.splitlines():
        group = re.match(r"\\multicolumn\{4\}\{@\{\}l@\{\}\}\{\\textbf\{([^}]+)\}\}", line)
        if group:
            current = group[1]
        row = re.match(r"(.+?)~\\cite\{([^}]+)\} & (.+?) & (.+?) & (.+?) \\\\", line)
        if not row:
            continue
        name, keys, size, observed, target = row.groups()
        observations = plain(observed)
        flags = [label for token, label in
                 (("ERP", "ERP"), ("fisheye", "Fisheye"), ("rgb-d", "RGB-D"),
                  ("perspective", "Perspective"), ("lidar", "LiDAR"), ("3d assets", "3D assets"))
                 if token.casefold() in observations.casefold()]
        origin = "Rendered observations" if re.search("rendered|synthetic|procedural|simulated", observed, re.I) else ""
        refs = [reference(bib, key.strip(), numbers) for key in keys.split(",")]
        rows.append(dict(name=plain(name), domain=current, scale=plain(size),
                         observations=observations, reference=plain(target),
                         projection=flags, origin=origin,
                         paper=next((r["paper"] for r in refs if r["paper"]), ""),
                         reference_numbers=sorted({r["reference_number"] for r in refs})))
    assert len(rows) == 42 and all(row["domain"] for row in rows)
    return rows


def main(root, dist):
    data = dist / "data"
    data.mkdir(parents=True, exist_ok=True)
    entry = root / MANUSCRIPT
    tex = (entry / "sections/05_evaluation.tex").read_text(encoding="utf-8-sig")
    bib = dict(re.findall(r"^@\w+\{([^,]+),\s*(.*?)(?=^\})",
                          (entry / "references.bib").read_text(encoding="utf-8-sig"), re.M | re.S))
    numbers = citation_numbers(entry / "build/main.aux")
    methods, results = methods_and_results(root, tex, bib, numbers)
    library = datasets(tex, bib, numbers)
    snapshot = dict(
        methods=methods, datasets=library, results=results,
        counts={"methods":len(methods), "datasets":len(library), "settings":len(results),
                "evaluations":sum(row["samples"] for row in results)},
    )
    (data / "survey.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    export_csv(data / "results.csv", results, list(results[0])[:9]+list(METRIC_KEYS))
    inputs = read_csv(root / STUDY / "实际输入与评价帧.csv")
    export_csv(data / "inputs.csv", inputs, ["setting","method","sample","source_frames","target_frames","reference_baseline_m"])
    csv_fields = ["name", "domain", "scale", "observations", "reference", "paper"]
    export_csv(data / "datasets.csv", library, csv_fields)
    print(f"{len(methods)} methods, {len(library)} datasets, {len(results)} configurations, {len(inputs)} input records")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("survey_root", type=Path)
    parser.add_argument("dist", type=Path)
    args = parser.parse_args()
    main(args.survey_root, args.dist)
