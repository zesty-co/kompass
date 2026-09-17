# Kompass Pod Rightsizing Helm Chart

## Overview

Kompass Pod Rightsizing is a Kubernetes resource optimization solution that helps with pod rightsizing. It consists of two main components:

1. **Recommendations Maker**: Analyzes resource usage patterns and generates optimization recommendations
2. **Automator** (Action Taker): Implements the recommendations by adjusting resource allocations
   The solution integrates with Victoria Metrics (via kube-state-metrics) to make data-driven decisions about resource optimization.

## Architecture

The Kompass Pod Rightsizing solution does the following:

1. Collects metrics from your K8s cluster using kube-state-metrics
2. Analyzes resource usage patterns using the Recommendations Maker
3. Implements optimizations using the Action Taker component
4. [Optional] Provides visibility into recommendations and actions through Grafana dashboards

## Prerequisites

- Kubernetes 1.16+
- Helm 3.0+

## Installation

Follow the installation instructions of [Kompass](https://github.com/zesty-co/kompass).

## Add Workloads for Pod Rightsizing

To enable Pod Rightsizing for specific workloads, create or update a `Policy` Custom Resource under the `spec` section.

### Important Notes

1. `applist` **Format:**
   1. `appList` is a list where you need to add a separate item for each workload you want to right-size.
   2. Only include the following fields for each workload: `kind`, `name`, `namespace`.
2. **Configuration Example:**

```yaml
appList:
  - kind: <YOUR_WORKLOAD_KIND>
    name: <YOUR_WORKLOAD_NAME>
    namespace: <YOUR_WORKLOAD_NAMESPACE>
```

1. **Remove Workloads:**
   To exclude a workload from Pod Rightsizing, delete the corresponding entry from the `appList` in the `Policy` CR.
2. **Multiple Configurations:**
   If a workload exists in more than one `Policy`, the configuration with the highest priority will be applied to the workload.
   Lower numbers indicate higher priority (e.g., `0` is the highest priority).

## Configuration Options

The following table lists the configurable parameters of the Kompass Pod Rightsizing chart and their default values.

### Global Configuration

| Parameter          | Description                          | Default    |
| ------------------ | ------------------------------------ | ---------- |
| `nameOverride`     | Override the name of the chart       | `""`       |
| `fullnameOverride` | Override the full name of the chart  | `""`       |
| `imagePullPolicy`  | Image pull policy for all containers | `"Always"` |
| `global.imagePullSecret.name` | Adds a single global image pull secret entry (`- name: ...`) for all workloads | `""` |
| `global.imagePullSecret.dockerconfigjson` | Creates a hook-scoped pull secret before hook Jobs run | `""` |
| `global.imagePullSecrets` | Additional global image pull secrets for all workloads | `[]` |
| `global.podLabels` | Global pod template labels merged into each component pod template | `{}` |
| `global.podAnnotations` | Global pod template annotations merged into each component pod template | `{}` |
| `global.workloadLabels` | Global workload labels merged into each component workload template | `{}` |
| `global.affinity` | Global pod affinity merged into each component workload | `{}` |
| `global.topologySpreadConstraints` | Global topology spread constraints (wins over component values when non-empty) | `[]` |
| `global.runtimeClassName` | Global runtime class name override for all workloads (wins over component values when set) | `""` |
| `global.automountServiceAccountToken` | Global automount service account token override (hasKey semantics; explicit `false` is honored) | unset |
| `global.podSecurityContext` | Global pod-level security context override for all workloads | `{}` |
| `global.securityContext` | Global container-level security context override for all containers | `{}` |

Precedence policy for overlapping keys is explicit: **global values win over component values**.

Security context precedence (merge order, later wins):
- Pod `spec.securityContext`: `component.podSecurityContext -> global.podSecurityContext`
- Container `securityContext`:
  - `actionTaker`: `actionTaker.securityContext -> global.securityContext`
  - `actionTaker.kubeRbacProxy`: `actionTaker.securityContext -> actionTaker.kubeRbacProxy.securityContext -> global.securityContext` (global still wins overall)
  - `guardian` / `recommendationsMaker` / `metricsExporter`: `component.securityContext -> global.securityContext`

Pod template and scheduling precedence:
- Maps (`podLabels`, `podAnnotations`, `affinity`): `component + global` (global wins on key conflict)
- Lists (`imagePullSecrets`, `topologySpreadConstraints`): component value is used unless global list is non-empty; when global is non-empty it wins
- String (`runtimeClassName`): component value is used unless global value is non-empty; when global is non-empty it wins
- Boolean (`automountServiceAccountToken`): component value is used unless global key exists; explicit `false` is honored via `hasKey`

Image pull secret behavior:
- Global list is built as: `[{name: global.imagePullSecret.name}] + global.imagePullSecrets` (if `global.imagePullSecret.name` is set)
- If this combined global list is non-empty, it is used for all workloads and overrides component and legacy root-level `imagePullSecrets`
- If the combined global list is empty, precedence is: component `imagePullSecrets` -> legacy root-level `imagePullSecrets`
- Hook Jobs use the same precedence; when `global.imagePullSecret.dockerconfigjson` is set, the first global secret is rendered as `<name>-rightsizing-hook` and created before hook Jobs run

### Service Account Configuration

| Parameter             | Description                 | Default                 |
| --------------------- | --------------------------- | ----------------------- |
| `serviceAccount.name` | Name of the service account | `"zesty-kompass-rightsizing"` |
| `guardianServiceAccount.name` | Name of the dedicated Guardian service account | `"zesty-kompass-guardian"` |

### Bridge Actor Configuration

| Parameter          | Description                                           | Default |
| ------------------ | ----------------------------------------------------- | ------- |
| `bridgeActor.port` | Port used by the pprof bridge actor container/runtime | `50052` |

### Action Taker Configuration

| Parameter                | Description                        | Default                           |
| ------------------------ | ---------------------------------- | --------------------------------- |
| `actionTaker.name`       | Name of the action taker component | `"action-taker"`                  |
| `actionTaker.image.name` | Image name for action taker        | `"/pod-rightsizing/action-taker"` |
| `actionTaker.image.tag`  | Image tag for action taker         | `"latest"`                        |
| `actionTaker.runtimeClassName` | Component runtime class name (global wins when set) | `""` |
| `actionTaker.imagePullSecrets` | Component image pull secrets (global wins when non-empty) | `[]` |
| `actionTaker.podLabels` | Component pod template labels merged with global | `{}` |
| `actionTaker.podAnnotations` | Component pod template annotations merged with global | `{}` |
| `actionTaker.workloadLabels` | Component workload labels merged with global | `{}` |
| `actionTaker.affinity` | Component affinity merged with global and the built-in default affinity | `{}` |
| `actionTaker.topologySpreadConstraints` | Component topology spread constraints (global wins when non-empty) | `[]` |
| `actionTaker.automountServiceAccountToken` | Component automount service account token control (explicit `false` honored) | unset |
| `actionTaker.webhooks.application.enabled` | Enable the Argo `Application` mutating webhook registration and manifest | `true` |
| `actionTaker.webhookService.selector` | Selector labels for the webhook service | `{"control-plane":"controller-manager","app.kubernetes.io/name":"pod-rightsizing"}` |
| `actionTaker.podSecurityContext` | Pod security context for action taker | `{"runAsNonRoot":true}` |
| `actionTaker.securityContext` | Main container security context for action taker | `{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}` |
| `actionTaker.kubeRbacProxy.securityContext` | kube-rbac-proxy-specific override on top of `actionTaker.securityContext` | `{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}` |

### Guardian Configuration

Guardian resources render only when `guardian.enabled` is `true`; they are not controlled by the root `enabled` or `config.kompassWorkloadsRightsizing.enabled` values. The chart mounts the shared `kompass-rightsizing-config` and the Helm-owned static `kompass-guardian-config`. Runtime Guardian params and store ConfigMaps are not rendered or owned by Helm.

The static `kompass-guardian-config` contains these installation defaults: `cadvisorScrapeInterval=15s`, `cadvisorMaxConcurrentScrapes=4`, `cpuThrottlingRatio=0.25`, `cpuThrottlingConsecutiveWindows=3`, `cpuRequestGrowthFactor=1.25`, `memoryRequestGrowthFactor=1.25`, `cpuRequestToLimitFactor=1.2`, `memoryRequestToLimitFactor=1.2`, `stabilizationWindow=10m`, and `recoveryApplyTimeout=5m`.

| Parameter | Description | Default |
| --------- | ----------- | ------- |
| `guardian.enabled` | Render Guardian resources | `false` |
| `guardian.image.name` | Guardian image name | `"/pod-rightsizing/guardian"` |
| `guardian.image.tag` | Guardian image tag | `"latest"` |
| `guardian.replicaCount` | Guardian replica count | `1` |
| `guardian.runtimeClassName` | Component runtime class name (global wins when set) | `""` |
| `guardian.imagePullSecrets` | Component image pull secrets (global wins when non-empty) | `[]` |
| `guardian.podLabels` | Component pod template labels merged with global | `{}` |
| `guardian.podAnnotations` | Component pod template annotations merged with global | `{}` |
| `guardian.workloadLabels` | Component workload labels merged with global | `{}` |
| `guardian.affinity` | Component affinity merged with global | `{}` |
| `guardian.topologySpreadConstraints` | Component topology spread constraints (global wins when non-empty) | `[]` |
| `guardian.automountServiceAccountToken` | Component automount service account token control (explicit `false` honored) | unset |
| `guardian.podSecurityContext` | Guardian pod security context | `{"runAsNonRoot":true,"seccompProfile":{"type":"RuntimeDefault"}}` |
| `guardian.securityContext` | Guardian container security context | `{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]},"seccompProfile":{"type":"RuntimeDefault"}}` |

### Recommendations Maker Configuration

| Parameter                         | Description                                 | Default                                    |
| --------------------------------- | ------------------------------------------- | ------------------------------------------ |
| `recommendationsMaker.name`       | Name of the recommendations maker component | `"recommendations-maker"`                  |
| `recommendationsMaker.image.name` | Image name for recommendations maker        | `"/pod-rightsizing/recommendations-maker"` |
| `recommendationsMaker.image.tag`  | Image tag for recommendations maker         | `"latest"`                                 |
| `recommendationsMaker.port`       | Port for the recommendations maker service  | `8088`                                     |
| `recommendationsMaker.runtimeClassName` | Component runtime class name (global wins when set) | `""` |
| `recommendationsMaker.imagePullSecrets` | Component image pull secrets (global wins when non-empty) | `[]` |
| `recommendationsMaker.podLabels` | Component pod template labels merged with global | `{}` |
| `recommendationsMaker.podAnnotations` | Component pod template annotations merged with global | `{}` |
| `recommendationsMaker.workloadLabels` | Component workload labels merged with global | `{}` |
| `recommendationsMaker.affinity` | Component affinity merged with global | `{}` |
| `recommendationsMaker.topologySpreadConstraints` | Component topology spread constraints (global wins when non-empty) | `[]` |
| `recommendationsMaker.automountServiceAccountToken` | Component automount service account token control (explicit `false` honored) | unset |
| `recommendationsMaker.podSecurityContext` | Pod security context for recommendations maker | `{}` |
| `recommendationsMaker.securityContext` | Main container security context for recommendations maker | `{}` |

### Metrics Exporter Configuration

| Parameter                         | Description                                 | Default                                    |
| --------------------------------- | ------------------------------------------- | ------------------------------------------ |
| `metricsExporter.podSecurityContext` | Pod security context for metrics exporter | `{}` |
| `metricsExporter.securityContext` | Main container security context for metrics exporter | `{}` |
| `metricsExporter.runtimeClassName` | Component runtime class name (global wins when set) | `""` |
| `metricsExporter.imagePullSecrets` | Component image pull secrets (global wins when non-empty) | `[]` |
| `metricsExporter.podLabels` | Component pod template labels merged with global | `{}` |
| `metricsExporter.podAnnotations` | Component pod template annotations merged with global | `{}` |
| `metricsExporter.workloadLabels` | Component workload labels merged with global | `{}` |
| `metricsExporter.affinity` | Component affinity merged with global | `{}` |
| `metricsExporter.topologySpreadConstraints` | Component topology spread constraints (global wins when non-empty) | `[]` |
| `metricsExporter.automountServiceAccountToken` | Component automount service account token control (explicit `false` honored) | unset |

### Pod Rightsizing ConfigMap

| Parameter                   | Description                           | Default                                              |
| --------------------------- | ------------------------------------- | ---------------------------------------------------- |
| `podRightsizingConfig.name` | Name of the pod rightsizing ConfigMap | `""` (uses default "kompass-pod-rightsizing-config") |

### Cert Manager Configuration

| Parameter                   | Description                      | Default |
| --------------------------- | -------------------------------- | ------- |
| `cert-manager.enabled`      | Enable cert-manager installation | `true`  |
| `cert-manager.namespace`    | Namespace for cert-manager       | \`\`    |
| `cert-manager.crds.enabled` | Enable cert-manager CRDs         | `true`  |

## Monitoring and Dashboards

Kompass Pod Rightsizing includes Grafana dashboards for monitoring the performance and recommendations of the system. These dashboards are automatically installed when the `grafana.enabled` parameter is set to `true`.

## Troubleshooting

### Common Issues

1. **Recommendations are not being generated**:
   1. Ensure kube-state-metrics is properly configured
   2. Check the logs of the recommendations-maker pod
2. **Actions are not being taken**:
   1. Verify the action-taker has proper permissions
   2. Check the logs of the action-taker pod
3. **Service account issues**:
   1. The default service account name is "kompass-rightsizing"
   2. You can customize it using `serviceAccount.name`
   3. Make sure the service account has the necessary RBAC permissions
