# pod\-rightsizing release notes

Version: v0.9.6 → v0.10.0

## Changelog

### Features

- **Rightsizing:** feat: send saving to bridge

### Bug fixes

- **Rightsizing:** fix: retry Guardian recovery workload updates on conflict
- **Rightsizing:** fix: preserve virtual workload group types in snapshots
- **Rightsizing:** fix: add missing job and cronjob permissions to guardian

### Other changes

- **Rightsizing:** Updated values.yaml key \`jvmConfig.jvmHeapTargetEnvVar\`.
- **Rightsizing:** Improve Workloads dashboard performance
- **Rightsizing:** Updated values.yaml key \`additionalSupportedKinds\`.
- **Rightsizing:** replace wildcard manager reads with supported\-kind RBAC
- **Rightsizing:** Apply JVM heap targets with append\-only injection
- **Rightsizing:** Update dashboard default time ranges and refresh intervals
- **Rightsizing:** Use Action metric for workload policy columns
