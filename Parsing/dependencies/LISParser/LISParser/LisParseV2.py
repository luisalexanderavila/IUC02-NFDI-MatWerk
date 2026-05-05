"""
LisParseV2.py - Parser for the new v2 LIS format (BAMDataset_v032026)

The v2 LIS format has the following header structure:
  CATEGORIZATION  ENTRY  ENTRY - ADDITIONAL INFORMATION  SYMBOL  UNIT  REQUIREMENT  INFORMATION  INFORMATION COMMON TO ALL (*)

Where CATEGORIZATION is a path like:
  Metadata --> Test info --> Test job details
  Primary data --> Test result --> Values recorded at test start

Each row corresponds to one metadata field. Multi-line values occur when a LIS
value is too long and continues on successive lines that do NOT start with a
recognized path (i.e. they lack the '--> ' pattern or are just continuation
text). The '*' in the last column marks data common to all experiments.

The parser detects the LIS schema version from the header row and handles
both old (v1) and new (v2) formats.
"""

import os
import re
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Column indices in the v2 tab-separated format ───────────────────────────
V2_COL_CATEGORY = 0   # Full path, "Metadata --> X --> Y"
V2_COL_ENTRY = 1      # Field name / entry label
V2_COL_SYMBOL = 3     # Symbol  (column 3 – after ENTRY-ADDITIONAL-INFO)
V2_COL_UNIT = 4       # Unit
V2_COL_REQUIREMENT = 5  # "Mandatory" / "Optional"
V2_COL_VALUE = 6      # Actual value
V2_COL_COMMON = 7     # "*" if common to all experiments

V2_HEADER_FIRST_TOKEN = "CATEGORIZATION"

# Path prefixes used in the v2 LIS file
_METADATA_PREFIX = "Metadata"
_METADATA_ALIAS_PREFIX = "additionalMetadata"
_PRIMARY_PREFIX = "Primary data"
_SECONDARY_PREFIX = "Secondary data"

_PATH_SEPARATOR = "-->"


def _is_v2_header(line: str) -> bool:
    """Return True if this line is the v2 column-header row."""
    return line.startswith(V2_HEADER_FIRST_TOKEN)


def _parse_path(category: str):
    """Split a path string like 'Metadata --> A --> B' into a list ['Metadata', 'A', 'B']."""
    return [p.strip() for p in category.split(_PATH_SEPARATOR)]


def _normalize_key(segment: str) -> str:
    """Normalize LIS path and entry labels for robust matching."""
    return segment.strip().casefold()


def _is_metadata_prefix(category_normalized: str) -> bool:
    return category_normalized.startswith(_normalize_key(_METADATA_PREFIX)) or category_normalized.startswith(
        _normalize_key(_METADATA_ALIAS_PREFIX)
    )


def _looks_like_continuation(line: str) -> bool:
    """
    Return True if the line appears to be a continuation of the previous
    multi-line value rather than a new LIS record.
    A new record starts with a recognised major section token followed by
    ' --> ', or is an empty line / comment.
    """
    if not line.strip():
        return False
    # A genuine new record always has a CATEGORIZATION token starting with a known prefix
    # and uses the --> separator.
    if _PATH_SEPARATOR in line and (
        line.startswith(_METADATA_PREFIX)
        or line.startswith(_METADATA_ALIAS_PREFIX)
        or line.startswith(_PRIMARY_PREFIX)
        or line.startswith(_SECONDARY_PREFIX)
    ):
        return False  # this is a new record
    return True  # treat as continuation


def _set_nested(d: dict, keys: list, value):
    """Set d[keys[0]][keys[1]]...[keys[-1]] = value, creating dicts as needed."""
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def _get_nested(d: dict, keys: list, default=None):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, {})
    return d if d != {} else default


