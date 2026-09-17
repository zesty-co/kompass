{{/*
Expand the name of the chart.
*/}}
{{- define "pod-rightsizing.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "prefix.name" -}}
{{- default "zesty-kompass" .Values.prefix | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "name" -}}
{{- printf "%s-%s" (include "prefix.name" .) .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create the name of the recommendations-maker
*/}}
{{- define "recommendations-maker.name" -}}
{{- .Values.recommendationsMaker.fullnameOverride | default (printf "%s-%s" (include "name" .) .Values.recommendationsMaker.name | trunc 63 | trimSuffix "-") }}
{{- end }}

{{/*
Create the name of the action-taker
*/}}
{{- define "action-taker.name" -}}
{{- .Values.actionTaker.fullnameOverride | default (printf "%s-%s" (include "name" .) .Values.actionTaker.name | trunc 63 | trimSuffix "-") }}
{{- end }}

{{/*
Guardian has a fixed name because the rightsizing exclusion refers to it directly.
*/}}
{{- define "guardian.name" -}}
kompass-guardian
{{- end }}

{{/*
Create the name of the metrics-exporter
*/}}
{{- define "metrics-exporter.name" -}}
{{- .Values.metricsExporter.fullnameOverride | default (printf "%s-%s" (include "name" .) .Values.metricsExporter.name | trunc 63 | trimSuffix "-") }}
{{- end }}

{{/*
Create the name of the bridge-data-exporter
*/}}
{{- define "bridge-data-exporter.name" -}}
{{- .Values.bridgeDataExporter.fullnameOverride | default (printf "%s-%s" (include "name" .) .Values.bridgeDataExporter.name | trunc 63 | trimSuffix "-") }}
{{- end }}

{{/*
Create the name of the kompass rightsizing config map
*/}}
{{- define "kompass-pod-rightsizing-config.name" -}}
{{- default "kompass-rightsizing-config" .Values.podRightsizingConfig.name }}
{{- end }}

{{/*
Create the name of the kompass rightsizing params/override config map
*/}}
{{- define "kompass-pod-rightsizing-params-config.name" -}}
{{- default "kompass-rightsizing-params-config" .Values.rightsizingParamsConfig.name }}
{{- end }}

{{/*
Create the name of the Guardian static config map.
*/}}
{{- define "kompass-guardian-config.name" -}}
kompass-guardian-config
{{- end }}

{{/*
Create the name of the kompass rightsizing initial values BU config map
*/}}
{{- define "kompass-pod-rightsizing-initial-values-config.name" -}}
{{- printf "%s-%s" (include "name" .) "initial-values-config" }}
{{- end }}

{{/*
Create the name of the kompass rightsizing grafana dashboard config map
*/}}
{{- define "kompass-pod-rightsizing-grafana-dashboard-config.name" -}}
{{- printf "%s-%s" (include "name" .) "grafana-dashboard" }}
{{- end }}

{{/*
Create the name of the kompass rightsizing job dashboard config map
*/}}
{{- define "kompass-pod-rightsizing-dashboards-config.name" -}}
{{- printf "%s-%s" (include "name" .) "dashboards" }}
{{- end }}

{{/*
Create the name of the kompass rightsizing webhook service
*/}}
{{- define "kompass-webhook-svc.name" -}}
{{- printf "%s-%s" (include "name" .) "webhook-service" }}
{{- end }}

{{- define "kube-state-metrics.serviceName" -}}
{{- if (index .Values "kube-state-metrics" "enabled") }}
{{- index .Values "kube-state-metrics" "fullnameOverride" | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- index .Values "kube-state-metrics" "serviceName" | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "vmagent.scrapeInterval" -}}
{{- default "30s" .Values.victoriaMetrics.vmagent.scrapeInterval -}}
{{- end }}

{{/*
Create the name of the service account to use for the system
*/}}
{{- define "pod-rightsizing.serviceAccountName" -}}
{{- default "zesty-kompass-rightsizing" .Values.serviceAccount.name }}
{{- end }}

{{/*
Create the name of the service account to use for the system
*/}}
{{- define "pod-rightsizing.metricsExporterServiceAccountName" -}}
{{- default "zesty-kompass-rightsizing-metrics-exporter" .Values.metricsExporterServiceAccount.name }}
{{- end }}

{{/*
Create the name of the service account to use for the system
*/}}
{{- define "pod-rightsizing.bridgeDataExporterServiceAccountName" -}}
{{- default "zesty-kompass-rightsizing-bridge-data-exporter" .Values.bridgeDataExporterServiceAccount.name }}
{{- end }}

{{/*
Create the name of the service account to use for Guardian.
*/}}
{{- define "pod-rightsizing.guardianServiceAccountName" -}}
{{- default "zesty-kompass-guardian" .Values.guardianServiceAccount.name }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "pod-rightsizing.fullname" -}}
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
{{- define "pod-rightsizing.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "pod-rightsizing.labels" -}}
helm.sh/chart: {{ include "pod-rightsizing.chart" . }}
{{ include "pod-rightsizing.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "pod-rightsizing.selectorLabels" -}}
app.kubernetes.io/name: pod-rightsizing # Don't change this, since the component monitor uses this value to identify the component
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Get the VictoriaMetrics remote URL, with a default.
*/}}
{{- define "pod-rightsizing.victoriaMetrics.url" -}}
{{- default "http://kompass-victoria-metrics:8428" .Values.global.victoriaMetricsRemoteUrl }}
{{- end -}}

{{/*
Build JVM auto-discovery signal lists.
The base lists can be replaced through jvmMetrics.autoDiscovery.*Signals, while
jvmMetrics.autoDiscovery.additional*Signals append customer-specific signals.
*/}}
{{- define "pod-rightsizing.jvmAutoDiscovery.envSignals" -}}
{{- $autoDiscovery := ((.Values.jvmMetrics | default dict).autoDiscovery | default dict) -}}
{{- join "," (concat ($autoDiscovery.envSignals | default list) ($autoDiscovery.additionalEnvSignals | default list)) -}}
{{- end -}}

{{- define "pod-rightsizing.jvmAutoDiscovery.commandSignals" -}}
{{- $autoDiscovery := ((.Values.jvmMetrics | default dict).autoDiscovery | default dict) -}}
{{- join "," (concat ($autoDiscovery.commandSignals | default list) ($autoDiscovery.additionalCommandSignals | default list)) -}}
{{- end -}}

{{- define "pod-rightsizing.jvmAutoDiscovery.imageSignals" -}}
{{- $autoDiscovery := ((.Values.jvmMetrics | default dict).autoDiscovery | default dict) -}}
{{- join "," (concat ($autoDiscovery.imageSignals | default list) ($autoDiscovery.additionalImageSignals | default list)) -}}
{{- end -}}

{{/*
Build the effective pod security context for a component.
Merge order (later wins): component.podSecurityContext -> global.podSecurityContext
*/}}
{{- define "pod-rightsizing.securityContext.pod" -}}
{{- $root := .root -}}
{{- $componentSecurityContext := default (dict) .componentSecurityContext -}}
{{- $podSecurityContext := mergeOverwrite (deepCopy $componentSecurityContext) (deepCopy (default (dict) $root.Values.global.podSecurityContext)) -}}
{{- $podSecurityContext = pick $podSecurityContext "fsGroup" "fsGroupChangePolicy" "runAsGroup" "runAsNonRoot" "runAsUser" "seLinuxOptions" "seccompProfile" "supplementalGroups" "supplementalGroupsPolicy" "sysctls" "windowsOptions" -}}
{{- toYaml $podSecurityContext -}}
{{- end -}}

{{/*
Build the effective container security context for a component.
Merge order (later wins): component.securityContext -> global.securityContext
*/}}
{{- define "pod-rightsizing.securityContext.container" -}}
{{- $root := .root -}}
{{- $componentSecurityContext := default (dict) .componentSecurityContext -}}
{{- $containerSecurityContext := mergeOverwrite (deepCopy $componentSecurityContext) (deepCopy (default (dict) $root.Values.global.securityContext)) -}}
{{- $containerSecurityContext = pick $containerSecurityContext "allowPrivilegeEscalation" "appArmorProfile" "capabilities" "privileged" "procMount" "readOnlyRootFilesystem" "runAsGroup" "runAsNonRoot" "runAsUser" "seLinuxOptions" "seccompProfile" "windowsOptions" -}}
{{- toYaml $containerSecurityContext -}}
{{- end -}}

{{/*
Build the effective kube-rbac-proxy security context.
Merge order (later wins): actionTaker.securityContext -> actionTaker.kubeRbacProxy.securityContext -> global.securityContext
*/}}
{{- define "pod-rightsizing.securityContext.actionTakerKubeRbacProxy" -}}
{{- $root := .root -}}
{{- $actionTakerSecurityContext := default (dict) .actionTakerSecurityContext -}}
{{- $kubeRbacProxySecurityContext := default (dict) .kubeRbacProxySecurityContext -}}
{{- $componentSecurityContext := mergeOverwrite (deepCopy $actionTakerSecurityContext) (deepCopy $kubeRbacProxySecurityContext) -}}
{{- include "pod-rightsizing.securityContext.container" (dict "root" $root "componentSecurityContext" $componentSecurityContext) -}}
{{- end -}}

{{/*
Merge component and global maps.
Merge order (later wins): component -> global
*/}}
{{- define "pod-rightsizing.mergeMaps.componentGlobal" -}}
{{- $componentMap := default (dict) .component -}}
{{- $globalMap := default (dict) .global -}}
{{- toYaml (mergeOverwrite (deepCopy $componentMap) (deepCopy $globalMap)) -}}
{{- end -}}

{{/*
Build effective pod labels for a component.
Merge order (later wins): component.podLabels -> global.podLabels -> required labels
*/}}
{{- define "pod-rightsizing.podTemplateLabels" -}}
{{- $root := .root -}}
{{- $componentValues := default (dict) .componentValues -}}
{{- $podLabels := mergeOverwrite (deepCopy (default (dict) $componentValues.podLabels)) (deepCopy (default (dict) $root.Values.global.podLabels)) -}}
{{- $_ := set $podLabels "app.kubernetes.io/part-of" "kompass" -}}
{{- toYaml $podLabels -}}
{{- end -}}

{{/*
Build effective workload labels for a component.
Merge order (later wins): component.workloadLabels -> global.workloadLabels -> required labels
*/}}
{{- define "pod-rightsizing.workloadLabels" -}}
{{- $root := .root -}}
{{- $componentValues := default (dict) .componentValues -}}
{{- $workloadLabels := mergeOverwrite (deepCopy (default (dict) $componentValues.workloadLabels)) (deepCopy (default (dict) $root.Values.global.workloadLabels)) -}}
{{- $_ := set $workloadLabels "app.kubernetes.io/part-of" "kompass" -}}
{{- toYaml $workloadLabels -}}
{{- end -}}

{{/*
Build effective pod annotations for a component.
Merge order (later wins): component.podAnnotations -> global.podAnnotations
*/}}
{{- define "pod-rightsizing.podTemplateAnnotations" -}}
{{- $root := .root -}}
{{- $componentValues := default (dict) .componentValues -}}
{{- include "pod-rightsizing.mergeMaps.componentGlobal" (dict "component" (default (dict) $componentValues.podAnnotations) "global" (default (dict) $root.Values.global.podAnnotations)) -}}
{{- end -}}

{{/*
Build effective affinity for a component.
Merge order (later wins): baseAffinity -> component.affinity -> global.affinity
*/}}
{{- define "pod-rightsizing.affinity" -}}
{{- $root := .root -}}
{{- $componentValues := default (dict) .componentValues -}}
{{- $baseAffinity := default (dict) .baseAffinity -}}
{{- $effectiveAffinity := mergeOverwrite (deepCopy $baseAffinity) (deepCopy (default (dict) $componentValues.affinity)) (deepCopy (default (dict) $root.Values.global.affinity)) -}}
{{- toYaml $effectiveAffinity -}}
{{- end -}}

{{/*
Default action-taker affinity.
*/}}
{{- define "pod-rightsizing.actionTaker.defaultAffinity" -}}
nodeAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
    nodeSelectorTerms:
      - matchExpressions:
          - key: kubernetes.io/arch
            operator: In
            values:
              - amd64
              - arm64
          - key: kubernetes.io/os
            operator: In
            values:
              - linux
{{- end -}}

{{/*
Build effective imagePullSecrets for a component.
Precedence: component.imagePullSecrets -> global.imagePullSecret/global.imagePullSecrets
When global secrets are defined, they are used and override component values.
*/}}
{{- define "pod-rightsizing.imagePullSecrets" -}}
{{- $root := .root -}}
{{- $componentValues := default (dict) .componentValues -}}
{{- $componentSecrets := default (list) $componentValues.imagePullSecrets -}}
{{- $legacySecrets := default (list) $root.Values.imagePullSecrets -}}
{{- $globalImagePullSecretName := $root.Values.global.imagePullSecret.name -}}
{{- if hasKey . "globalImagePullSecretName" -}}
{{- $globalImagePullSecretName = .globalImagePullSecretName -}}
{{- end -}}
{{- $globalSecrets := list -}}
{{- if $globalImagePullSecretName -}}
{{- $globalSecrets = append $globalSecrets (dict "name" $globalImagePullSecretName) -}}
{{- end -}}
{{- range (default (list) $root.Values.global.imagePullSecrets) -}}
{{- $globalSecrets = append $globalSecrets . -}}
{{- end -}}
{{- if gt (len $globalSecrets) 0 -}}
{{- toYaml $globalSecrets -}}
{{- else if gt (len $componentSecrets) 0 -}}
{{- toYaml $componentSecrets -}}
{{- else if gt (len $legacySecrets) 0 -}}
{{- toYaml $legacySecrets -}}
{{- end -}}
{{- end -}}

{{/*
Build hook-scoped image pull secret name when the chart creates the secret before hook Jobs run.
*/}}
{{- define "pod-rightsizing.hookImagePullSecretName" -}}
{{- if and .Values.global.imagePullSecret.name .Values.global.imagePullSecret.dockerconfigjson -}}
{{- printf "%s-rightsizing-hook" .Values.global.imagePullSecret.name | trunc 253 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/*
Build effective imagePullSecrets for hook Jobs.
*/}}
{{- define "pod-rightsizing.hookImagePullSecrets" -}}
{{- $hookImagePullSecretName := include "pod-rightsizing.hookImagePullSecretName" . -}}
{{- $args := dict "root" . "componentValues" (dict) -}}
{{- if $hookImagePullSecretName -}}
{{- $args = mergeOverwrite $args (dict "globalImagePullSecretName" $hookImagePullSecretName) -}}
{{- end -}}
{{- include "pod-rightsizing.imagePullSecrets" $args -}}
{{- end -}}

{{/*
Build effective topologySpreadConstraints for a component.
Precedence: component.topologySpreadConstraints -> global.topologySpreadConstraints
When global constraints are defined, they are used and override component values.
*/}}
{{- define "pod-rightsizing.topologySpreadConstraints" -}}
{{- $root := .root -}}
{{- $componentValues := default (dict) .componentValues -}}
{{- $componentConstraints := default (list) $componentValues.topologySpreadConstraints -}}
{{- $globalConstraints := default (list) $root.Values.global.topologySpreadConstraints -}}
{{- if gt (len $globalConstraints) 0 -}}
{{- toYaml $globalConstraints -}}
{{- else if gt (len $componentConstraints) 0 -}}
{{- toYaml $componentConstraints -}}
{{- end -}}
{{- end -}}

{{/*
Build effective automountServiceAccountToken for a component.
Precedence (later wins): component.automountServiceAccountToken -> global.automountServiceAccountToken
Uses hasKey so explicit false is honored.
*/}}
{{- define "pod-rightsizing.automountServiceAccountToken" -}}
{{- $root := .root -}}
{{- $componentValues := default (dict) .componentValues -}}
{{- if hasKey (default (dict) $root.Values.global) "automountServiceAccountToken" -}}
{{- get $root.Values.global "automountServiceAccountToken" -}}
{{- else if hasKey $componentValues "automountServiceAccountToken" -}}
{{- get $componentValues "automountServiceAccountToken" -}}
{{- end -}}
{{- end -}}

{{/*
Build effective runtimeClassName for a component.
Precedence: component.runtimeClassName -> global.runtimeClassName
When global runtimeClassName is defined, it overrides component values.
*/}}
{{- define "pod-rightsizing.runtimeClassName" -}}
{{- $root := .root -}}
{{- $componentValues := default (dict) .componentValues -}}
{{- $componentRuntimeClassName := default "" $componentValues.runtimeClassName -}}
{{- $globalRuntimeClassName := default "" $root.Values.global.runtimeClassName -}}
{{- if $globalRuntimeClassName -}}
{{- $globalRuntimeClassName -}}
{{- else if $componentRuntimeClassName -}}
{{- $componentRuntimeClassName -}}
{{- end -}}
{{- end -}}

{{/*
Normalize CPU quantity to millicores for comparison.
*/}}
{{- define "pod-rightsizing.cpuToMillicores" -}}
{{- $value := toString . -}}
{{- if hasSuffix "m" $value -}}
{{- printf "%.0f" (float64 (trimSuffix "m" $value)) -}}
{{- else -}}
{{- printf "%.0f" (mulf (float64 $value) 1000) -}}
{{- end -}}
{{- end -}}

{{/*
Normalize memory quantity to MiB for comparison.
*/}}
{{- define "pod-rightsizing.memoryToMi" -}}
{{- $value := toString . -}}
{{- if hasSuffix "Ki" $value -}}
{{- printf "%.6f" (divf (float64 (trimSuffix "Ki" $value)) 1024) -}}
{{- else if hasSuffix "Mi" $value -}}
{{- printf "%.6f" (float64 (trimSuffix "Mi" $value)) -}}
{{- else if hasSuffix "Gi" $value -}}
{{- printf "%.6f" (mulf (float64 (trimSuffix "Gi" $value)) 1024) -}}
{{- else if hasSuffix "Ti" $value -}}
{{- printf "%.6f" (mulf (float64 (trimSuffix "Ti" $value)) 1048576) -}}
{{- else if hasSuffix "K" $value -}}
{{- printf "%.6f" (divf (float64 (trimSuffix "K" $value)) 1048.576) -}}
{{- else if hasSuffix "M" $value -}}
{{- printf "%.6f" (divf (float64 (trimSuffix "M" $value)) 1.048576) -}}
{{- else if hasSuffix "G" $value -}}
{{- printf "%.6f" (mulf (float64 (trimSuffix "G" $value)) 953.67431640625) -}}
{{- else if hasSuffix "T" $value -}}
{{- printf "%.6f" (mulf (float64 (trimSuffix "T" $value)) 953674.31640625) -}}
{{- else -}}
{{- printf "%.6f" (divf (float64 $value) 1048576) -}}
{{- end -}}
{{- end -}}

{{/*
Enforce minimum resource value.
*/}}
{{- define "pod-rightsizing.enforceMin" -}}
{{- $user := toString .user -}}
{{- $min := toString .min -}}
{{- $kind := toString .kind -}}
{{- $userVal := 0.0 -}}
{{- $minVal := 0.0 -}}
{{- if eq $kind "cpu" -}}
{{- $userVal = float64 (include "pod-rightsizing.cpuToMillicores" $user) -}}
{{- $minVal = float64 (include "pod-rightsizing.cpuToMillicores" $min) -}}
{{- else if eq $kind "memory" -}}
{{- $userVal = float64 (include "pod-rightsizing.memoryToMi" $user) -}}
{{- $minVal = float64 (include "pod-rightsizing.memoryToMi" $min) -}}
{{- end -}}
{{- if lt $userVal $minVal }}{{ $min }}{{ else }}{{ $user }}{{ end -}}
{{- end -}}

{{/*
Metrics Exporter resources with minimum values enforced
*/}}
{{- define "pod-rightsizing.metricsExporter.resources" -}}
{{- $resources := .Values.metricsExporter.resources | default dict -}}
{{- $userCpu := $resources.requests.cpu | default "100m" -}}
{{- $userMemory := $resources.requests.memory | default "128Mi" -}}
resources:
  requests:
    cpu: {{ include "pod-rightsizing.enforceMin" (dict "kind" "cpu" "user" $userCpu "min" "100m") }}
    memory: {{ include "pod-rightsizing.enforceMin" (dict "kind" "memory" "user" $userMemory "min" "128Mi") }}
{{- with $resources.limits }}
  limits:
    {{- toYaml . | nindent 4 }}
{{- end }}
{{- end -}}

{{/*
Bridge Data Exporter resources with minimum values enforced
*/}}
{{- define "pod-rightsizing.bridgeDataExporter.resources" -}}
{{- $resources := .Values.bridgeDataExporter.resources | default dict -}}
{{- $userCpu := $resources.requests.cpu | default "100m" -}}
{{- $userMemory := $resources.requests.memory | default "128Mi" -}}
resources:
  requests:
    cpu: {{ include "pod-rightsizing.enforceMin" (dict "kind" "cpu" "user" $userCpu "min" "100m") }}
    memory: {{ include "pod-rightsizing.enforceMin" (dict "kind" "memory" "user" $userMemory "min" "128Mi") }}
{{- with $resources.limits }}
  limits:
    {{- toYaml . | nindent 4 }}
{{- end }}
{{- end -}}

{{/*
Recommendations Maker resources with minimum values enforced
*/}}
{{- define "pod-rightsizing.recommendationsMaker.resources" -}}
{{- $resources := .Values.recommendationsMaker.resources | default dict -}}
{{- $userCpu := $resources.requests.cpu | default "200m" -}}
{{- $userMemory := $resources.requests.memory | default "128Mi" -}}
resources:
  requests:
    cpu: {{ include "pod-rightsizing.enforceMin" (dict "kind" "cpu" "user" $userCpu "min" "200m") }}
    memory: {{ include "pod-rightsizing.enforceMin" (dict "kind" "memory" "user" $userMemory "min" "128Mi") }}
{{- with $resources.limits }}
  limits:
    {{- toYaml . | nindent 4 }}
{{- end }}
{{- end -}}

{{/*
Action Taker resources with minimum values enforced
*/}}
{{- define "pod-rightsizing.actionTaker.resources" -}}
{{- $resources := .Values.actionTaker.resources | default dict -}}
{{- $userCpu := $resources.requests.cpu | default "100m" -}}
{{- $userMemory := $resources.requests.memory | default "128Mi" -}}
resources:
  requests:
    cpu: {{ include "pod-rightsizing.enforceMin" (dict "kind" "cpu" "user" $userCpu "min" "100m") }}
    memory: {{ include "pod-rightsizing.enforceMin" (dict "kind" "memory" "user" $userMemory "min" "128Mi") }}
{{- with $resources.limits }}
  limits:
    {{- toYaml . | nindent 4 }}
{{- end }}
{{- end -}}

{{/*
Guardian resources with minimum values enforced
*/}}
{{- define "pod-rightsizing.guardian.resources" -}}
{{- $resources := .Values.guardian.resources | default dict -}}
{{- $userCpu := $resources.requests.cpu | default "100m" -}}
{{- $userMemory := $resources.requests.memory | default "128Mi" -}}
resources:
  requests:
    cpu: {{ include "pod-rightsizing.enforceMin" (dict "kind" "cpu" "user" $userCpu "min" "100m") }}
    memory: {{ include "pod-rightsizing.enforceMin" (dict "kind" "memory" "user" $userMemory "min" "128Mi") }}
{{- with $resources.limits }}
  limits:
    {{- toYaml . | nindent 4 }}
{{- end }}
{{- end -}}
