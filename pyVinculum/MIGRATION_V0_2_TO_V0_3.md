# Migration: v0.2 → v0.3

Existing v0.2 code continues to work with `VinculumEngine.bind()`.

To adopt trusted governance:

1. Provision a deployment-scoped Ed25519 root public key.
2. Protect the root private key outside application runtime.
3. Create a durable `FileCheckpointStore` (or production adapter).
4. Use `TrustedGovernanceBootstrapper` once to install the root-signed epoch-1 bundle.
5. On normal startup, create `TrustedGovernanceRuntime` and call `load_or_advance()` with the current signed bundle.
6. Change binding calls from `bind(..., context=context)` to `bind_trusted(..., runtime=runtime)`.
7. Preserve the `trust` receipt from the `BindingReport` with downstream CERPA/decision records.

Do not place root private keys or checkpoint integrity keys in source-controlled application artifacts.
