# kompass release notes

Version: 0.4.11 → 0.5.0

## Changelog

### Features

- **Rightsizing:** feat: add failure condition to explain why an action failed

### Other changes

- **Insights Agent:** Added templates/aws\-auth\-rbac.yaml.
- **Chart and configuration:** Updated Chart.yaml key \`dependencies\`.
- **Insights Agent:** Updated templates/monitoring/cluster\_role.yaml.
- **Rightsizing:** Updated crds/rightsizing.kompass.zesty.co\_actions.yaml key \`spec.versions\`.
- **Rightsizing:** Preserve workload baselines for InPlace replacement pods
- **Chart and configuration:** Updated templates/bridge/role.yaml.
- **Insights Agent:** Updated templates/role.yaml.
- **Insights Agent:** Added templates/rosa\-metadata\-rbac.yaml.
- **Chart and configuration:** Updated values.yaml key \`global.supportedKinds\`.
- **Rightsizing:** protect managed HPA settings with opt\-in webhook
- **Rightsizing:** Updated values.yaml key \`rightsizing.config.kompassWorkloadsRightsizing.enabled\`.
- **Insights Agent:** Updated templates/clusterRole.yaml.
- **Rightsizing:** Updated values.yaml key \`actionTaker.webhooks.hpa.enabled\`.
- **Rightsizing:** Updated crds/rightsizing.kompass.zesty.co\_clusteractions.yaml key \`spec.versions\`.
- **Chart and configuration:** Updated values.yaml key \`global.additionalSupportedKinds\`.
- **Chart and configuration:** Updated values.yaml key \`global.guardian.enabled\`.
