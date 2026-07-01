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

## Configuration

### Value precedence: global vs component

Many settings can be configured either globally (`global.*`) or per component (e.g. `insights.*`,
`recommendations.*`). **Global values take precedence over component values** — this lets a cluster
operator enforce a setting uniformly from one place, and a component's own value (or built-in default)
cannot override what is set under `global`.

Merge behavior by type:
- **Maps** (e.g. `podSecurityContext`, `podLabels`): deep-merged per key — global wins on conflicting
  keys; component-only keys are preserved.
- **Lists** (e.g. `tolerations`, `imagePullSecrets`): replaced entirely by the global list when set.
- **Scalars** (booleans/strings): the global value is used when explicitly set, otherwise the component value.

Resolution order, lowest to highest: chart default → component value → global value.

### OpenShift

The chart auto-detects OpenShift via its API groups (`security.openshift.io/v1`). On OpenShift it omits
its default pod-level `securityContext` UID/group/seccomp fields so the platform's SCC can assign them,
avoiding admission failures from hardcoded UIDs. Control detection with `global.openShift`:

- unset / `~` (default): auto-detect.
- `true`: force OpenShift behavior (also needed for `helm template`, where API detection is unavailable).
- `false`: force standard behavior even on an OpenShift cluster.

Any `securityContext` values you supply explicitly are always applied, on any platform.

#### kube-state-metrics on OpenShift

`kube-state-metrics` is a third-party dependency that hardcodes its own pod-level `securityContext`
(UID/GID `65534`) independently of `global.openShift`. Its internal toggle must be disabled explicitly:

```yaml
# openshift-values.yaml
kubeStateMetrics:
  securityContext:
    enabled: false
```

With `securityContext.enabled: false`, kube-state-metrics emits no pod-level `securityContext` and
the cluster's SCC assigns the UID automatically.

