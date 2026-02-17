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
  {{- if and .Values.kubeStateMetrics.enabled -}}
  {{- $ctx := dict "Values" .Values.kubeStateMetrics "Chart" .Chart "Release" .Release -}}
  {{- include "kube-state-metrics.selectorLabels" $ctx | trimPrefix " " -}}
  {{- end -}}
{{- end -}}

{{/*
Generate service name for Kube State Metrics (KSM)
- Use name from the KSM Helm Chart, only if the KSM is installed as part of this chart, otherwise use service name provided in `.Values.kubeStateMetrics.serviceName`
*/}}
{{- define "kompass.kube-state-metrics.serviceName" -}}
  {{- if .Values.kubeStateMetrics.enabled -}}
  {{- $ctx := dict "Values" .Values.kubeStateMetrics "Chart" .Chart "Release" .Release -}}
  {{- include "kube-state-metrics.fullname" $ctx -}}
  {{- else -}}
  {{- .Values.kubeStateMetrics.serviceName -}}
  {{- end -}}
{{- end }}

{{/*
Generate service namespace for Kube State Metrics (KSM)
- Use name from the KSM Helm Chart, only if the KSM is installed as part of this chart, otherwise use service namespace provided in `.Values.kubeStateMetrics.serviceNamespace`
*/}}
{{- define "kompass.kube-state-metrics.serviceNamespace" -}}
  {{- if .Values.kubeStateMetrics.enabled -}}
  {{- $ctx := dict "Values" .Values.kubeStateMetrics "Chart" .Chart "Release" .Release -}}
  {{- include "kube-state-metrics.namespace" $ctx -}}
  {{- else -}}
  {{- .Values.kubeStateMetrics.serviceNamespace -}}
  {{- end -}}
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

{{/*
Resolve a map workload value from global/component values.
Global values override component values for matching keys.
*/}}
{{- define "kompass.workload.resolveMap" -}}
{{- $global := default (dict) .global -}}
{{- $component := default (dict) .component -}}
{{- $key := .key -}}
{{- $globalHasKey := hasKey $global $key -}}
{{- $componentHasKey := hasKey $component $key -}}
{{- if and $globalHasKey $componentHasKey -}}
{{- $componentValue := default (dict) (index $component $key) -}}
{{- $globalValue := default (dict) (index $global $key) -}}
{{- toYaml (mergeOverwrite (deepCopy $componentValue) $globalValue) -}}
{{- else if $globalHasKey -}}
{{- toYaml (default (dict) (index $global $key)) -}}
{{- else if $componentHasKey -}}
{{- toYaml (default (dict) (index $component $key)) -}}
{{- else -}}
{{- toYaml (dict) -}}
{{- end -}}
{{- end -}}

{{/*
Resolve container securityContext from global/component values.
Global values override component values for matching keys.
Pod-only securityContext keys are removed from the resolved map.
*/}}
{{- define "kompass.workload.resolveContainerSecurityContext" -}}
{{- $resolved := include "kompass.workload.resolveMap" (dict "global" .global "component" .component "key" "securityContext") | fromYaml | default (dict) -}}
{{- $podOnlyKeys := list "fsGroup" "fsGroupChangePolicy" "supplementalGroups" "supplementalGroupsPolicy" "sysctls" -}}
{{- range $key := $podOnlyKeys -}}
{{- $_ := unset $resolved $key -}}
{{- end -}}
{{- toYaml $resolved -}}
{{- end -}}

{{/*
Resolve a list workload value from global/component values.
Global value takes precedence when set.
*/}}
{{- define "kompass.workload.resolveList" -}}
{{- $global := default (dict) .global -}}
{{- $component := default (dict) .component -}}
{{- $key := .key -}}
{{- $globalValue := default (list) (index $global $key) -}}
{{- $componentValue := default (list) (index $component $key) -}}
{{- if and (hasKey $global $key) (gt (len $globalValue) 0) -}}
{{- toYaml $globalValue -}}
{{- else if and (hasKey $component $key) (gt (len $componentValue) 0) -}}
{{- toYaml $componentValue -}}
{{- else -}}
{{- toYaml (list) -}}
{{- end -}}
{{- end -}}

{{/*
Resolve a bool workload value from global/component values.
Global value takes precedence and explicit false is preserved.
*/}}
{{- define "kompass.workload.resolveBool" -}}
{{- $global := default (dict) .global -}}
{{- $component := default (dict) .component -}}
{{- $key := .key -}}
{{- $globalValue := index $global $key -}}
{{- $componentValue := index $component $key -}}
{{- if and (hasKey $global $key) (ne $globalValue nil) -}}
{{- $globalValue | toJson -}}
{{- else if and (hasKey $component $key) (ne $componentValue nil) -}}
{{- $componentValue | toJson -}}
{{- else -}}
null
{{- end -}}
{{- end -}}

{{/*
Resolve a string workload value from global/component values.
Global value takes precedence when explicitly set.
*/}}
{{- define "kompass.workload.resolveString" -}}
{{- $global := default (dict) .global -}}
{{- $component := default (dict) .component -}}
{{- $key := .key -}}
{{- $globalValue := default "" (index $global $key) -}}
{{- $componentValue := default "" (index $component $key) -}}
{{- if and (hasKey $global $key) (not (empty $globalValue)) -}}
{{- $globalValue -}}
{{- else if and (hasKey $component $key) (not (empty $componentValue)) -}}
{{- $componentValue -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end -}}
