# Zesty Kompass

> Redefining the boundaries of Kubernetes optimization

This is the Helm chart used to installing Kompass and its
various subsystems.

## Subsystems

For the values of the various subsystems please refer to each
of them separately:

1. [Insights](https://github.com/zesty-co/kompass-insights)
2. [Pod Rightsizing](https://github.com/zesty-co/kompass-pod-rightsizing)
3. [Disk](https://github.com/zesty-co/zesty-helm)

## Prerequisuites

1. Follow the guidelines to onboard with Zesty in the [docs](https://docs.zesty.co/docs/home-page).
2. Have the following tools:
    - [Helm](https://helm.sh/docs/intro/install/)
    - [Kubectl](https://kubernetes.io/docs/tasks/tools/)
3. Make sure your context is set to the appropriate cluster

## Installation

1. Add the Kompass helm chart repo to your client configuration
```sh
helm repo add kompass https://zesty-co.github.io/kompass
helm repo update
```
2. Search the repo to make sure it's set up
```
$ helm search repo kompass
NAME                    CHART VERSION   APP VERSION     DESCRIPTION
kompass/kompass         0.1.8           1.16.0          Helm chart for Kompass
```
3. Install the chart
```sh
helm install kompass kompass/kompass --namespace zesty-system --create-namespace -f values.yaml
```

## Uninstalling
```sh
helm delete kompass
```


## Storage configuration

Kompass does not require a StorageClass named `ebs-sc`. With no per-component
overrides, PVCs use the cluster default; a suitable provisioner must exist.
The validator checks actual enabled components, including Grafana, instead of
assuming that `global.storageClassName` has propagated through YAML anchors.

YAML anchors are expanded before Helm merges values files. A later override of
only `global.storageClassName` does not update third-party chart settings. Use
an overlay that sets the component values explicitly:

```yaml
global:
  storageClassName: &storageClass gp3
kompass-insights:
  persistence:
    spec:
      storageClassName: *storageClass
victoriaMetrics:
  server:
    persistentVolume:
      storageClassName: *storageClass
victoriaMetricsCluster:
  vmstorage:
    persistentVolume:
      storageClassName: *storageClass
  vmselect:
    persistentVolume:
      storageClassName: *storageClass
grafana:
  persistence:
    storageClassName: *storageClass
```

Set the anchor to `null` to clear old generated storage choices on a new install.
Existing bound PVCs generally cannot change StorageClass in place; preserve their
class during upgrades and migrate data separately if necessary. Component
settings are authoritative. The chart does not implement dynamic global storage
inheritance across upstream dependencies.

The Insights PVC template omits a null StorageClass on fresh installs and keeps
the API-assigned class during upgrades when no explicit class is configured.
This avoids attempting to clear an immutable field on existing bound volumes.
