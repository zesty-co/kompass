# kompass release notes

Version: 0.4.10 → 0.4.11

## Insights Agent

- support oracle opencost native
- retire spot data feed access
- support gcp
- \#\# Docker Images
  \#\# Docker Images
  
  Application Image:
  \`\`\`bash
  docker pull 473301030746.dkr.ecr.us\-west\-2.amazonaws.com/zesty\-k8s/agent:v1.169.5
  \`\`\`
  \*\*Full Changelog\*\*: https://gitlab.com/zestyco/kompass/kompass\-agent/\-/compare/v1.169.4...v1.169.5
- remove retired admission dev config
- \#\# Docker Images
  \#\# Docker Images
  
  Application Image:
  \`\`\`bash
  docker pull 473301030746.dkr.ecr.us\-west\-2.amazonaws.com/zesty\-k8s/kompass\-manager:v0.0.4
  \`\`\`
  
  \*\*Full Changelog\*\*: https://gitlab.com/zestyco/kompass/kompass\-agent/\-/compare/v0.0.3...v0.0.4
- use pull secrets for generic license registries \(KPS\-0\)
- support gcp
- SQLite migration cleanup
- actually billing cost monthly
- \#\# Release v0.0.4 \(2026\-11\-01T08:10:46Z\)
  \#\# Release v0.0.4 \(2026\-11\-01T08:10:46Z\)
  
  Welcome to this new release\!
  
  \#\# Changelog
- none namespaced owner discovery
- \#\# Release v1.169.5 \(2026\-11\-01T08:21:33Z\)
  \#\# Release v1.169.5 \(2026\-11\-01T08:21:33Z\)
  
  Welcome to this new release\!
  
  \#\# Changelog
- return error on athena error instead of trying forever
- fallback to node spec providerID if cluster name in lable is wrong
- retire admission controller and retired products
- remove action taker
- autodiscovery for managed oke
- memory list price
- spot cur discount already in node cost

## Rightsizing

- \[KPS\-7668\] Enforce HorizontalScaling policy priorities with Lease claims
- bot \- pod\-rightsizing \- change  version to 30c2de15
- Resolve KPS\-8107 "Tag customer selected jvm pods at admission and startup"
- bot \- pod\-rightsizing \- change  version to 058bd740
- \#\# Release v0.9.4
  \#\# Release v0.9.4
  
  Promoted from RC: \`v0.9.4\-rc1\`
  
  \#\# Changes Since v0.9.3
- \[KPS\-8217\] Stop rollback to initial values \- use prev desired instead
- bot \- pod\-rightsizing \- change  version to 198ac4ba
- KPS\-8276 \- Allow "additionalSupportedKinds" as Standalone
- KPS\-8121 \- Collect JVM recommendation inputs
- bot \- pod\-rightsizing \- change  version to 1849b846
- bot \- pod\-rightsizing \- change  version to ee30f471
- jvm max heap recording rule
- bot \- pod\-rightsizing \- change  version to 0d9077f1
- bot \- pod\-rightsizing \- change  version to 354ac6f1
- bot \- pod\-rightsizing \- change  version to 6f1e7a0c
- bot \- pod\-rightsizing \- change  version to 08150bdb
- \[KPS\-7494\] \- Route controller\-runtime logs through active Coralogix logger
- KPS\-8122 \- Calculate JVM memory and maximum\-heap pairs
- bot \- pod\-rightsizing \- change  version to c8533f04
- KPS\-8112 \- Carry memory and JVM maximum heap pairs through recommendation and Action models
- bot \- pod\-rightsizing \- change  version to f26ac03f
- bot \- pod\-rightsizing \- change  version to 56508c95
- bot \- pod\-rightsizing \- change  version to v0.9.4\-rc1
- variants for jvm workloads
- bot \- pod\-rightsizing \- change  version to e11cc0d0
- \#\# Docker Images
  \#\# Docker Images
  
  \#\#\# Action Taker
  \`\`\`bash
  docker pull 672188301118.dkr.ecr.eu\-west\-1.amazonaws.com/pod\-rightsizing/action\-taker:v0.9.4
  \`\`\`
  
  \#\#\# Recommendations Maker
  \`\`\`bash
  docker pull 672188301118.dkr.ecr.eu\-west\-1.amazonaws.com/pod\-rightsizing/recommendations\-maker:v0.9.4
  \`\`\`
  
  \#\#\# Metrics Exporter
  \`\`\`bash
  docker pull 672188301118.dkr.ecr.eu\-west\-1.amazonaws.com/pod\-rightsizing/metrics\-exporter:v0.9.4
  \`\`\`
  
  \#\#\# Bridge Data Exporter
  \`\`\`bash
  docker pull 672188301118.dkr.ecr.eu\-west\-1.amazonaws.com/pod\-rightsizing/bridge\-data\-exporter:v0.9.4
  \`\`\`
  
  \#\#\# Guardian
  \`\`\`bash
  docker pull 672188301118.dkr.ecr.eu\-west\-1.amazonaws.com/pod\-rightsizing/guardian:v0.9.4
  \`\`\`
  
  \*\*Full Changelog\*\*: https://gitlab.com/zestyco/kompass/pod\-rightsizing/\-/compare/v0.9.3...v0.9.4
- \[SUPPORT\-940\] Enforce minimum CPU and memory scale\-up steps
- schedule manual ci tests
- KPS\-8108 expose current jvm indication
- filter managed JVM memory/heap pairs

## Pod Placement

- pro
- \#\# Release v0.6.2 \(2026\-10\-05T12:44:24Z\)
  \#\# Release v0.6.2 \(2026\-10\-05T12:44:24Z\)
  
  Welcome to this new release\!
  
  \#\# Changelog
- \#\# Docker Images
  \#\# Docker Images
  
  Application Image:
  \`\`\`bash
  docker pull 473301030746.dkr.ecr.us\-west\-2.amazonaws.com/zesty\-k8s/pod\-placement:v0.6.2
  \`\`\`
  
  \*\*Full Changelog\*\*: https://gitlab.com/zestyco/kompass/kompass\-pod\-placement/\-/compare/v0.6.0...v0.6.2

## Bridge/shared

- Updated tests/kube\_state\_metrics\_crs\_test.yaml key \`tests\`.
- \#\# Docker Images
  \#\# Docker Images
  
  Application Image:
  \`\`\`bash
  docker pull 473301030746.dkr.ecr.us\-west\-2.amazonaws.com/zesty\-k8s/kompass\-bridge:v0.3.0
  \`\`\`
  
  \*\*Full Changelog\*\*: https://gitlab.com/zestyco/kompass/kompass\-bridge/\-/compare/v0.2.2\-rc1...v0.3.0
- Added docs/install.md.
- support chunking \(KPS\-0\)
- \#\# Release v0.3.0 \(2026\-10\-06T08:07:28Z\)
  \#\# Release v0.3.0 \(2026\-10\-06T08:07:28Z\)
  
  Welcome to this new release\!
  
  \#\# Changelog
- Updated values.yaml key \`kubeStateMetrics.rbac.extraRules\`.
- Updated tests/kube\_state\_metrics\_crs\_test.yaml key \`templates\`.
- Updated values.yaml key \`kubeStateMetrics.customResourceState.config.spec.resources\`.
- Updated README.md.
