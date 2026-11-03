# Zesty Kompass

> Redefining the boundaries of Kubernetes optimization

This Helm chart installs Kompass and its subsystems.

## Subsystems

For the values of the various subsystems please refer to each
of them separately:

1. [Insights](https://github.com/zesty-co/kompass-insights)
2. [Pod Rightsizing](https://github.com/zesty-co/kompass-pod-rightsizing)
3. [Disk](https://github.com/zesty-co/zesty-helm)

## Prerequisites

1. Complete [Zesty onboarding](https://docs.zesty.co/docs/get-started-with-zesty).
   Download the values file for your cluster from the Zesty installation wizard.
2. Install the following tools:
     - [Helm](https://helm.sh/docs/intro/install/)
     - [Kubectl](https://kubernetes.io/docs/tasks/tools/)
3. Authenticate to the target cluster and identify its Kubernetes context.

## Installation

### Install with an AI agent

Copy this prompt into an AI agent that can run Helm and kubectl on your machine:

```text
Read https://raw.githubusercontent.com/zesty-co/kompass/main/docs/install.md
and install Kompass using my Zesty-provided values file.
Ask for the file path and target Kubernetes context.
Validate required settings, including my Zesty organization ID.
Ask me for missing onboarding values before installing.
Install the chart and verify cluster identity, licensing, and deployment health.
```

The [installation guide](docs/install.md) contains the procedure that the agent follows.

### Install manually

Follow the [installation guide](docs/install.md) for the Helm commands, cluster checks,
verification, and troubleshooting.

## Uninstalling

Replace `YOUR_CONTEXT` with the context used for installation.
Use your release name and namespace if they differ from the defaults.

```sh
helm uninstall kompass --namespace zesty-system --kube-context YOUR_CONTEXT
```
