# kompass release notes

Version: 0.5.0 → 0.6.3

## What's new

- **Recommendations-only rightsizing.** With `rightsizing.enabled: false`, rightsizing has no
  chart-granted permissions to change customer workloads, Pods, HPAs or KEDA objects.
  Recommendations keep working. Pod Placement has independent permissions.
- **Shared read scope.** `global.readScope` applies to both the Kompass Agent and rightsizing:
    - `cluster` (default) reads all resources, the same as before.
    - `supportedKinds` removes wildcard reads.
      It grants supported-kind and explicit discovery reads.
      Discovery permissions include resources outside the supported-kind lists.
      With chart-provided bindings only, Secret reads are limited to the Kompass namespace.
- **One list of workload kinds.** Add custom workload kinds once, in
  `global.additionalSupportedKinds`. The Kompass Agent and rightsizing share this list.
- **Fewer permissions.** Rightsizing no longer deletes Pods; it evicts them instead, and only when
  rightsizing is on. Guardian's namespace-wide wildcard read rule has been removed.

## ⚠️ Before you upgrade

Two settings were removed. **Helm ignores them silently**, so move them before you upgrade:

| If you set | Set instead | If you don't |
|---|---|---|
| `kompass-insights.insights.clusterRole.fullRO: false` | `global.readScope: supportedKinds` | Zesty Compute Optimization can read every resource in the cluster again, including Secrets. |
| `rightsizing.additionalSupportedKinds` | Merge the same entries into `global.additionalSupportedKinds` | Rightsizing no longer uses entries from the old key. |

Check your current values. Replace `<release>` and `<namespace>` with your installation's values:

```bash
helm get values <release> -n <namespace> -o yaml \
  | yq '{"fullRO": .["kompass-insights"].insights.clusterRole.fullRO, "rightsizingKinds": .rightsizing.additionalSupportedKinds}'
```

Example migration. Keep existing global entries and remove duplicates:

```yaml
global:
  readScope: supportedKinds          # was kompass-insights.insights.clusterRole.fullRO: false
  additionalSupportedKinds:          # was rightsizing.additionalSupportedKinds
    - Group: example.com
      Version: v1
      Kind: Widget
      Resource: widgets              # set when the plural isn't Kind + "s"
      Alias: widget
      Properties: [Virtual]
```

- **With `readScope: supportedKinds`, wildcard reads are removed.** Explicit discovery reads remain.
  Add your custom workload kinds to `global.additionalSupportedKinds`.
  Set `Resource` if its name differs from lowercase `Kind` plus "s".
- **With rightsizing on**, the default supported kinds now include Argo Workflows and Spark
  applications, so rightsizing can update them.

## Chart changes

### Features

- **Chart and configuration:** Added `global.readScope` (`cluster` or `supportedKinds`), applied to
  the Kompass Agent and rightsizing.
- **Chart and configuration:** The Kompass Agent and rightsizing both use `global.supportedKinds`
  and `global.additionalSupportedKinds`.
- **Rightsizing:** Chart-granted write permissions on customer workloads require
  `rightsizing.enabled: true`.
- **Rightsizing:** Report savings from applied actions to Kompass Bridge.
- **Rightsizing:** JVM rightsizing can apply heap targets through an environment variable
  (`rightsizing.jvmConfig.jvmHeapTargetEnvVar`, default `JAVA_TOOL_OPTIONS`).

### Changes

- **Rightsizing:** Removed permission to delete Pods.
  Leases are managed only in the Kompass namespace.
- **Rightsizing:** With `global.readScope: supportedKinds`, chart-provided Secret reads are limited
  to the Kompass namespace. The default `cluster` scope permits wildcard reads, including Secrets.
- **Guardian:** Removed the namespace-wide wildcard read rule.
- **Chart and configuration:** Updated `kompass-insights` to 2.3.36 and
  `pod-rightsizing` to v0.10.0.

### Removed

- **Insights Agent:** `kompass-insights.insights.clusterRole.fullRO`. Use `global.readScope`.
- **Rightsizing:** `rightsizing.additionalSupportedKinds`. Use `global.additionalSupportedKinds`.

## Changelog

### Features

- **Rightsizing:** feat: send saving to bridge

### Bug fixes

- **Rightsizing:** fix: retry Guardian recovery workload updates on conflict
- **Rightsizing:** fix: preserve virtual workload group types in snapshots
- **Rightsizing:** fix: add missing job and cronjob permissions to guardian
- **Insights Agent:** fix: resolve Oracle pricing from canonical shape labels

### Other changes

- **Rightsizing:** Updated values.yaml key \`jvmConfig.jvmHeapTargetEnvVar\`.
- **Rightsizing:** Improve Workloads dashboard performance
- **Rightsizing:** Updated values.yaml key \`additionalSupportedKinds\`.
- **Insights Agent:** Updated values.yaml key \`insights.clusterRole.fullRO\`.
- **Insights Agent:** Updated values.yaml key \`gcpBilling.project\`.
- **Chart and configuration:** Updated values.yaml key \`global.readScope\`.
- **Rightsizing:** replace wildcard manager reads with supported\-kind RBAC
- **Insights Agent:** Updated values.yaml key \`gcpBilling.table\`.
- **Chart and configuration:** Added values.schema.json.
- **Insights Agent:** Updated values.yaml key \`gcpBilling.location\`.
- **Rightsizing:** Apply JVM heap targets with append\-only injection
- **Rightsizing:** Update dashboard default time ranges and refresh intervals
- **Insights Agent:** Updated values.yaml key \`gcpBilling.enabled\`.
- **Rightsizing:** Use Action metric for workload policy columns
