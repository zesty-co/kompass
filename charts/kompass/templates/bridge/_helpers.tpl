{{/*
Helper templates for the Kompass Bridge component.
*/}}

{{/*
Short component name.
*/}}
{{- define "kompass.bridge.name" -}}
kompass-bridge
{{- end -}}

{{/*
Fully qualified name for Bridge resources.
*/}}
{{- define "kompass.bridge.fullname" -}}
{{- printf "%s-bridge" (include "prefix.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Selector labels for Bridge pods.
*/}}
{{- define "kompass.bridge.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kompass.bridge.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Common labels for Bridge resources.
*/}}
{{- define "kompass.bridge.labels" -}}
helm.sh/chart: {{ include "kompass.chart" . }}
{{ include "kompass.bridge.selectorLabels" . }}
app.kubernetes.io/component: bridge
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Resolved container image reference.
Falls back to .Chart.AppVersion when image.tag is empty.
*/}}
{{- define "kompass.bridge.image" -}}
{{- $img := (index .Values "kompass-bridge" "image") | default (dict) -}}
{{- $registry := $img.registry | default "" -}}
{{- $repository := $img.repository | default "" -}}
{{- $tag := default .Chart.AppVersion $img.tag -}}
{{- if $registry -}}
{{ $registry }}/{{ $repository }}:{{ $tag }}
{{- else -}}
{{ $repository }}:{{ $tag }}
{{- end -}}
{{- end -}}
