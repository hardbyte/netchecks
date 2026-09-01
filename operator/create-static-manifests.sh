#!/bin/bash
# Generates the /manifests/deploy.yaml

if [ -n "$DEBUG" ]; then
  set -x
fi

#set -o errexit
set -o nounset
set -o pipefail

cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P

MANIFEST="manifests/deploy.yaml"

helm dependency build ./charts/netchecks

# crds.keep=false: the `helm.sh/resource-policy: keep` annotation only matters
# for Helm-managed releases; rendering without it avoids leaving an empty
# `annotations:` key behind once the sed below strips helm.sh lines.
helm template netchecks-operator ./charts/netchecks \
  --values examples/kind-installation/values.yaml \
  --set crds.keep=false \
  --namespace netchecks \
  > "${MANIFEST}"

sed -i.bak '/app.kubernetes.io\/managed-by: Helm/d' "${MANIFEST}"
sed -i.bak '/helm.sh/d' "${MANIFEST}"
rm -f "${MANIFEST}.bak"
