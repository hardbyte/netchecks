#!/bin/bash
# Generates the /manifests/deploy.yaml

if [ -n "$DEBUG" ]; then
	set -x
fi

#set -o errexit
set -o nounset
set -o pipefail


cd $(dirname "${BASH_SOURCE}") && pwd -P

MANIFEST=manifests/deploy.yaml

helm template netchecks-operator ./charts/netchecks \
  --values examples/kind-installation/values.yaml \
  --namespace netchecks \
  > $MANIFEST

sed -i.bak '/app.kubernetes.io\/managed-by: Helm/d' $MANIFEST
sed -i.bak '/helm.sh/d' $MANIFEST

