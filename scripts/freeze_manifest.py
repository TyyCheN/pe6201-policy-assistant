"""Write or verify data/corpus/MANIFEST.json, the freeze record of the corpus.

    python scripts/freeze_manifest.py            # write the manifest (done once, at the freeze commit)
    python scripts/freeze_manifest.py --check    # verify that no corpus file has changed since
"""
import hashlib, json, re, sys
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "data" / "corpus"
CLAUSE = re.compile(r"^\[(D\d\d-[A-Z]?[\d.]+)\] (.+)$", re.M)


def build():
    docs = []
    for path in sorted(CORPUS.glob("D*.md")):
        text = path.read_text(encoding="utf-8")
        clauses = CLAUSE.findall(text)
        docs.append({"file": path.name, "title": re.search(r"^# (.+)$", text, re.M).group(1),
                     "clauses": len(clauses), "words": sum(len(t.split()) for _, t in clauses),
                     "sha256": hashlib.sha256(text.encode()).hexdigest()})
    return {"source": "Haida Co. Employee Handbook",
            "version": "October 2026 revision",
            "language": "English translation of the Chinese original",
            "documents": docs,
            "total_clauses": sum(d["clauses"] for d in docs),
            "total_words": sum(d["words"] for d in docs)}


if __name__ == "__main__":
    manifest, path = build(), CORPUS / "MANIFEST.json"
    if "--check" in sys.argv:
        frozen = json.loads(path.read_text(encoding="utf-8"))
        changed = [d["file"] for d, f in zip(manifest["documents"], frozen["documents"]) if d != f]
        same = manifest == frozen
        print("corpus unchanged since freeze" if same else f"CORPUS CHANGED: {changed or 'file list differs'}")
        sys.exit(0 if same else 1)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{manifest['total_clauses']} clauses, {manifest['total_words']} words, {len(manifest['documents'])} documents")