class ParserV2:
    """
    Parser for BAM LIS files in the v2 (2026) metadata format.

    The parse_lis() method returns a dict with structure:
        {
            "filename": str,
            "lis_version": "v2",
            "schema_version": "2025-12",   # detected from filename / header
            "metadata": {                  # hierarchical dict mirroring LIS paths
                "Test info": {
                    "Test job details": {
                        "Date of test start": "...",
                        ...
                    },
                    ...
                },
                "Material history and condition": { ... },
                ...
            },
            "primary_data": { ... },       # hierarchical dict for "Primary data" section
            "secondary_data": { ... },     # hierarchical dict for "Secondary data" section
            "data": {                      # numeric time-series data
                "Elapsed time from end of loading": { "unit": "h", "values": [...] },
                ...
            }
        }
    """

    def __init__(self, filename: str, encoding: str = "auto"):
        self.filename = filename
        self.encoding = encoding
        self.file_lines = self._read_raw(filename)

    # ──────────────────────────────────────────────────
    # Reading
    # ──────────────────────────────────────────────────

    def _read_raw(self, filename: str):
        enc = self.encoding
        if enc == "auto":
            # LIS files in BAMDataset_v032026 (*-MD-TR.lis) are UTF-8 encoded;
            # older files may be latin1.  Try UTF-8 first, fall back silently.
            try:
                with open(filename, "r", encoding="utf-8") as fh:
                    lines = fh.readlines()
                self.encoding = "utf-8"
                return lines
            except UnicodeDecodeError:
                with open(filename, "r", encoding="latin1") as fh:
                    lines = fh.readlines()
                self.encoding = "latin1"
                return lines
        with open(filename, "r", encoding=enc) as fh:
            return fh.readlines()

    # ──────────────────────────────────────────────────
    # Version detection
    # ──────────────────────────────────────────────────

    def _detect_version(self):
        """
        Returns ('v2', schema_version_str) if the file follows the new format,
        ('v1', None) otherwise.
        """
        for line in self.file_lines[:5]:
            stripped = line.strip()
            if _is_v2_header(stripped):
                # Try to extract schema version from filename:
                # "Vh5205_C-78-MD-TR.lis" → "v032026" suggests schema 2025-12
                lower_path = self.filename.lower()
                basename = os.path.basename(self.filename).lower()
                schema_version = (
                    "2025-12"
                    if ("v032026" in lower_path or "032026" in lower_path or "2026" in basename)
                    else "unknown"
                )
                return "v2", schema_version
        return "v1", None

    # ──────────────────────────────────────────────────
    # Main parse
    # ──────────────────────────────────────────────────

    def parse_lis(self) -> dict:
        lis_version, schema_version = self._detect_version()

        if lis_version == "v2":
            return self._parse_v2(schema_version)
        else:
            logger.warning(
                "File does not appear to be v2 format; falling back to legacy parser."
            )
            from LISParser.LisParse import Parser
            legacy = Parser(self.filename, encoding=self.encoding)
            result = legacy.parse_lis()
            result["lis_version"] = "v1"
            result["schema_version"] = "2024-09"
            return result

    # ──────────────────────────────────────────────────
    # v2 parsing logic
    # ──────────────────────────────────────────────────

    def _parse_v2(self, schema_version: str) -> dict:
        lines = [l.rstrip("\n").rstrip("\r") for l in self.file_lines]

        result = {
            "filename": os.path.basename(self.filename),
            "lis_version": "v2",
            "schema_version": schema_version,
            "metadata": {},
            "primary_data": {},
            "secondary_data": {},
            "data": {},
        }

        # ── Find header line and skip it ──────────────────────────────
        header_idx = None
        for i, line in enumerate(lines):
            if _is_v2_header(line.strip()):
                header_idx = i
                break

        if header_idx is None:
            logger.error("No v2 header line found — cannot parse file.")
            return result

        # ── Find [data] section boundary ─────────────────────────────
        data_section_idx = None
        for i, line in enumerate(lines):
            if "[data]" in line.strip().lower():
                data_section_idx = i
                break

        metadata_end = data_section_idx if data_section_idx is not None else len(lines)

        # ── Parse metadata records (header_idx+1 … metadata_end) ─────
        i = header_idx + 1
        while i < metadata_end:
            line = lines[i]
            stripped = line.strip()

            # Skip blanks, separator lines, and lines with no content
            if not stripped or stripped.startswith("--") or not "\t" in line:
                i += 1
                continue

            cols = line.split("\t")

            category = cols[V2_COL_CATEGORY].strip() if len(cols) > V2_COL_CATEGORY else ""
            category_normalized = _normalize_key(category)

            # Only process lines that start with a known top-level path token
            if not (
                _is_metadata_prefix(category_normalized)
                or category_normalized.startswith(_normalize_key(_PRIMARY_PREFIX))
                or category_normalized.startswith(_normalize_key(_SECONDARY_PREFIX))
            ):
                i += 1
                continue

            # Determine which top-level bucket to use
            if category_normalized.startswith(_normalize_key(_PRIMARY_PREFIX)):
                top_bucket = "primary_data"
                path_parts = _parse_path(category)[1:]   # drop "Primary data"
            elif category_normalized.startswith(_normalize_key(_SECONDARY_PREFIX)):
                top_bucket = "secondary_data"
                path_parts = _parse_path(category)[1:]   # drop "Secondary data"
            else:
                top_bucket = "metadata"
                path_parts = _parse_path(category)[1:]   # drop "Metadata" or alias

            path_parts = [_normalize_key(part) for part in path_parts if part.strip()]

            entry = cols[V2_COL_ENTRY].strip() if len(cols) > V2_COL_ENTRY else ""
            entry = _normalize_key(entry)
            symbol = cols[V2_COL_SYMBOL].strip() if len(cols) > V2_COL_SYMBOL else ""
            unit = cols[V2_COL_UNIT].strip() if len(cols) > V2_COL_UNIT else ""
            requirement = cols[V2_COL_REQUIREMENT].strip() if len(cols) > V2_COL_REQUIREMENT else ""
            value = cols[V2_COL_VALUE].strip() if len(cols) > V2_COL_VALUE else ""
            common = cols[V2_COL_COMMON].strip() if len(cols) > V2_COL_COMMON else ""
            additional_info = cols[2].strip() if len(cols) > 2 else ""

            # ── Multi-line value handling ─────────────────────────────
            # Collect continuation lines that follow if they don't start a
            # new record and are not blank lines separating sections.
            j = i + 1
            while j < metadata_end:
                next_line = lines[j]
                next_stripped = next_line.strip()
                if not next_stripped:
                    break   # blank line → end of continuation
                if "\t" in next_line:
                    next_cols = next_line.split("\t")
                    next_cat = next_cols[V2_COL_CATEGORY].strip() if len(next_cols) > V2_COL_CATEGORY else ""
                    next_cat_normalized = _normalize_key(next_cat)
                    if _is_metadata_prefix(next_cat_normalized) \
                       or next_cat_normalized.startswith(_normalize_key(_PRIMARY_PREFIX)) \
                       or next_cat_normalized.startswith(_normalize_key(_SECONDARY_PREFIX)):
                        break  # a new record starts
                # continuation line — join with a space so multi-line values
                # become space-separated strings instead of newline-separated.
                if "\t" in next_line:
                    # Col[0] is the value fragment; a trailing "\t*" means
                    # the parent record is common-to-all.
                    candidate = next_cols[0].strip()
                    if next_cols[-1].strip() == "*":
                        common = "*"
                    if candidate:
                        value = value + " " + candidate
                else:
                    value = value + " " + next_stripped
                j += 1
            i = j   # advance outer loop past all continuation lines

            # ── Build record object ───────────────────────────────────
            value = value.strip()
            record = {
                "value": value,
                "unit": unit,
                "symbol": symbol,
                "requirement": requirement,
                "common": common == "*",
                "_additional_info": additional_info,
            }

            # Store under the full hierarchical path
            # path is: path_parts + [entry]
            if not entry:
                continue

            full_path = path_parts + [entry]
            # Navigate to parent to detect duplicate entry-label collisions.
            # When two rows share the same col[1] label (e.g. "k-Value") but differ in
            # col[2] additional info ("Lr = Lo" vs "Lr = Le"), append the normalised
            # col[2] to both keys so each is stored separately.
            _parent = result[top_bucket]
            for _k in path_parts:
                _parent = _parent.setdefault(_k, {})
            if entry in _parent and isinstance(_parent[entry], dict) and "value" in _parent[entry]:
                _existing = _parent[entry]
                _old_sfx = _normalize_key(_existing.get("_additional_info", ""))
                _new_sfx = _normalize_key(additional_info)
                _compound_old = (entry + " " + _old_sfx).strip() if _old_sfx else entry
                _compound_new = (entry + " " + _new_sfx).strip() if _new_sfx else entry
                _parent[_compound_old] = _parent.pop(entry)
                _parent[_compound_new] = record
            else:
                _set_nested(result[top_bucket], full_path, record)

        # ── Parse [data] section ──────────────────────────────────────
        if data_section_idx is not None:
            result["data"] = self._parse_data_section(lines, data_section_idx)

        self.json_content = result
        return result

    def _parse_data_section(self, lines: list, data_section_idx: int) -> dict:
        """Parse the tab-separated numeric time-series after [data]."""
        data_lines = lines[data_section_idx + 1:]

        # First non-empty line: column titles
        # Second non-empty line: symbols
        # Third non-empty line: units
        non_empty = [l for l in data_lines if l.strip()]
        if len(non_empty) < 3:
            return {}

        titles = [t.strip() for t in non_empty[0].split("\t")]
        symbols = [s.strip() for s in non_empty[1].split("\t")]
        units = [u.strip() for u in non_empty[2].split("\t")]

        data = {}
        for title, unit in zip(titles, units):
            if title:
                data[title] = {"unit": unit, "values": []}

        # Numeric rows start from index 3 in the non_empty list
        for line in non_empty[3:]:
            if not line.strip():
                continue
            raw_tokens = [tok.strip() for tok in line.split("\t")]
            values = []
            for tok in raw_tokens:
                if tok == "":
                    values.append(None)
                    continue
                tok = tok.replace(",", ".")
                try:
                    values.append(float(tok))
                except ValueError:
                    values.append(None)

            for title, val in zip(titles, values):
                if title in data:
                    data[title]["values"].append(val)

        return data

    # ──────────────────────────────────────────────────
    # Convenience: flat dict for mapping
    # ──────────────────────────────────────────────────

    def get_flat_metadata(self) -> dict:
        """
        Return a flat dict keyed by 'Section.Subsection.Field_name' and
        containing sub-dicts with 'value', 'unit', etc.
        This is the format consumed by the mapping/translation logic.
        """
        if not hasattr(self, "json_content"):
            self.parse_lis()

        flat = {}

        def _flatten(d: dict, prefix: str = ""):
            for k, v in d.items():
                normalized_k = _normalize_key(str(k))
                key = f"{prefix}.{normalized_k}" if prefix else normalized_k
                if isinstance(v, dict):
                    if "value" in v and set(v.keys()) - {"_additional_info"} <= {"value", "unit", "symbol", "requirement", "common"}:
                        # Leaf record
                        flat[key] = v
                    else:
                        _flatten(v, key)

        for section in ("metadata", "primary_data", "secondary_data"):
            _flatten(self.json_content.get(section, {}), section)

        return flat
