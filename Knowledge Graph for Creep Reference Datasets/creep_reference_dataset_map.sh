#!/usr/bin/env bash

set -euo pipefail

# --- paths --------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JSON_DIR="$REPO_ROOT/JSON datasets"
MAPPING_YML="$REPO_ROOT/creep_reference_dataset_mapping.yml"
OUTPUT_TTL="$REPO_ROOT/creep_reference_dataset_rdf.ttl"
CTO_TTL="$REPO_ROOT/cto.ttl"

WORK_DIR="$REPO_ROOT/.rml_work"
NPM_DIR="$WORK_DIR/npm"
PARTS_DIR="$WORK_DIR/parts"
RML_TTL="$WORK_DIR/creep_reference_dataset_rml.ttl"
STAGED_JSON="$WORK_DIR/current.json"
SHAPES_DIR="$REPO_ROOT/shape"

log() { echo "[creep-map] $*" >&2; }
die() { echo "[creep-map] ERROR: $*" >&2; exit 1; }

[[ -f "$MAPPING_YML" ]] || die "mapping file not found: $MAPPING_YML"
[[ -d "$JSON_DIR" ]]    || die "\"JSON datasets\" folder not found next to this script"
[[ -f "$CTO_TTL" ]]     || log "warning: cto.ttl not found at repo root (mapping still runs, but IRIs won't resolve locally)"

