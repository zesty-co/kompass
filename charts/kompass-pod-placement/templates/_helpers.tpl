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
app.kubernetes.io/instance: "{{ include "kompass-pod-placement.fullname" . }}"
app.kubernetes.io/name: "{{ include "kompass-pod-placement.fullname" . }}"
{{- end }}

{{/*
Selector labels
*/}}
{{- define "kompass-pod-placement.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kompass-pod-placement.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account
*/}}
{{- define "kompass-pod-placement.serviceAccountName" -}}
{{ printf "%s-sa" (include "kompass-pod-placement.fullname" .) }}
{{- end }}

{{/*
Create the name of role
*/}}
{{- define "kompass-pod-placement.roleName" -}}
{{- printf "%s-role" (include "kompass-pod-placement.fullname" .) }}
{{- end }}

{{- define "cxLogging.ingressUrl" }}
- name: CORALOGIX_INGRESS_URL
{{- /*
For backward compatibility, if the cxLogging.otelEndpoint is provided, use it to generate the ingressUrl.
To remove in the future.
*/}}
{{- if .Values.global.cxLogging.otelEndpoint }}
  value: https://{{ .Values.global.cxLogging.otelEndpoint }}/
{{- else }}
  value: {{ .Values.global.cxLogging.ingressUrl }}
{{- end }}
{{- end }}
