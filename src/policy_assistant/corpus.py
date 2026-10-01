"""Load the frozen corpus. One retrieval unit = one numbered handbook clause."""
import json
import re
from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "corpus"
_CLAUSE = re.compile(r"^\[(D\d\d-[A-Z]?[\d.]+)\] (.+)$")


@dataclass(frozen=True)
class Clause:
    id: str          # e.g. "D07-5.1"
    doc_id: str      # e.g. "D07"
    doc_title: str   # e.g. "Chapter 7 — Leave"
    section: str     # e.g. "5 Marriage leave and bereavement leave" ("" if none)
    text: str
    source: str
    version: str     # document date shown to the user (G4 provenance)

    @property
    def search_text(self):
        """Clause text with its chapter and section headings, so short clauses keep their context."""
        return " | ".join(x for x in (self.doc_title, self.section, self.text) if x)

    @property
    def provenance(self):
        return f"{self.source}, {self.version} — {self.doc_title}, clause {self.id}"


def load_corpus(corpus_dir=CORPUS_DIR):
    """Each file is '# chapter title', optional '## section' headings and '[clause-id] text' lines.
    Source name and document date are stored once, in MANIFEST.json."""
    corpus_dir = Path(corpus_dir)
    manifest = json.loads((corpus_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    clauses = []
    for path in sorted(corpus_dir.glob("D*.md")):
        title, section = "", ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                section = line[3:].strip()
            elif line.startswith("# "):
                title = line[2:].strip()
            else:
                m = _CLAUSE.match(line)
                if m:
                    clauses.append(Clause(m.group(1), path.stem, title, section, m.group(2),
                                          manifest["source"], manifest["version"]))
    if not clauses:
        raise FileNotFoundError(f"no clauses found in {corpus_dir}")
    return clauses
