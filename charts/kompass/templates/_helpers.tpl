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

{{- define "kompass.kube-state-metrics.selectorLabels" -}}
  {{- $ctx := dict "Values" .Values.kubeStateMetrics "Chart" .Chart "Release" .Release -}}
  {{- include "kube-state-metrics.selectorLabels" $ctx | trimPrefix " " -}}
{{- end -}}

{{- define "kompass.kube-state-metrics.serviceName" -}}
  {{- $ctx := dict "Values" .Values.kubeStateMetrics "Chart" .Chart "Release" .Release -}}
  {{- include "kube-state-metrics.fullname" $ctx -}}
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

{{- define "kompass.scrapeInterval" -}}
{{- default "30s" .Values.victoriaMetricsAgent.scrapeInterval -}}
{{- end }}

{{- define "kompass.scrapeIntervalLong" -}}
{{- default "1m" .Values.victoriaMetricsAgent.scrapeIntervalLong -}}
{{- end }}

{{- define "kompass.scrapeIntervalVolume" -}}
{{- default "600s" .Values.victoriaMetricsAgent.scrapeIntervalVolume -}}
{{- end }}

{{/*
Create the name of the recommendations-maker
*/}}
{{- define "rightsizing.recommendationsMaker.name" -}}
{{/* Capture the parent context ('.') passed to this helper */}}
{{- $parentContext := . -}}
{{/* Extract the 'recommendationsMaker' specific values from the 'rightsizing' section of the parent's values */}}
{{- $makerValues := $parentContext.Values.rightsizing.recommendationsMaker -}}

{{/* Initialize an empty dictionary to build the context for the 'name' sub-helper */}}
{{- $nameHelperContext := dict -}}

{{/* Attempt to retrieve the 'rightsizing' subchart object from the parent's .Subcharts */}}
{{- $rightsizingSubchart := get $parentContext.Subcharts "rightsizing" -}}

{{/*
  Determine the .Chart and .Values for the 'name' sub-helper.
  Prefer the subchart's .Chart and .Values if the subchart is present and properly loaded.
  Otherwise, fall back to the parent chart's .Chart and .Values.
  This ensures 'include "name"' behaves as if called from within the subchart's scope when possible.
*/}}
{{- if and $rightsizingSubchart $rightsizingSubchart.Chart $rightsizingSubchart.Values -}}
{{- $_ := set $nameHelperContext "Chart" $rightsizingSubchart.Chart -}}
{{- $_ := set $nameHelperContext "Values" $rightsizingSubchart.Values -}}
{{- else -}}
{{- $_ := set $nameHelperContext "Chart" $parentContext.Chart -}}
{{- $_ := set $nameHelperContext "Values" $parentContext.Values -}}
{{- end -}}

{{/* Add global Helm objects (.Release, .Capabilities) and parent .Name to the 'name' sub-helper's context */}}
{{- $_ := set $nameHelperContext "Release" $parentContext.Release -}}
{{- $_ := set $nameHelperContext "Capabilities" $parentContext.Capabilities -}}
{{- $_ := set $nameHelperContext "Name" $parentContext.Name -}}

{{/*
  Call the 'name' helper (expected to be defined in the rightsizing subchart, or a common library)
  using the constructed context. Trim any leading/trailing whitespace from its output.
  This $baseName is typically the chart name, like 'kompass' or 'pod-rightsizing'.
*/}}
{{- $baseName := include "name" $nameHelperContext | trim -}}

{{/*
  Construct the default full name for the recommendationsMaker component.
  This usually follows the pattern '<baseName>-<componentName>', e.g., 'pod-rightsizing-recommendations-maker'.
  The result is trimmed, truncated to 63 chars, and any trailing hyphen is removed.
*/}}
{{- $defaultFullName := printf "%s-%s" $baseName $makerValues.name | trim | trunc 63 | trimSuffix "-" -}}

{{/*
  Determine the final name:
  - Use 'recommendationsMaker.fullnameOverride' if provided in the values.
  - Otherwise, use the $defaultFullName constructed above.
  The final result is also trimmed to ensure cleanliness.
*/}}
{{- $makerValues.fullnameOverride | default $defaultFullName | trim -}}
{{- end -}}