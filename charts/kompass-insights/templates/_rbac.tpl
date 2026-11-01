{{- define "zesty-k8s.rosaDiscoveryRules" -}}
- apiGroups: ["config.openshift.io"]
  resources: ["infrastructures"]
  resourceNames: ["cluster"]
  verbs: ["get"]
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["ebs-cloud-credentials"]
  verbs: ["get"]
{{- end -}}
