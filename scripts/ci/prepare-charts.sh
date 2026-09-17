#!/bin/sh
set -eu

[ "$#" -eq 1 ] || { echo 'usage: prepare-charts.sh OUTPUT_DIRECTORY' >&2; exit 2; }
script_dir="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
source_charts="${CHARTS_DIR:-$script_dir/../../charts}"
workspace="$1"
[ ! -e "$workspace" ] || { echo "Output already exists: $workspace" >&2; exit 1; }
mkdir -p "$workspace"
cp -R "$source_charts/." "$workspace/"
temporary="$(mktemp -d)"
# Do not read or update repositories configured by another job on a shared runner.
export HELM_REPOSITORY_CONFIG="$temporary/repositories.yaml"
export HELM_REPOSITORY_CACHE="$temporary/repository-cache"
cleanup() {
  if [ -f "$temporary/Chart.yaml" ]; then
    cp "$temporary/Chart.yaml" "$workspace/kompass/Chart.yaml"
    # The temporary lock contains file:// URLs and cannot accompany public metadata.
    rm -f "$workspace/kompass/Chart.lock"
  fi
  rm -rf "$temporary"
}
trap cleanup 0
trap 'exit 129' 1
trap 'exit 130' 2
trap 'exit 143' 15

cp "$workspace/kompass/Chart.yaml" "$temporary/Chart.yaml"
for child in kompass-insights kompass-pod-placement pod-rightsizing; do
  # Before the first rightsizing promotion, its existing remote dependency still works.
  [ -f "$workspace/$child/Chart.yaml" ] || continue
  CHILD="$child" yq eval -e '.name == strenv(CHILD)' "$workspace/$child/Chart.yaml" >/dev/null
  CHILD="$child" yq eval -i \
    '(.dependencies[] | select(.name == strenv(CHILD))).repository = "file://../" + strenv(CHILD)' \
    "$workspace/kompass/Chart.yaml"
done

# Register remaining external repositories, including dependencies of subcharts.
# Local children need no published package or repository index entry.
: > "$temporary/repositories"
for chart_file in "$workspace/"*/Chart.yaml; do
  yq eval -r '.dependencies[]?.repository // ""' "$chart_file" >> "$temporary/repositories"
done
LC_ALL=C sort -u "$temporary/repositories" > "$temporary/sorted-repositories"
repository_number=0
while IFS= read -r repository; do
  case "$repository" in
    https://*|http://*)
      repository_number=$((repository_number + 1))
      helm repo add "kompass-ci-$repository_number" "$repository"
      ;;
    ''|file://*|oci://*) ;;
    *) echo "Unsupported Helm repository: $repository" >&2; exit 1 ;;
  esac
done < "$temporary/sorted-repositories"

# Package child dependencies first so their archives are included in the umbrella.
for chart_file in "$workspace/"*/Chart.yaml; do
  chart_path="${chart_file%/Chart.yaml}"
  [ "${chart_path##*/}" != kompass ] || continue
  helm dependency update "$chart_path" --skip-refresh
done
helm dependency update "$workspace/kompass" --skip-refresh
# cleanup restores the original public Chart.yaml while retaining built dependencies.
