# Insights RBAC

`insights.clusterRole.fullRO` defaults to `false`. The default Insights
ClusterRole grants explicit resource permissions without wildcard Secret reads.
On OpenShift, it also grants the named discovery reads described below.
Insights and Manager share this identity. Their namespaced Role permits
Secret access for runtime identity, licensing, and debugging.

Append native Kubernetes PolicyRules using `insights.clusterRole.extraRules`:

```yaml
insights:
  clusterRole:
    extraRules:
      - apiGroups: ["example.com"]
        resources: ["customworkloads"]
        verbs: ["get"]
```

For the umbrella chart, place that configuration under `kompass-insights`:

```yaml
kompass-insights:
  insights:
    clusterRole:
      extraRules:
        - apiGroups: ["example.com"]
          resources: ["customworkloads"]
          verbs: ["get"]
```

Extensions are additive in both modes and preserve fields such as
`resourceNames`, subresource names, and `nonResourceURLs`. They do not install
CRDs or configure informers. Custom workload-owner traversal needs `get` on the
encountered resource. An omitted, empty, or null extension list adds no rules.

Setting `fullRO: true` explicitly restores wildcard `get/list/watch`, including
Secrets. Existing explicit operational grants also include writes; this setting
controls the additional wildcard read rule.

## Metadata discovery compatibility

When Helm discovers `config.openshift.io/v1/Infrastructure`, the chart
automatically adds these named `get` permissions for Manager's ROSA fallbacks.
No additional values setting is required. Detection applies to all OpenShift
clusters, not only ROSA, and works in both `fullRO` modes.

| API group | Resource | Name | Manager's target namespace | Verb |
| --- | --- | --- | --- | --- |
| `""` | secrets | ebs-cloud-credentials | openshift-cluster-csi-drivers | get |
| config.openshift.io | infrastructures | cluster | Cluster-scoped | get |

The Secret grant applies to that name in every namespace: `resourceNames`
restricts names, not namespaces. On clusters without the Infrastructure API,
these rules are omitted. Explicit cloud metadata bypasses Manager's discovery
reads but does not change which RBAC rules the chart renders.

For offline rendering, supply the capability explicitly:

```bash
helm template kompass charts/kompass-insights \
  --api-versions=config.openshift.io/v1/Infrastructure
```

The same flag applies when rendering the umbrella chart. Rendering systems must
provide the target cluster's API capabilities for automatic detection to work.
Upgrades retaining an explicitly configured `fullRO: true` continue to grant
wildcard reads.