mkdir -p "$WORK_DIR" "$PARTS_DIR"
rm -f "$PARTS_DIR"/*.nt

# --- 0. check / install tooling -----------------------------------------
command -v node >/dev/null 2>&1 || die "node is required (https://nodejs.org)"
command -v npm  >/dev/null 2>&1 || die "npm is required (comes with node)"
command -v python3 >/dev/null 2>&1 || die "python3 is required"
command -v jq >/dev/null 2>&1 || die "jq is required (e.g. 'brew install jq' / 'apt install jq')"

if [[ ! -x "$NPM_DIR/node_modules/.bin/yarrrml-parser" ]]; then
  log "installing @rmlio/yarrrml-parser (one-time, into .rml_work/npm) ..."
  mkdir -p "$NPM_DIR"
  npm install --prefix "$NPM_DIR" @rmlio/yarrrml-parser >/dev/null 2>&1 \
    || die "failed to install @rmlio/yarrrml-parser via npm"
fi
YARRRML_PARSER="$NPM_DIR/node_modules/.bin/yarrrml-parser"

python3 -c "import morph_kgc" >/dev/null 2>&1 || {
  log "installing morph-kgc (one-time RML engine, pure Python) ..."
  pip3 install --user --break-system-packages -q morph-kgc 2>/dev/null \
    || pip3 install --user -q morph-kgc \
    || die "failed to install morph-kgc via pip"
}
python3 -c "import rdflib" >/dev/null 2>&1 || {
  pip3 install --user --break-system-packages -q "rdflib>=6.1.1,<7.3.0" 2>/dev/null \
    || pip3 install --user -q "rdflib>=6.1.1,<7.3.0" \
    || die "failed to install rdflib via pip"
}
python3 -c "import pyshacl" >/dev/null 2>&1 || {
  log "installing pyshacl (one-time SHACL validator) ..."
  pip3 install --user --break-system-packages -q pyshacl 2>/dev/null \
    || pip3 install --user -q pyshacl \
    || die "failed to install pyshacl via pip"
}

# --- 1. compile YARRRML -> RML (once per run; mapping is static) --------
log "compiling YARRRML mapping to RML ..."
"$YARRRML_PARSER" -i "$MAPPING_YML" -o "$RML_TTL" >/dev/null 2>&1 \
  || die "yarrrml-parser failed to compile $MAPPING_YML"

# --- 2. stage + map every JSON dataset -----------------------------------
# jq adds the small helper fields the mapping relies on:
#   _fileID  - stable id derived from the file name (used to build every IRI)
#   _idx     - row index, only added inside chemicalCompositionMeasured[]
read -r -d '' JQ_FILTER <<'JQ_EOF' || true
  .MeasurementData._fileID = $fid
  | .MeasurementData.AdditionalMetadata.TestPiece._fileID = $fid
  | .MeasurementData.AdditionalMetadata.TestInfo.testParameters._fileID = $fid
  | .MeasurementData.AdditionalMetadata.TestInfo.testJobDetails._fileID = $fid
  | .MeasurementData.AdditionalMetadata.TestInfo.relatedResearchOutcome.relatedArticle |=
      ((. // []) | to_entries | map(.value + {_fileID: $fid, _idx: (.key | tostring)}))
  | .MeasurementData.AdditionalMetadata.DataProcessingProcedures._fileID = $fid
  | .MeasurementData.AdditionalMetadata.MaterialHistoryAndCondition._fileID = $fid
  | .MeasurementData.AdditionalMetadata.MaterialHistoryAndCondition.chemicalComposition |=
      ((. // []) | map(
          .chemicalCompositionMeasured |=
            ((. // []) | to_entries | map(.value + {_fileID: $fid, _idx: (.key | tostring)}))
        ))
  | .MeasurementData.AdditionalMetadata.MeasuringAndTestEquipment.testMachine._fileID = $fid
  | .MeasurementData.AdditionalMetadata.MeasuringAndTestEquipment.extensionValues.contactingExtensometer._fileID = $fid
  | .MeasurementData.PrimaryData.TestResult.valuesRecordedAfterTestEnd._fileID = $fid
  | .MeasurementData.PrimaryData.TestResult.valuesRecordedAtTestStart._fileID = $fid
  | .MeasurementData.PrimaryData.TestResult.valuesRecordedDuringTestRun._fileID = $fid
  | .MeasurementData.SecondaryData.TestResult.elongationValues._fileID = $fid
  | .MeasurementData.SecondaryData.TestResult.extensionValues._fileID = $fid
JQ_EOF

shopt -s nullglob
json_files=("$JSON_DIR"/*.json)
shopt -u nullglob
[[ ${#json_files[@]} -gt 0 ]] || die "no .json files found in \"JSON datasets\""

count=0
for f in "${json_files[@]}"; do
  base="$(basename "$f" .json)"
  # file-name-derived, idempotent identifier (safe for use in an IRI)
  fid="$(printf '%s' "$base" | sed -E 's/[^A-Za-z0-9_.-]/_/g')"

  log "mapping: $base"
  jq --arg fid "$fid" "$JQ_FILTER" "$f" > "$STAGED_JSON" \
    || die "jq staging failed for $f"

  cfg="$WORK_DIR/morph_config.ini"
  cat > "$cfg" <<CFG_EOF
[CONFIGURATION]
output_file = $PARTS_DIR/$fid.nt
output_format = N-TRIPLES
na_values = ,nan,Not applicable

[DataSource1]
mappings: $RML_TTL
CFG_EOF

  # run from REPO_ROOT: the compiled RML mapping references the staged JSON source via the relative path ".rml_work/current.json"
  ( cd "$REPO_ROOT" && python3 -m morph_kgc "$cfg" ) \
    || die "morph-kgc mapping failed for $f"

  count=$((count + 1))
done
log "mapped $count JSON dataset(s)"

# --- 3. merge + de-duplicate all parts into one turtle file --------------
log "merging and de-duplicating triples into $(basename "$OUTPUT_TTL") ..."
python3 - "$OUTPUT_TTL" "$PARTS_DIR" <<'PY_EOF'
import sys, glob, os
from rdflib import Graph, Namespace

out_path, parts_dir = sys.argv[1], sys.argv[2]

g = Graph()
g.bind("msekg", Namespace("https://nfdi.fiz-karlsruhe.de/matwerk/msekg/"))
g.bind("cto", Namespace("https://w3id.org/pmd/cto/"))
g.bind("pmdco", Namespace("https://w3id.org/pmd/co/"))
g.bind("mwo", Namespace("http://purls.helmholtz-metadaten.de/mwo/"))
g.bind("tto", Namespace("https://w3id.org/pmd/tto/"))
g.bind("obo", Namespace("http://purl.obolibrary.org/obo/"))
g.bind("unit", Namespace("http://qudt.org/vocab/unit/"))
g.bind("qudt", Namespace("http://qudt.org/schema/qudt/"))
g.bind("dcterms", Namespace("http://purl.org/dc/terms/"))

n_files = 0
for nt_file in sorted(glob.glob(os.path.join(parts_dir, "*.nt"))):
    if os.path.getsize(nt_file) == 0:
        continue
    g.parse(nt_file, format="nt")
    n_files += 1

g.serialize(destination=out_path, format="turtle")
print(f"[creep-map] merged {n_files} part file(s) -> {len(g)} unique triples", file=sys.stderr)
PY_EOF

# --- 4. validate against the SHACL shapes in ./shape ---------------------
if [[ -d "$SHAPES_DIR" ]] && compgen -G "$SHAPES_DIR"/*.ttl >/dev/null; then
  log "validating $(basename "$OUTPUT_TTL") against SHACL shapes in $(basename "$SHAPES_DIR")/ ..."
  python3 - "$OUTPUT_TTL" "$SHAPES_DIR" <<'PY_EOF' || log "warning: SHACL validation reported violations (see report above)"
import sys, glob
from rdflib import Graph
from pyshacl import validate

data_path, shapes_dir = sys.argv[1], sys.argv[2]

data = Graph()
data.parse(data_path, format="turtle")

shapes = Graph()
for f in sorted(glob.glob(shapes_dir + "/*.ttl")):
    shapes.parse(f, format="turtle")

conforms, _, results_text = validate(
    data, shacl_graph=shapes, inference="none",
    abort_on_first=False, meta_shacl=False, advanced=True,
)
print(results_text, file=sys.stderr)
sys.exit(0 if conforms else 1)
PY_EOF
else
  log "no SHACL shapes found in $(basename "$SHAPES_DIR")/, skipping validation"
fi

log "done -> $OUTPUT_TTL"
