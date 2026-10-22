"""Build the bundled disease browser from an NLM MeSH descriptor XML snapshot.

Offline build only: this script and the browser create no external connection.
Use desc2026.gz from https://www.nlm.nih.gov/databases/download/mesh.html.
MeSH tree placements are preserved, including levels beyond five. A descriptor
may have several placements; it remains one uniquely counted classification.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def build(source: Path) -> dict:
    terms = []
    placements = {}
    with gzip.open(source, "rb") as stream:
        for _, record in ET.iterparse(stream, events=("end",)):
            if record.tag != "DescriptorRecord":
                continue
            paths = sorted({
                item.text for item in record.findall("TreeNumberList/TreeNumber")
                if item.text and (
                    item.text.startswith("C") and not item.text.startswith("C22")
                    or item.text == "F03" or item.text.startswith("F03.")
                )
            })
            if paths:
                uid = record.findtext("DescriptorUI")
                name = record.findtext("DescriptorName/String")
                if not uid or not name:
                    raise ValueError("Missing MeSH identifier or name")
                aliases = sorted({
                    item.text for item in record.findall("ConceptList/Concept/TermList/Term/String")
                    if item.text and item.text != name
                })
                terms.append([uid, name, paths, aliases])
                for path in paths:
                    if path in placements:
                        raise ValueError(f"Duplicate tree placement: {path}")
                    placements[path] = uid
            record.clear()
    for path in placements:
        if "." in path and path.rsplit(".", 1)[0] not in placements:
            raise ValueError(f"Missing parent for {path}")
    levels = collections.Counter(len(path.split(".")) for path in placements)
    return {
        "version": "mesh-2026-disease-v1",
        "source": "NLM Medical Subject Headings (MeSH) 2026",
        "sourceUrl": "https://www.nlm.nih.gov/databases/download/mesh.html",
        "sourceFile": "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.gz",
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "coverage": "MeSH Diseases (C), excluding the Animal Diseases branch (C22), plus Mental Disorders (F03). Includes disease groups and related condition headings; not an FDA-monitored indication list or an exhaustive list of every human disease.",
        "uniqueCount": len(terms),
        "placementCount": len(placements),
        "levelCounts": [levels[i] for i in range(1, max(levels) + 1)],
        "terms": sorted(terms),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "new-platform/frontend/data/diseaseCatalog.json")
    args = parser.parse_args()
    catalog = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({key: catalog[key] for key in ("uniqueCount", "placementCount", "levelCounts", "sourceSha256")}))
