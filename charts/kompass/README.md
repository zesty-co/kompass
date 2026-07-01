# VictoriaMetrics topology selection

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

## OpenShift / OKD image pull secrets

Do not set `global.imagePullSecrets` on OpenShift or OKD. OpenShift manages
`ServiceAccount.imagePullSecrets` through its service account controller, so Helm
server-side apply can fail with a field ownership conflict when subcharts render
the same field on ServiceAccounts.

Keep the global value empty and configure pull secrets only on Kompass workloads
that render pod-level `imagePullSecrets`:

```yaml
zestyImagePullSecrets: &zestyImagePullSecrets
  - name: zesty-ecr
  - name: zesty-ecr-stg

global:
  imagePullSecrets: []

kompass-insights:
  imagePullSecrets: *zestyImagePullSecrets
  insights:
    imagePullSecrets: *zestyImagePullSecrets
  recommendations:
    imagePullSecrets: *zestyImagePullSecrets
  selfMonitoring:
    imagePullSecrets: *zestyImagePullSecrets

kompass-pod-placement:
  imagePullSecrets: *zestyImagePullSecrets

kompass-bridge:
  imagePullSecrets: *zestyImagePullSecrets

validator:
  imagePullSecrets: *zestyImagePullSecrets

victoriaMetricsMigration:
  imagePullSecrets: *zestyImagePullSecrets
```

If you upgrade with reused values, make sure the old global value is removed.
Either use `--reset-values` or explicitly keep `global.imagePullSecrets: []` in
the OKD values file:

```bash
helm upgrade kompass ./charts/kompass -n zesty-system -f charts/kompass/okd.yaml --reset-values
```

For third-party charts or subcomponents that only support pull secrets through a
ServiceAccount, let OpenShift manage the ServiceAccount field instead of Helm:

```bash
oc -n zesty-system secrets link kompass-cert-manager zesty-ecr zesty-ecr-stg --for=pull
oc -n zesty-system secrets link kompass-cert-manager-cainjector zesty-ecr zesty-ecr-stg --for=pull
oc -n zesty-system secrets link kompass-cert-manager-webhook zesty-ecr zesty-ecr-stg --for=pull
oc -n zesty-system secrets link kompass-kube-state-metrics zesty-ecr zesty-ecr-stg --for=pull
oc -n zesty-system secrets link admission-kompass-admission-controller-sa zesty-ecr zesty-ecr-stg --for=pull
```

## Using pre-existing kube-state-metrics

When you already run kube-state-metrics (KSM), point Kompass to that service instead of installing KSM from this chart:

```yaml
kubeStateMetrics:
  enabled: false
  serviceName: kube-state-metrics
  serviceNamespace: monitoring
```

`kompass_rs_action_info` is produced by KSM `customResourceState` (not by vmagent), so your external KSM must include the Action CRD metric config:

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
          labelsFromPath:
            namespace: [metadata, namespace]
            policy: [spec, policy]
            horizontal_scaling_policy: [spec, horizontalScalingPolicy]
            workload_name: [spec, workload, name]
            action_type: [spec, actionType]
            source_apc: [spec, sourceAPC]
            execution_method: [spec, executionMethod]
          errorLogV: 10
          metrics:
            - name: action_info
              help: "Kompass Rightsizing action CRD info"
              each:
                type: Gauge
                gauge:
                  path: [metadata, generation]
```

Your external KSM also needs RBAC to list/watch the Action CRD:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kube-state-metrics-kompass-actions
rules:
  - apiGroups: ["rightsizing.kompass.zesty.co"]
    resources: ["actions"]
    verbs: ["list", "watch"]
```
