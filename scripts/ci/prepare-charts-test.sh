#!/bin/sh
set -eu
script_dir="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' 0
source_charts="$temporary/source"
mkdir -p "$source_charts/kompass"
cat > "$source_charts/kompass/Chart.yaml" <<'YAML'
apiVersion: v2
name: kompass
version: 1.0.0
dependencies:
  - name: kompass-insights
    version: 1.0.0
    repository: https://unpublished.invalid/charts
  - name: kompass-pod-placement
    version: 1.0.0
    repository: https://unpublished.invalid/charts
  - name: pod-rightsizing
    alias: rightsizing
    version: v1.2.3
    repository: https://unpublished.invalid/charts
YAML
for child in admission kompass-insights kompass-pod-placement pod-rightsizing; do
  mkdir -p "$source_charts/$child/templates"
  version=1.0.0
  [ "$child" != pod-rightsizing ] || version=v1.2.3
  printf 'apiVersion: v2\nname: %s\nversion: %s\n' "$child" "$version" > "$source_charts/$child/Chart.yaml"
  cat > "$source_charts/$child/templates/configmap.yaml" <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}-{{ .Chart.Name }}
data:
  version: {{ .Chart.Version | quote }}
YAML
done
cat >> "$source_charts/kompass-insights/Chart.yaml" <<'YAML'
dependencies:
  - name: admission
    version: 1.0.0
    repository: file://../admission
YAML
cp -R "$source_charts" "$temporary/original"
CHARTS_DIR="$source_charts" sh "$script_dir/prepare-charts.sh" "$temporary/prepared"
# The fake public URL is unreachable: successful packaging proves local resolution.
diff -r "$temporary/original" "$source_charts"
cmp "$source_charts/kompass/Chart.yaml" "$temporary/prepared/kompass/Chart.yaml"
[ ! -f "$temporary/prepared/kompass/Chart.lock" ]
[ -f "$temporary/prepared/kompass/charts/pod-rightsizing-v1.2.3.tgz" ]
helm lint "$temporary/prepared/kompass"
helm template test "$temporary/prepared/kompass" > "$temporary/rendered.yaml"
grep -q 'name: test-rightsizing' "$temporary/rendered.yaml"
grep -q 'name: test-admission' "$temporary/rendered.yaml"
helm package "$temporary/prepared/kompass" --destination "$temporary/packages"
mkdir "$temporary/unpacked"
tar -xzf "$temporary/packages/kompass-1.0.0.tgz" -C "$temporary/unpacked"
yq -e '[.dependencies[].repository] | all_c(. == "https://unpublished.invalid/charts")' \
  "$temporary/unpacked/kompass/Chart.yaml" >/dev/null
[ ! -f "$temporary/unpacked/kompass/Chart.lock" ]

# The scripts can land before rightsizing itself is introduced.
yq -i 'del(.dependencies[] | select(.name == "pod-rightsizing"))' "$source_charts/kompass/Chart.yaml"
rm -rf "$source_charts/pod-rightsizing"
CHARTS_DIR="$source_charts" sh "$script_dir/prepare-charts.sh" "$temporary/before-migration"
cmp "$source_charts/kompass/Chart.yaml" "$temporary/before-migration/kompass/Chart.yaml"
helm lint "$temporary/before-migration/kompass"

# Never silently package a local version that does not satisfy the umbrella pin.
yq -i '(.dependencies[] | select(.name == "kompass-insights")).version = "9.9.9"' "$source_charts/kompass/Chart.yaml"
if CHARTS_DIR="$source_charts" sh "$script_dir/prepare-charts.sh" "$temporary/mismatch" > "$temporary/mismatch.log" 2>&1; then
  echo 'Mismatched local dependency version unexpectedly accepted.' >&2
  exit 1
fi
cmp "$source_charts/kompass/Chart.yaml" "$temporary/mismatch/kompass/Chart.yaml"
[ ! -f "$temporary/mismatch/kompass/Chart.lock" ]

echo 'Local chart preparation tests passed'
