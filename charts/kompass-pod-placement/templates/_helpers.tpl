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
Create the name of the service account
*/}}
{{- define "kompass-pod-placement.serviceAccountName" -}}
{{- if .Values.serviceAccount.name }}
{{- .Values.serviceAccount.name }}
{{- else }}
{{- printf "%s-sa" (include "kompass-pod-placement.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create the name of role
*/}}
{{- define "kompass-pod-placement.roleName" -}}
{{- printf "%s-role" (include "kompass-pod-placement.fullname" .) }}
{{- end }}

{{/*
Create the name of cluster role
*/}}
{{- define "kompass-pod-placement.clusterRoleName" -}}
{{- include "kompass-pod-placement.fullname" . }}
{{- end }}

{{- define "cxLogging.ingressUrl" }}
- name: CORALOGIX_INGRESS_URL
{{- /*
For backward compatibility, if the cxLogging.otelEndpoint is provided, use it to generate the ingressUrl.
To remove in the future.
*/}}
{{- if and .Values.global.cxLogging .Values.global.cxLogging.enabled }}
{{- if .Values.global.cxLogging.otelEndpoint }}
  value: https://{{ .Values.global.cxLogging.otelEndpoint }}/
{{- else }}
  value: {{ .Values.global.cxLogging.ingressUrl }}
{{- end }}
{{- else if .Values.cxLogging.otelEndpoint }}
  value: https://{{ .Values.cxLogging.otelEndpoint }}/
{{- else }}
  value: {{ .Values.cxLogging.ingressUrl }}
{{- end }}
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
