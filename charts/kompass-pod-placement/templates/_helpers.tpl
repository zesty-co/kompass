{{/*
Helper template
*/}}
{{- define "kompass-pod-placement.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "kompass-pod-placement.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s" $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "kompass-pod-placement.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "kompass-pod-placement.labels" -}}
{{- include "kompass-pod-placement.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ include "kompass-pod-placement.chart" . }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "kompass-pod-placement.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kompass-pod-placement.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Render affinity configuration
*/}}
{{- define "kompass-pod-placement.affinity" -}}
{{- if .Values.affinity }}
{{- toYaml .Values.affinity }}
{{- else }}
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            {{- include "kompass-pod-placement.selectorLabels" . | nindent 12 }}
        topologyKey: kubernetes.io/hostname
{{- end }}
{{- end }}

{{/*
Create image reference
*/}}
{{- define "kompass-pod-placement.image" -}}
{{ .Values.image.registry }}:{{ default .Chart.AppVersion .Values.image.tag  }}
{{- end }}
