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
{{- if .Values.affinity -}}
{{- toYaml .Values.affinity -}}
{{- else -}}
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

{{- define "kompass-pod-placement.webhook.certificateName" -}}
{{ include "kompass-pod-placement.fullname" . }}-webhook-cert
{{- end }}

{{- define "kompass-pod-placement.isOpenShift" -}}
{{- $global := .Values.global | default dict -}}
{{- $toggle := get $global "openShift" -}}
{{- if kindIs "bool" $toggle -}}
  {{- if $toggle -}}true{{- end -}}
{{- else -}}
  {{- if or (.Capabilities.APIVersions.Has "security.openshift.io/v1") (.Capabilities.APIVersions.Has "route.openshift.io/v1") -}}true{{- end -}}
{{- end -}}
{{- end -}}

{{- define "kompass-pod-placement.imagePullSecrets" -}}
{{- $global := .Values.global | default dict -}}
{{- $globalList := $global.imagePullSecrets | default list -}}
{{- $componentList := .Values.imagePullSecrets | default list -}}
{{- $legacyName := (($global.imagePullSecret) | default dict).name | default "" -}}
{{- $resolved := list -}}
{{- if gt (len $globalList) 0 -}}
{{- $resolved = $globalList -}}
{{- else if gt (len $componentList) 0 -}}
{{- $resolved = $componentList -}}
{{- else if ne $legacyName "" -}}
{{- $resolved = list (dict "name" $legacyName) -}}
{{- end -}}
{{- if gt (len $resolved) 0 -}}
{{- toYaml $resolved -}}
{{- end -}}
{{- end -}}

{{- define "kompass-pod-placement.defaultPodSecurityContext" -}}
{{- if not (include "kompass-pod-placement.isOpenShift" .) -}}
fsGroup: 65532
runAsGroup: 65532
runAsNonRoot: true
runAsUser: 65532
seccompProfile:
  type: RuntimeDefault
{{- end -}}
{{- end -}}
