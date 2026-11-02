# VictoriaMetrics topology selection

## Product recording rules

The spoke chart mounts the base recording rules ConfigMap at `/config` and
projects product-owned recording-rules ConfigMaps into the shared
`/config/recording-rules` directory. `vmalert` uses flat `*.yaml` and `*.yml`
globs for both directories. Avoid recursive globs: Kubernetes ConfigMap
projected volumes expose timestamp and `..data` symlinks that recursive globs
can load more than once. Product ConfigMaps are optional so products can be
enabled independently. Use distinct YAML/YML data keys and unique rule-group
names across products.

The rightsizing chart publishes `kompass-vm-rightsizing-recording-rules` when
its `custom-recording-rules/` files contain rules. Its `rightsizing.yaml` is
currently empty, so the existing Rightsizing rules continue to come from the
base ConfigMap. The spoke also reserves `kompass-vm-insights-recording-rules`
and `kompass-vm-pod-placement-recording-rules` for those product charts.

This chart can run VictoriaMetrics in one of two modes and route all traffic through VMAuth:

- Single-node (vmsingle)
- Cluster (vmselect/vminsert/vmstorage)

Pick the mode via `victoriaMetricsAuth.useSingle` and enable exactly one backend:

## Option A — Single-node

```yaml
victoriaMetricsAuth:
  useSingle: true

victoriaMetrics:
  enabled: true

victoriaMetricsCluster:
  enabled: false
```

## Option B — Cluster

```yaml
victoriaMetricsAuth:
  useSingle: false

victoriaMetrics:
  enabled: false

victoriaMetricsCluster:
  enabled: true
```

## Notes

- VMAuth is the client-facing endpoint. Use the global URLs:
  - `global.victoriaMetricsRemoteUrl` (read/API)
  - `global.victoriaMetricsRemotePrometheusWriteUrl` (Prometheus remote_write)
- Service names used by internal routing are taken from `fullnameOverride` values and are required:
  - `victoriaMetrics.server.fullnameOverride`
  - `victoriaMetricsCluster.vmselect.fullnameOverride`
  - `victoriaMetricsCluster.vminsert.fullnameOverride`
- You can deploy both single-node and cluster VictoriaMetrics at the same time and use `victoriaMetricsAuth.useSingle` to route traffic to the correct one.

## Using pre-existing kube-state-metrics

When you already run kube-state-metrics (KSM), point Kompass to that service instead of installing KSM from this chart:

```yaml
kubeStateMetrics:
  enabled: false
  serviceName: kube-state-metrics
  serviceNamespace: monitoring
```

`kompass_rs_action_info` is produced by KSM `customResourceState`. External KSM must export both resource kinds with this configuration (the labels mirror this chart's values):

```yaml
customResourceState:
  enabled: true
  config:
    kind: CustomResourceStateMetrics
    spec:
      resources:
        - groupVersionKind:
            group: rightsizing.kompass.zesty.co
            kind: Action
            version: v1alpha1
          metricNamePrefix: kompass_rs
          commonLabels:
            cr_kind: Action
          labelsFromPath:
            namespace: [metadata, namespace]
            policy: [status, activations, rightsizing, policyName]
            horizontal_scaling_policy: [status, activations, horizontalScaling, policyName]
            rightsizing_policy: [status, activations, rightsizing, policyName]
            phase: [status, phase]
            workload_name: [spec, workload, name]
            workload_kind: [spec, workload, kind]
            action_type: [spec, actionType]
          errorLogV: 10
          metrics:
            - name: action_info
              help: "Current Kompass Action activation and workload identity; gauge is CR generation"
              each:
                type: Gauge
                gauge:
                  path: [metadata, generation]
        - groupVersionKind:
            group: rightsizing.kompass.zesty.co
            kind: ClusterAction
            version: v1alpha1
          metricNamePrefix: kompass_rs
          commonLabels:
            cr_kind: ClusterAction
            namespace: ""
          labelsFromPath:
            policy: [status, activations, rightsizing, policyName]
            horizontal_scaling_policy: [status, activations, horizontalScaling, policyName]
            rightsizing_policy: [status, activations, rightsizing, policyName]
            phase: [status, phase]
            workload_name: [spec, workload, name]
            workload_kind: [spec, workload, kind]
            action_type: [spec, actionType]
          errorLogV: 10
          metrics:
            - name: action_info
              help: "Current Kompass Action activation and workload identity; gauge is CR generation"
              each:
                type: Gauge
                gauge:
                  path: [metadata, generation]
```

Grant the external KSM service account this ClusterRole through your existing ClusterRoleBinding:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kube-state-metrics-kompass-actions
rules:
  - apiGroups: ["rightsizing.kompass.zesty.co"]
    resources: ["actions", "clusteractions"]
    verbs: ["list", "watch"]
```

One gauge per current CR uses `metadata.generation`; its numeric value is not an activation flag. `cr_kind` distinguishes Action from ClusterAction. `namespace` is explicitly empty for ClusterAction. `workload_kind`/`workload_name` identify the target; `phase`, `rightsizing_policy`, and `horizontal_scaling_policy` describe current status activations. The compatibility `policy` label also reads the rightsizing activation. Missing activation paths become empty labels. The intended Grafana consumer constructs `namespace;name;lowercase-kind` for Action and `name;lowercase-kind` for ClusterAction. Its intended activation precedence is: a `Completed` or `Failed` CR is Inactive, even if `rightsizing_policy` is nonempty; otherwise, a nonempty `rightsizing_policy` means Active; otherwise, an unactivated `Pending`/`InProgress` CR means Pending. An absent CR is Inactive. The Grafana consumer implementation is outside this repository, so its behavior has not been verified against this precedence. Deleted CRs cease to indicate management after ordinary scrape staleness.
