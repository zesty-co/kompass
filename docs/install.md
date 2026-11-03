# Install Kompass

Use this procedure to install a new Kompass Helm release with an existing Zesty-provided
values file.
An operator or an AI agent can follow these steps. The commands work in Bash and Zsh.

The values file must come from the Zesty installation wizard for the target cluster.
Complete provider onboarding before you start:

- [AWS EKS](https://docs.zesty.co/docs/install-the-insights-agent-aws-eks.md)
- [Azure AKS](https://docs.zesty.co/docs/install-the-insights-agent-azure-aks.md)

Use the supplied file as the installation configuration. Keep credential values out of terminal
output and chat. Rendered manifests and ConfigMaps can contain credentials, as well as Secrets.

## 1. Identify the installation inputs

Ask for the absolute path to the values file and the target Kubernetes context.
Ask whether Zesty supplied a chart version. Use that version when available.
The default release name is `kompass`, and the default namespace is `zesty-system`.

Replace the placeholders below. Keep these variables available for all subsequent commands.

```sh
VALUES_FILE='/absolute/path/to/customer-values.yaml'
KUBE_CONTEXT='replace-with-target-context'
RELEASE='kompass'
NAMESPACE='zesty-system'
```

Check the file, tools, cluster connection, and Helm releases:

```sh
test -r "$VALUES_FILE"
helm version --short
kubectl version --client
kubectl config get-contexts "$KUBE_CONTEXT"
kubectl --context "$KUBE_CONTEXT" cluster-info
helm list --kube-context "$KUBE_CONTEXT" --all-namespaces --all
```

Stop if a command fails. Resolve the missing prerequisite before you continue.
If Helm returns a full page of releases, use its `--offset` option to check the remaining pages.
If a Kompass release already exists, report its name, namespace, chart version, and status.
Stop this fresh-install procedure; an existing release needs a separate upgrade or recovery task.

Check that any cluster identity in the supplied values matches the selected context.
Use `--context` or `--kube-context` on every cluster command, as shown in this guide.

## 2. Check cluster prerequisites

The Kubernetes credentials must permit the chart's namespaced resources, cluster-scoped resources,
and installation hooks. These include CRDs and cluster roles.

Inspect storage and existing dependency deployments:

```sh
kubectl --context "$KUBE_CONTEXT" get storageclass
kubectl --context "$KUBE_CONTEXT" get deployments --all-namespaces
```

Compare these results with the non-secret settings in the values file:

- Check that each configured StorageClass exists. Check for a default class when a PVC uses it.
- Check existing kube-state-metrics and cert-manager deployments against the supplied settings.
- Check the names and namespaces of any pre-existing credential or image-pull Secrets.
- Check that the cluster can schedule the configured workloads and provision their storage.

Storage settings are specific to each component. An override of `global.storageClassName` does not
update every PVC through the chart's YAML anchors. See
[Helm's YAML anchor behavior](https://helm.sh/docs/chart_template_guide/yaml_techniques/#yaml-anchors).

An external kube-state-metrics service also needs the Kompass Action metric configuration and RBAC.
See
[`charts/kompass/README.md:64`](https://github.com/zesty-co/kompass/blob/main/charts/kompass/README.md#L64).

If the supplied settings conflict with the cluster, report the affected value paths and required
changes. Resolve the conflict before installation. A permission error does not establish that a
resource is absent.

## 3. Select a chart version and install

Add the public Helm repository and list the available Kompass chart versions:

```sh
helm repo add kompass https://zesty-co.github.io/kompass
helm repo update kompass
helm search repo kompass/kompass --versions
```

If the local `kompass` repository name points to another URL, resolve that conflict first.
Use rows whose `NAME` is exactly `kompass/kompass`; the results also include component charts.
Select the version supplied by Zesty.
If none was supplied, select the latest stable Kompass version.
Set the exact chart version below, then inspect its metadata:

```sh
CHART_VERSION='replace-with-selected-version'
helm show chart kompass/kompass --version "$CHART_VERSION"
```

Report the target context, release name, namespace, chart version, and enabled Kompass components.
Install with the supplied values file:

```sh
helm install "$RELEASE" kompass/kompass \
  --kube-context "$KUBE_CONTEXT" \
  --namespace "$NAMESPACE" --create-namespace \
  --version "$CHART_VERSION" \
  --values "$VALUES_FILE" \
  --timeout 10m
```

Run the readiness checks after Helm completes. The default chart creates the webhook certificate
in a post-install hook. Action Taker needs this certificate to start.
Helm's `--wait` delays post-install hooks until workloads are ready, which blocks this installation.
See [Helm's hook lifecycle](https://helm.sh/docs/topics/charts_hooks/#hooks-and-the-release-lifecycle),
[`charts/pod-rightsizing/templates/webhook/certificate.yaml:8`](https://github.com/zesty-co/kompass/blob/main/charts/pod-rightsizing/templates/webhook/certificate.yaml#L8),
and
[`charts/pod-rightsizing/templates/action-taker/action-taker.yaml:259`](https://github.com/zesty-co/kompass/blob/main/charts/pod-rightsizing/templates/action-taker/action-taker.yaml#L259).

The chart runs prerequisite checks before installation. If installation fails, collect the
diagnostics below before you attempt recovery. A failed installation can leave resources behind.

## 4. Verify the deployment

Check the Helm release and Kubernetes resources:

```sh
helm status "$RELEASE" --kube-context "$KUBE_CONTEXT" --namespace "$NAMESPACE"
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get deployments,statefulsets,daemonsets,pods,pvc
```

For each Deployment, StatefulSet, and DaemonSet in this installation, set its type and name below.
Wait for each rollout to complete:

```sh
WORKLOAD='deployment/replace-with-workload-name'
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  rollout status "$WORKLOAD" --timeout=10m
```

For each PVC used by the installed components, set its name and wait for storage binding:

```sh
PVC='replace-with-pvc-name'
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Bound "pvc/$PVC" --timeout=10m
```

If a wait fails, collect diagnostics and report the installation as incomplete.

For resources that belong to this installation, check that:

- Helm reports the release as `deployed`.
- Each enabled Deployment, StatefulSet, and DaemonSet has its desired ready replicas.
- Long-running Pods have ready containers. Completed installation Jobs are expected.
- PersistentVolumeClaims are `Bound`.

Confirm that the cluster appears as connected in the Zesty platform.
If the agent cannot access the platform, report that this check requires the user's confirmation.
Kubernetes readiness alone does not confirm that Zesty receives cluster data.
Recommendations can take up to 24 hours to appear; see the provider installation guide above.

Finish with a summary of the context, release, namespace, chart version, resource health, and
Zesty connection status. Include any failed or incomplete checks and the next required action.

## Troubleshooting

### Installation validation fails

Read the validation Job logs promptly:

```sh
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  logs job/kompass-validation --all-containers=true --tail=100
```

The current chart retains the failed Job for 300 seconds after completion. Successful validation
Jobs are deleted. See
[`charts/kompass/templates/pre-install-hooks/kompass-validator.yaml:83`](https://github.com/zesty-co/kompass/blob/main/charts/kompass/templates/pre-install-hooks/kompass-validator.yaml#L83).
The Job can already be absent when an installation times out.

### Resources do not become ready

Read recent namespace events:

```sh
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get events --sort-by='.lastTimestamp'
```

Use the failing resource's events and logs to identify the cause. Share only relevant diagnostic
excerpts after removing credential values.

- For pending Pods or PVCs, check scheduling constraints, capacity, and storage provisioning.
- For image-pull failures, check the configured registry and image-pull Secret references.
- For Manager or Bridge readiness failures, check their logs and license delivery status.

Manager normally provisions the shared license Secret. See
[`charts/kompass-insights/values.yaml:5`](https://github.com/zesty-co/kompass/blob/main/charts/kompass-insights/values.yaml#L5).
Check Secret metadata without displaying its contents.
