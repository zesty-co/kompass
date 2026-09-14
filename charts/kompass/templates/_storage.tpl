{{/*
Third-party charts use component-specific values; YAML anchors are expanded before
Helm merges files. Keep validation aligned with the actual enabled PVC consumers.
An omitted/null class uses the cluster default. An explicit classless PVC is
excluded from dynamic provisioning validation.
*/}}
{{- define "kompass.requiredStorageClasses" -}}
{{- $classes := list -}}
{{- $ki := index .Values "kompass-insights" -}}
{{- $consumers := list (dict "enabled" $ki.enabled "pvc" $ki.persistence.spec "classlessEmpty" true) -}}
{{- $consumers = append $consumers (dict "enabled" (and .Values.victoriaMetrics.enabled .Values.victoriaMetrics.server.persistentVolume.enabled (not .Values.victoriaMetrics.server.persistentVolume.existingClaim)) "pvc" .Values.victoriaMetrics.server.persistentVolume) -}}
{{- $consumers = append $consumers (dict "enabled" (and .Values.victoriaMetricsCluster.enabled .Values.victoriaMetricsCluster.vmstorage.persistentVolume.enabled) "pvc" .Values.victoriaMetricsCluster.vmstorage.persistentVolume) -}}
{{- $consumers = append $consumers (dict "enabled" (and .Values.victoriaMetricsCluster.enabled .Values.victoriaMetricsCluster.vmselect.enabled .Values.victoriaMetricsCluster.vmselect.persistentVolume.enabled) "pvc" .Values.victoriaMetricsCluster.vmselect.persistentVolume) -}}
{{- $consumers = append $consumers (dict "enabled" (and .Values.grafana.enabled .Values.grafana.persistence.enabled (not .Values.grafana.persistence.existingClaim)) "pvc" .Values.grafana.persistence) -}}
{{- range $consumers -}}
  {{- if .enabled -}}
    {{- $name := get .pvc "storageClassName" -}}
    {{- if or (eq $name "-") (and .classlessEmpty (hasKey .pvc "storageClassName") (kindIs "string" $name) (eq $name "")) -}}
      {{/* Static/classless storage is managed by the customer. */}}
    {{- else if not $name -}}
      {{- $classes = append $classes "__default__" -}}
    {{- else -}}
      {{- if not (regexMatch "^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$" $name) -}}
        {{- fail "storageClassName must be a Kubernetes StorageClass name" -}}
      {{- end -}}
      {{- $classes = append $classes $name -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
{{- dict "classes" (uniq $classes) | toYaml -}}
{{- end -}}
