{{/*
Helper Templates for Kompass Insights
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "zesty-k8s.name" -}}
  {{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "zesty-k8s.fullname" -}}
  {{- if .Values.fullnameOverride }}
    {{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
  {{- else }}
    {{- $name := default .Chart.Name .Values.nameOverride }}
    {{- if contains $name .Chart.Name }}
      {{- .Chart.Name | trunc 63 | trimSuffix "-" }}
    {{- else }}
      {{- printf "%s-%s" .Chart.Name $name | trunc 63 | trimSuffix "-" }}
    {{- end }}
  {{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "zesty-k8s.chart" -}}
  {{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a version as used by the chart and image tag.
*/}}
{{- define "zesty-k8s.version" -}}
  {{ default .Chart.AppVersion .Values.image.tag  }}
{{- end }}


{{/*
Create a name for the SA.
*/}}
{{- define "zesty-k8s.serviceAccountName" -}}
  {{ printf "%s-sa" (include "zesty-k8s.fullname" .) }}
{{- end -}}

{{/*
Create a name for the PVC.
*/}}
{{- define "zesty-k8s.pvcname" -}}
  {{ printf "%s-db-pvc" (include "zesty-k8s.fullname" .) }}
{{- end -}}

{{/*
Create a name for the external-secret.
*/}}
{{- define "zesty-k8s.externalSecret.awsCred" -}}
  {{ printf "%s-aws-cluster-secret" (include "zesty-k8s.fullname" .) }}
{{- end -}}

{{/*
Create a name for the ConfigMap.
*/}}
{{- define "zesty-k8s.configmap" -}}
  {{ printf "%s-cm" (include "zesty-k8s.fullname" .) }}
{{- end -}}

{{/*
Create a name for the ClusterRole.
*/}}
{{- define "zesty-k8s.clusterrole" -}}
  {{ printf "%s-clusterRole" (include "zesty-k8s.fullname" .) }}
{{- end -}}

{{/*
Create a name for the ClusterRoleBinding.
*/}}
{{- define "zesty-k8s.clusterrolebinding" -}}
  {{ printf "%s-clusterRoleBinding" (include "zesty-k8s.fullname" .) }}
{{- end -}}

{{/*
Create a name for the Role.
*/}}
{{- define "zesty-k8s.role" -}}
  {{ printf "%s-role" (include "zesty-k8s.fullname" .) }}
{{- end -}}

{{/*
Create a name for the RoleBinding.
*/}}
{{- define "zesty-k8s.rolebinding" -}}
  {{ printf "%s-roleBinding" (include "zesty-k8s.fullname" .) }}
{{- end -}}

{{/*
Create a name for the Service.
*/}}
{{- define "zesty-k8s.svc" -}}
  {{ printf "%s-svc" (include "zesty-k8s.fullname" .) }}
{{- end -}}

{{/*
All of the relevant verbs.
*/}}
{{- define "zesty-k8s.verbs" -}}
verbs:
  - get
  - list
  - patch
  - update
  - watch
{{- end -}}

