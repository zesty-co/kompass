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

{{/*
Release-specific Lease name used for actor cleanup leader election.
*/}}
{{- define "kompass.bridge.cleanupLeaderElectionID" -}}
{{- $bridgeValues := index .Values "kompass-bridge" | default (dict) -}}
{{- $manager := $bridgeValues.manager | default (dict) -}}
{{- $leaderElection := $manager.leaderElection | default (dict) -}}
{{- $suffix := $leaderElection.idSuffix | default "kompass-bridge-actor-cleanup" -}}
{{- printf "%s-%s" .Release.Name $suffix | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Kompass Bridge service
*/}}
{{- define "kompass.bridge.service" -}}
{{- (index .Values.global "kompass-bridge").name -}}
{{- end -}}

{{/*
Resolve bridge Kafka password env var.
Requires either an explicit bridge kafka password or a credentials secret name.
*/}}
{{- define "kompass.bridge.kafkaPasswordEnv" -}}
{{- $bridgeKafka := (index .Values "kompass-bridge" "kafka") | default (dict) -}}
{{- $kompassInsightsSecret := (index .Values "kompass-insights" "secret") | default (dict) -}}
{{- $kafkaPassword := (index $bridgeKafka "password") | default "" -}}
{{- $kafkaPasswordSecretName := (index $kompassInsightsSecret "name") | default "" -}}
- name: KAFKA_PASSWORD
  {{- if $kafkaPassword }}
  value: {{ $kafkaPassword | quote }}
  {{- else if $kafkaPasswordSecretName }}
  valueFrom:
    secretKeyRef:
      name: {{ $kafkaPasswordSecretName | quote }}
      key: "ENCRYPTED_CREDENTIALS"
      optional: true
  {{- else }}
  {{- fail "kompass-bridge.kafka.password or kompass-insights.secret.name must be set for bridge Kafka authentication" }}
  {{- end }}
{{- end -}}
