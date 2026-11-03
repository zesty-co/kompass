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

## 2. Select a chart version and validate the values

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
Set the exact chart version below, then inspect its metadata and umbrella defaults:

```sh
CHART_VERSION='replace-with-selected-version'
helm show chart kompass/kompass --version "$CHART_VERSION"
helm show values kompass/kompass --version "$CHART_VERSION"
```

Inspect the selected chart's packaged dependency defaults for settings absent from the umbrella
defaults. Parse the customer values file and resolve overrides with Helm's value precedence.
Include global values and any configured environment overrides or Secret references.
Use the requirements for the selected chart and image versions.

### Required configuration

Validate these inputs for a fresh installation with Insights and Manager enabled:

| Setting | Required check |
| --- | --- |
| `kompass-insights.orgID` | A positive integer or integer string identifying the customer's Zesty organization. Reject missing, blank, zero, negative, or placeholder values. |
| `kompass-insights.metadata.*` | When `enabled: true`, resolve a supported `provider`; an omitted provider defaults to AWS. Cloud identity requires nonblank `accountID`, `region`, and `clusterName` matching the target cluster. |
| `kompass-insights.assumeRole.*` | Resolve the intended AWS authentication mode. For role assumption, require `enabled: true`, `roleArn`, `zestyExternalID`, and usable source credentials. Otherwise, explicitly set `enabled: false`. |
| `global.imagePullSecret.name` | Required for Manager license retrieval from a non-ECR registry. For ECR, configure this Secret or a working AWS identity for Manager. |
| Organization license | Confirm that Zesty has provisioned the organization's signed license artifact in the registry used by Manager. Check the configured license Secret name and document key. |

When explicit metadata is disabled, Manager discovers the cluster identity from Kubernetes.
Check that node metadata and discovery permissions are available. If discovery cannot work, obtain
the explicit metadata from onboarding. For `OnPremise`, Manager uses the `kube-system` namespace UID
as the cluster ID; cloud account, region, and cluster name are not required.

Manager populates `kompass-insights.insights.secret` with runtime identity. Its default name is
`kompass-insights-secret`. It downloads the license into `global.license.secretName`, using
`global.license.documentKey`; the defaults are `kompass-license` and `kompass_license`.
Keep valid defaults. These generated Secrets do not need to exist before a fresh installation.
If Insights is disabled, establish external identity and license provisioning for enabled consumers.

