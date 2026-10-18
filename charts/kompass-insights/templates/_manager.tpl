{{- define "zesty-k8s.manager.container" -}}
- name: manager
  image: "{{ include "zesty-k8s.imageRepository" (dict "repository" .Values.manager.repository "registry" .Values.global.zestyImageRegistry) }}:{{ .Values.manager.tag | default (include "zesty-k8s.version" .) }}"
  imagePullPolicy: {{ .Values.manager.pullPolicy }}
  {{- with .Values.manager.extraArgs }}
  args:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  {{- with include "zesty-k8s.workload.extractContainerSecurityContext" (dict
    "context" (mergeOverwrite (deepCopy (.Values.manager.securityContext | default dict)) (.Values.global.securityContext | default dict))
    "path" "manager.securityContext"
  ) | fromYaml }}
  securityContext:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  env:
    - name: ZESTY_SECRET_NAME
      value: {{ .Values.insights.secret }}
    - name: LICENSE_SECRET_NAME
      value: {{ .Values.global.license.secretName | quote }}
    - name: LICENSE_DOCUMENT_KEY
      value: {{ .Values.global.license.documentKey | quote }}
    - name: IMAGE_PREFIX
      valueFrom:
        configMapKeyRef:
          name: "{{ include "zesty-k8s.configmap" . }}"
          key: IMAGE_PREFIX
    - name: IMAGE_PULL_SECRET_NAME
      valueFrom:
        configMapKeyRef:
          name: "{{ include "zesty-k8s.configmap" . }}"
          key: IMAGE_PULL_SECRET_NAME
    - name: KOMPASS_CHART_VERSION
      value: {{ .Chart.Version }}
    - name: NAMESPACE
      valueFrom:
        fieldRef:
          fieldPath: metadata.namespace
    - name: NODE_NAME
      valueFrom:
        fieldRef:
          fieldPath: spec.nodeName
    - name: ORG_ID
      valueFrom:
        configMapKeyRef:
          name: "{{ include "zesty-k8s.configmap" . }}"
          key: ORG_ID
          optional: false
    - name: METADATA_ENABLED
      valueFrom:
        configMapKeyRef:
          name: "{{ include "zesty-k8s.configmap" . }}"
          key: METADATA_ENABLED
          optional: true
    - name: METADATA_PROVIDER
      valueFrom:
        configMapKeyRef:
          name: "{{ include "zesty-k8s.configmap" . }}"
          key: METADATA_PROVIDER
          optional: true
    - name: METADATA_ACCOUNTID
      valueFrom:
        configMapKeyRef:
          name: "{{ include "zesty-k8s.configmap" . }}"
          key: METADATA_ACCOUNTID
          optional: true
    - name: METADATA_REGION
      valueFrom:
        configMapKeyRef:
          name: "{{ include "zesty-k8s.configmap" . }}"
          key: METADATA_REGION
          optional: true
    - name: METADATA_CLUSTERNAME
      valueFrom:
        configMapKeyRef:
          name: "{{ include "zesty-k8s.configmap" . }}"
          key: METADATA_CLUSTERNAME
          optional: true
    - name: ZESTY_ROLE_ARN
      valueFrom:
        configMapKeyRef:
          name: "{{ include "zesty-k8s.configmap" . }}"
          key: ZESTY_ROLE_ARN
          optional: true
    {{- include "zesty-k8s.manager.coralogix.envs" . | nindent 4 }}
  {{- $reservedManagerEnvNames := list "LICENSE_SECRET_NAME" "LICENSE_DOCUMENT_KEY" "IMAGE_PREFIX" "IMAGE_PULL_SECRET_NAME" }}
  {{- range .Values.manager.env }}
    {{- if not (has .name $reservedManagerEnvNames) }}
    {{- toYaml (list .) | nindent 4 }}
    {{- end }}
  {{- end }}
  {{- with .Values.manager.envFrom }}
  envFrom:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  {{- range $probe := list "startup" "readiness" "liveness" }}
  {{ $probe }}Probe:
    exec:
      command: ["/bin/kompass-manager", "healthcheck", {{ $probe | quote }}]
    {{- pick (index $.Values.manager.probes $probe) "initialDelaySeconds" "periodSeconds" "timeoutSeconds" "failureThreshold" "successThreshold" "terminationGracePeriodSeconds" | toYaml | nindent 4 }}
  {{- end }}
  resources:
    {{- toYaml .Values.manager.resources | nindent 4 }}
  volumeMounts:
    - name: manager-health
      mountPath: /var/run/kompass-manager
    {{- with .Values.manager.extraVolumeMounts }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
{{- end -}}
