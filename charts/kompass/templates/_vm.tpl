{{/* VictoriaMetrics helpers */}}

{{/*
Generate VM single service name
*/}}
{{- define "kompass.victoria-metrics.vmsingle.service.name" -}}
{{ required "values.victoriaMetrics.server.fullnameOverride is required" .Values.victoriaMetrics.server.fullnameOverride }}
{{- end -}}

{{/*
Generate VM single url
*/}}
{{- define "kompass.victoria-metrics.vmsingle.url" -}}
http://{{ include "kompass.victoria-metrics.vmsingle.service.name" . }}:8428
{{- end -}}

{{/*
Generate VM cluster vmselect service name
*/}}
{{- define "kompass.victoria-metrics.vmcluster.vmselect.service.name" -}}
{{ required "values.victoriaMetricsCluster.vmselect.fullnameOverride is required" .Values.victoriaMetricsCluster.vmselect.fullnameOverride }}
{{- end -}}

{{/*
Generate VM cluster vmselect url
*/}}
{{- define "kompass.victoria-metrics.vmcluster.vmselect.tenant.url" -}}
http://{{ include "kompass.victoria-metrics.vmcluster.vmselect.service.name" . }}:8481/select/0:0
{{- end -}}

{{/*
Generate VM cluster vmselect url
*/}}
{{- define "kompass.victoria-metrics.vmcluster.vmselect.url" -}}
{{ include "kompass.victoria-metrics.vmcluster.vmselect.tenant.url" . }}/prometheus
{{- end -}}

{{/*
Generate VM cluster vminsert service name
*/}}
{{- define "kompass.victoria-metrics.vmcluster.vminsert.service.name" -}}
{{ required "values.victoriaMetricsCluster.vminsert.fullnameOverride is required" .Values.victoriaMetricsCluster.vminsert.fullnameOverride }}
{{- end -}}

{{/*
Generate VM cluster vminsert url
*/}}
{{- define "kompass.victoria-metrics.vmcluster.vminsert.url" -}}
http://{{ include "kompass.victoria-metrics.vmcluster.vminsert.service.name" . }}:8480/insert/0:0/prometheus
{{- end -}}

{{/* High level helper*/}}

{{/*
Validate VM topology for VMAuth routing
*/}}
{{- define "kompass.victoria-metrics.auth.topology.validate" -}}
{{- if .Values.victoriaMetricsAuth.enabled -}}
{{- if .Values.victoriaMetricsAuth.useSingle -}}
{{- if not .Values.victoriaMetrics.enabled -}}
{{- fail "invalid VictoriaMetrics topology: victoriaMetricsAuth.useSingle=true requires victoriaMetrics.enabled=true" -}}
{{- end -}}
{{- else -}}
{{- if not .Values.victoriaMetricsCluster.enabled -}}
{{- fail "invalid VictoriaMetrics topology: victoriaMetricsAuth.useSingle=false requires victoriaMetricsCluster.enabled=true" -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Generate VM select endpoint
*/}}
{{- define "kompass.victoria-metrics.select.endpoint" -}}
{{- include "kompass.victoria-metrics.auth.topology.validate" . -}}
{{- if .Values.victoriaMetricsAuth.useSingle -}}
{{ include "kompass.victoria-metrics.vmsingle.url" . }}
{{- else -}}
{{ include "kompass.victoria-metrics.vmcluster.vmselect.url" . }}
{{- end -}}
{{- end -}}

{{/*
Generate VM insert endpoint
*/}}
{{- define "kompass.victoria-metrics.insert.endpoint" -}}
{{- include "kompass.victoria-metrics.auth.topology.validate" . -}}
{{- if .Values.victoriaMetricsAuth.useSingle -}}
{{ include "kompass.victoria-metrics.vmsingle.url" . }}
{{- else -}}
{{ include "kompass.victoria-metrics.vmcluster.vminsert.url" . }}
{{- end -}}
{{- end -}}

{{/*
Generate VMUI endpoint
*/}}
{{- define "kompass.victoria-metrics.vmui.endpoint" -}}
{{- include "kompass.victoria-metrics.auth.topology.validate" . -}}
{{- if .Values.victoriaMetricsAuth.useSingle -}}
{{ include "kompass.victoria-metrics.vmsingle.url" . }}
{{- else -}}
{{ include "kompass.victoria-metrics.vmcluster.vmselect.tenant.url" . }}
{{- end -}}
{{- end -}}