The chart declares the organization and role inputs in
[`charts/kompass/values.yaml:192`](https://github.com/zesty-co/kompass/blob/main/charts/kompass/values.yaml#L192).
Runtime identity rules are in the `kompass-agent` repository:
`manager/pkg/metadata/metadata.go:53` and `insights-agent/pkg/secret/secret.go:79`.

### Cloud authentication

Resolve the target provider, enabled AWS integrations, and intended authentication mode first.
The umbrella chart enables role assumption by default, even when no role values are supplied.
For direct SDK access or an installation without AWS integrations, set
`kompass-insights.assumeRole.enabled: false`. Ask the user when the intended mode is unclear.
Require AWS role inputs only when that authentication mode is intended.

AWS observation requires usable source SDK credentials, such as IRSA or EKS Pod Identity.
Verify the service-account identity, permissions, and trust for each configured role assumption.
A role ARN and external ID alone do not provide source credentials.
With role assumption disabled, verify the intended direct source identity and its permissions.
For other providers, verify the workload identity or credentials selected during onboarding.

The current Insights Agent uses the AWS SDK credential chain instead of legacy encrypted AWS
credentials. See `kompass-agent/insights-agent/pkg/aws/session_manager.go:169`.
Check the authentication requirements of the selected image version before using an older file.

### Registry access and license delivery

Resolve the Manager repository from `kompass-insights.manager.repository` and
`global.zestyImageRegistry`. Its parent repository path becomes `IMAGE_PREFIX`.
Manager downloads `<IMAGE_PREFIX>/license/<orgID>:<LICENSE_TAG>`.
The default license tag is `latest`.

Manager reads registry credentials from the singular `global.imagePullSecret.name` setting.
The plural `global.imagePullSecrets` and component Pod pull-secret lists configure Pod image
pulls; they do not set Manager's license credential Secret.

If `global.imagePullSecret.dockerconfigjson` is supplied with the name, the chart creates the
Secret.
Validate this value as base64-encoded Docker configuration JSON without displaying it.
Otherwise, check the existing named Secret in the installation namespace.
It must have type `kubernetes.io/dockerconfigjson`.
Its credentials must match the exact registry host.

With no named Secret, Manager uses its own AWS SDK identity for ECR authentication.
Verify ECR token access and read access to the organization license repository from that identity.
The Insights role-assumption settings do not configure this ECR credential path.
Confirm network access to the registry and required authentication endpoints.

Chart mappings are in
[`charts/kompass-insights/templates/configMap.yaml:15`](https://github.com/zesty-co/kompass/blob/main/charts/kompass-insights/templates/configMap.yaml#L15)
and
[`charts/kompass/templates/image-pull-secret.yaml:1`](https://github.com/zesty-co/kompass/blob/main/charts/kompass/templates/image-pull-secret.yaml#L1).
Manager's authentication implementation is in
`kompass-agent/manager/pkg/license/delivery.go:154`.

### Enabled integrations and missing values

Validate additional settings only for enabled integrations:

- With `kompass-insights.awsAthena.enabled: true`, resolve the database, table, region, query-result
  bucket, catalog, and workgroup. Verify the effective billing identity and its permissions,
  including any linked-role fallback or configured `masterRoleArn` and `masterExternalID`.
- With CX logging enabled, check the effective `global.cxLogging` or `kompass-insights.cxLogging`
  configuration. Verify the cluster name, endpoint settings, and API-key Secret or supplied key.

List missing or invalid value paths and explain which requirement each fails.
Ask the user for the missing onboarding values, including the organization ID when absent.
Preserve existing settings and apply supplied corrections to the customer values file.
Validate the resulting configuration again before installation.
Stop while required values or provisioning prerequisites remain unresolved.
A successful Helm render does not verify these runtime requirements.

## 3. Check cluster prerequisites

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

## 4. Install

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

## 5. Verify the deployment

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

### Verify runtime identity and licensing

Set the runtime and license Secret names from the resolved values. The defaults are shown below:

```sh
RUNTIME_SECRET='kompass-insights-secret'
LICENSE_SECRET='kompass-license'
kubectl --context "$KUBE_CONTEXT" --namespace "$NAMESPACE" \
  get secret "$RUNTIME_SECRET" "$LICENSE_SECRET"
```

Secret existence is the first check. Inspect identity fields locally without displaying other
Secret data. Confirm that `ORG_ID` is positive and matches the supplied organization ID.
Check that `CLUSTER_ID` and `PROVIDER` are populated. For cloud identity, also check `ACCOUNT_ID`,
`REGION`, and `CLUSTER_NAME` against the target cluster. On-premises identity uses the
`kube-system` namespace UID as `CLUSTER_ID`.

Check that the configured license document key is populated without displaying the document.
When Manager supplies the license, confirm successful delivery in its logs.
Manager readiness and a `License sync succeeded` message do not prove that the license is valid.
When Insights is enabled, confirm that it accepts the organization-matching license and reaches
readiness. Otherwise, verify license acceptance through the enabled consumers.
Verify readiness and connectivity for enabled Bridge components.
Treat missing identity, failed license delivery, or rejected licensing as an incomplete
installation.

Runtime checks are implemented in `kompass-agent/manager/pkg/license/sync.go:50` and
`kompass-agent/insights-agent/cmd/main.go:64`.

### Confirm the Zesty connection

Confirm that the cluster appears as connected in the Zesty platform.
If the agent cannot access the platform, report that this check requires the user's confirmation.
Kubernetes readiness alone does not confirm that Zesty receives cluster data.
Recommendations can take up to 24 hours to appear; see the provider installation guide above.

Finish with a summary of the context, release, namespace, chart version, resource health,
identity verification, license acceptance, and Zesty connection status.
Include any failed or incomplete checks and the next required action.

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