{{- define "zesty-k8s.labels" -}}
helm.sh/chart: {{ include "zesty-k8s.chart" . }}
{{ include "zesty-k8s.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "zesty-k8s.selectorLabels" -}}
app.kubernetes.io/name: {{ include "zesty-k8s.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "zesty-k8s.victoriaMetrics.endpoint" -}}
    {{- if and .Values.global .Values.global.victoriaMetricsRemoteUrl }}
        {{- .Values.global.victoriaMetricsRemoteUrl -}}
    {{- else -}}
        http://kompass-victoria-metrics-auth:8427
    {{- end }}
{{- end }}

{{- define "zesty-k8s.exposedMetrics.port" -}}
{{- default "9003" .Values.insights.metrics.port }}
{{- end }}

{{- define "zesty-k8s.recommendations.fullname" -}}
 {{ printf "%s-recommendations" (include "zesty-k8s.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "zesty-k8s.self-monitoring.fullname" -}}
 {{ printf "%s-self-monitoring" (include "zesty-k8s.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "zesty-k8s.self-monitoring.serviceAccountName" -}}
 {{- printf "%s-sa" (include "zesty-k8s.self-monitoring.fullname" .)}}
{{- end }}

{{- define "zesty-k8s.globalConfig" -}}
  {{- if and .Values.global .Values.global.globalConfigName }}
      {{- .Values.global.globalConfigName -}}
  {{- else -}}
      global-config
  {{- end }}
{{- end }}

{{- define "zesty-k8s.workload.mergeMaps" -}}
{{- $global := default dict .global -}}
{{- $component := default dict .component -}}
{{- $fallback := default dict .fallback -}}
{{- $key := .key -}}
{{- $componentValue := (get $component $key) | default dict -}}
{{- $globalValue := (get $global $key) | default dict -}}
{{- $resolved := deepCopy $fallback | mergeOverwrite $componentValue | mergeOverwrite $globalValue -}}
{{- if gt (len $resolved) 0 -}}
{{- toYaml $resolved -}}
{{- end -}}
{{- end }}

{{- define "zesty-k8s.workload.resolveListWithGlobalPrecedence" -}}
{{- $global := default dict .global -}}
{{- $component := default dict .component -}}
{{- $fallback := .fallback | default (list) -}}
{{- $key := .key -}}
{{- $resolved := $fallback -}}
{{- if and (hasKey $global $key) (ne (get $global $key) nil) -}}
  {{- $resolved = (get $global $key) -}}
{{- else if and (hasKey $component $key) (ne (get $component $key) nil) -}}
  {{- $resolved = (get $component $key) -}}
{{- end -}}
{{- if ne $resolved nil -}}
{{- if not (kindIs "slice" $resolved) -}}
{{- fail (printf "Invalid type for workload list key '%s': expected list, got %s" $key (kindOf $resolved)) -}}
{{- end -}}
{{- toYaml $resolved -}}
{{- end -}}
{{- end }}

{{- define "zesty-k8s.workload.resolveBool" -}}
{{- $global := default dict .global -}}
{{- $component := default dict .component -}}
{{- $key := .key -}}
{{- if and (hasKey $global $key) (ne (get $global $key) nil) -}}
{{- get $global $key -}}
{{- else if and (hasKey $component $key) (ne (get $component $key) nil) -}}
{{- get $component $key -}}
{{- else if ne .fallback nil -}}
{{- .fallback -}}
{{- end -}}
{{- end }}

{{- define "zesty-k8s.workload.resolveString" -}}
{{- $global := default dict .global -}}
{{- $component := default dict .component -}}
{{- $key := .key -}}
{{- $globalValue := get $global $key -}}
{{- $componentValue := get $component $key -}}
{{- if and (hasKey $global $key) (ne $globalValue nil) (ne (toString $globalValue) "") -}}
{{- $globalValue -}}
{{- else if and (hasKey $component $key) (ne $componentValue nil) (ne (toString $componentValue) "") -}}
{{- $componentValue -}}
{{- else if and (ne .fallback nil) (ne (toString .fallback) "") -}}
{{- .fallback -}}
{{- end -}}
{{- end }}

{{- define "zesty-k8s.workload.validateContainerSecurityContext" -}}
{{- $context := .context | default dict -}}
{{- $path := .path | default "securityContext" -}}
{{- if not (kindIs "map" $context) -}}
{{- fail (printf "Invalid %s: expected map, got %s" $path (kindOf $context)) -}}
{{- end -}}
{{- end }}

{{- define "zesty-k8s.workload.extractPodSecurityContext" -}}
{{- $context := .context | default dict -}}
{{- $path := .path | default "securityContext" -}}
{{- if not (kindIs "map" $context) -}}
{{- fail (printf "Invalid %s: expected map, got %s" $path (kindOf $context)) -}}
{{- end -}}
{{- $pod := dict -}}
{{- if hasKey $context "fsGroup" -}}
{{- $_ := set $pod "fsGroup" (get $context "fsGroup") -}}
{{- end -}}
{{- if hasKey $context "fsGroupChangePolicy" -}}
{{- $_ := set $pod "fsGroupChangePolicy" (get $context "fsGroupChangePolicy") -}}
{{- end -}}
{{- if hasKey $context "supplementalGroups" -}}
{{- $_ := set $pod "supplementalGroups" (get $context "supplementalGroups") -}}
{{- end -}}
{{- if hasKey $context "sysctls" -}}
{{- $_ := set $pod "sysctls" (get $context "sysctls") -}}
{{- end -}}
{{- if gt (len $pod) 0 -}}
{{- toYaml $pod -}}
{{- end -}}
{{- end }}

{{- define "zesty-k8s.workload.extractContainerSecurityContext" -}}
{{- $context := .context | default dict -}}
{{- $path := .path | default "securityContext" -}}
{{- if not (kindIs "map" $context) -}}
{{- fail (printf "Invalid %s: expected map, got %s" $path (kindOf $context)) -}}
{{- end -}}
{{- $container := deepCopy $context -}}
{{- if hasKey $container "fsGroup" -}}
{{- $_ := unset $container "fsGroup" -}}
{{- end -}}
{{- if hasKey $container "fsGroupChangePolicy" -}}
{{- $_ := unset $container "fsGroupChangePolicy" -}}
{{- end -}}
{{- if hasKey $container "supplementalGroups" -}}
{{- $_ := unset $container "supplementalGroups" -}}
{{- end -}}
{{- if hasKey $container "sysctls" -}}
{{- $_ := unset $container "sysctls" -}}
{{- end -}}
{{- if gt (len $container) 0 -}}
{{- toYaml $container -}}
{{- end -}}
{{- end }}

{{- define "zesty-k8s.workload.legacyImagePullSecrets" -}}
{{- $globalPullSecrets := list -}}
{{- if .Values.global.imagePullSecret.name -}}
{{- $globalPullSecrets = append $globalPullSecrets (dict "name" .Values.global.imagePullSecret.name) -}}
{{- end -}}
{{- range .Values.global.imagePullSecrets -}}
{{- $globalPullSecrets = append $globalPullSecrets . -}}
{{- end -}}
{{- $pullSecrets := .Values.imagePullSecrets | default $globalPullSecrets -}}
{{- if gt (len ($pullSecrets | default (list))) 0 -}}
{{- toYaml $pullSecrets -}}
{{- end -}}
{{- end }}

{{- define "zesty-k8s.workload.resolveImagePullSecrets" -}}
{{- $global := default dict .global -}}
{{- $component := default dict .component -}}
{{- $fallback := include "zesty-k8s.workload.legacyImagePullSecrets" .root | fromYamlArray | default (list) -}}
{{- include "zesty-k8s.workload.resolveListWithGlobalPrecedence" (dict
  "global" $global
  "component" $component
  "fallback" $fallback
  "key" "imagePullSecrets"
) -}}
{{- end }}

{{- define "zesty-k8s.coralogix.envs" -}}
{{- if and .Values.global.cxLogging .Values.global.cxLogging.enabled -}}
- name: CX_CLUSTER_NAME
  value: {{ .Values.global.cxLogging.clusterName }}
{{- if .coralogixApiKey }}
- name: CORALOGIX_API_KEY
{{- else }}
- name: CX_API_KEY
{{- end }}
  value: {{ .Values.global.cxLogging.apiKey }}
{{- if .domain }}
- name: CORALOGIX_DOMAIN
  value: {{ .Values.global.cxLogging.domain }}
{{- end }}
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
{{- if .ingressLogsUrl }}
- name: CORALOGIX_INGRESS_LOGS_URL
  value: {{ .Values.global.cxLogging.ingressLogsUrl }}
{{- end }}
{{- if .logUrl }}
- name: CORALOGIX_LOG_URL
  value: {{ .Values.global.cxLogging.logUrl }}
{{- end }}
{{- if .timeDeltaUrl }}
- name: CORALOGIX_TIME_DELTA_URL
  value: {{ .Values.global.cxLogging.timeDeltaUrl }}
{{- end }}
{{- if .otelEndpoint }}
- name: CORALOGIX_OTEL_ENDPOINT
  value: {{ .Values.global.cxLogging.otelEndpoint }}
{{- end }}
{{- else if and .Values.cxLogging .Values.cxLogging.enabled }}
- name: CX_CLUSTER_NAME
  value: {{ .Values.cxLogging.clusterName }}
{{- if .coralogixApiKey }}
- name: CORALOGIX_API_KEY
{{- else }}
- name: CX_API_KEY
{{- end }}
  value: {{ .Values.cxLogging.apiKey }}
{{- if .domain }}
- name: CORALOGIX_DOMAIN
  value: {{ .Values.cxLogging.domain }}
{{- end }}
- name: CORALOGIX_INGRESS_URL
{{- /*
For backward compatibility, if the cxLogging.otelEndpoint is provided, use it to generate the ingressUrl.
To remove in the future.
*/}}
{{- if .Values.cxLogging.otelEndpoint }}
  value: https://{{ .Values.cxLogging.otelEndpoint }}/
{{- else }}
  value: {{ .Values.cxLogging.ingressUrl }}
{{- end }}
{{- if .ingressLogsUrl }}
- name: CORALOGIX_INGRESS_LOGS_URL
  value: {{ .Values.cxLogging.ingressLogsUrl }}
{{- end }}
{{- if .logUrl }}
- name: CORALOGIX_LOG_URL
  value: {{ .Values.cxLogging.logUrl }}
{{- end }}
{{- if .timeDeltaUrl }}
- name: CORALOGIX_TIME_DELTA_URL
  value: {{ .Values.cxLogging.timeDeltaUrl }}
{{- end }}
{{- if .otelEndpoint }}
- name: CORALOGIX_OTEL_ENDPOINT
  value: {{ .Values.cxLogging.otelEndpoint }}
{{- end}}
{{- end -}}
{{- end -}}

{{- define "zesty-k8s.controller.coralogix.envs" -}}
{{- include "zesty-k8s.coralogix.envs" (dict "Values" .Values "coralogixApiKey" false "domain" true "ingressLogsUrl" true "logUrl" true "timeDeltaUrl" true "otelEndpoint" true) }}
{{- end }}

{{- define "zesty-k8s.recommendations.coralogix.envs" -}}
{{- include "zesty-k8s.coralogix.envs" (dict "Values" .Values "coralogixApiKey" true "domain" false "logUrl" true "timeDeltaUrl" true "otelEndpoint" false) }}
{{- end }}

{{- define "zesty-k8s.monitoring.coralogix.envs" -}}
{{- include "zesty-k8s.coralogix.envs" (dict "Values" .Values "coralogixApiKey" false "domain" false "logUrl" false "timeDeltaUrl" false "otelEndpoint" false) }}
{{- end }}
