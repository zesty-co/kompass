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
helm repo add zesty https://zesty-co.github.io/kompass
helm repo update
```
2. Search the repo to make sure it's set up
```
$ helm search repo zesty
NAME                    CHART VERSION   APP VERSION     DESCRIPTION
zesty/kompass           0.1.0           1.16.0          Helm chart for Kompass
```
3. Install the chart
```sh
helm install kompass kompass/kompass --namespace zesty-system --create-namespace -f values.yaml
```

## Uninstalling
```sh
helm delete kompass
```

