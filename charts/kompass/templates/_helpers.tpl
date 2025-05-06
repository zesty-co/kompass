{{/*
Helper Templates for Kompass Insights
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "kompass.name" -}}
  {{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "prefix.name" -}}
  {{- default "kompass" .Values.prefix | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "name" -}}
  {{- printf "%s-%s" (include "prefix.name" .) .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "kompass.fullname" -}}
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
{{- define "kompass.chart" -}}
  {{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "kube-state-metrics.serviceName" -}}
  {{- if .Values.kubeStateMetrics.enabled }}
    {{- .Values.kubeStateMetrics.fullnameOverride | trunc 63 | trimSuffix "-" }}
  {{- else }}
    {{- .Values.kubeStateMetrics.serviceName | trunc 63 | trimSuffix "-" }}
  {{- end }}
{{- end }}

{{- define "kompass.labels" -}}
helm.sh/chart: {{ include "kompass.chart" . }}
{{ include "kompass.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "kompass.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kompass.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}