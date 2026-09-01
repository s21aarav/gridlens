# Kubernetes deployment surface

The API manifest provides a small cloud-native deployment example with two
replicas, readiness/liveness probes, resource requests and limits, and secrets
injected through a gridlens-secrets object.

The image and secret are placeholders for a real registry and secret manager.
The repository does not claim that this manifest alone provides production
availability, identity, or OT network isolation.
