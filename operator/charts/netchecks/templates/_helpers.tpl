{{/*
Expand the name of the chart.
*/}}
{{- define "netchecks.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "netchecks.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "netchecks.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "netchecks.labels" -}}
helm.sh/chart: {{ include "netchecks.chart" . }}
{{ include "netchecks.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "netchecks.selectorLabels" -}}
app.kubernetes.io/name: {{ include "netchecks.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use for the operator
*/}}
{{- define "netchecks.serviceAccountName" -}}
{{- if .Values.operator.serviceAccount.create }}
{{- default (include "netchecks.fullname" .) .Values.operator.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.operator.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Whether CRDs should be installed by this chart.

Honors the legacy `installCRDs` value as an alias for `crds.install`. That value was
documented but had no effect while the CRDs lived in the chart's `crds/` directory,
which Helm never templates.
*/}}
{{- define "netchecks.crds.install" -}}
{{- $install := .Values.crds.install -}}
{{- if hasKey .Values "installCRDs" -}}
{{- $install = and $install .Values.installCRDs -}}
{{- end -}}
{{- if $install -}}true{{- end -}}
{{- end }}

{{/*
Extra annotations applied to the CRDs managed by this chart.
*/}}
{{- define "netchecks.crds.annotations" -}}
{{- if .Values.crds.keep -}}
helm.sh/resource-policy: keep
{{- end -}}
{{- end }}
