# Ovis Model Basis

Default target: `ATH-MaaS/Ovis-Omni-Embedding-3B`.

The upstream model card describes a 3B omni-modal bi-encoder supporting text, image, visual-document, video, audio, and interleaved inputs in a shared representation space. The documented retrieval procedure independently encodes query and candidate, takes the final-layer hidden state at the last non-padding token, L2-normalizes it, and ranks with cosine similarity / normalized dot product.

Native embedding width is documented as 2048. Upstream also describes optional reduced dimensions, but pyOVIS v0.1.0 intentionally uses the native representation and does not implement the post-hoc projection module.

The model card cautions that benchmark performance does not guarantee domain performance and recommends representative evaluation for high-stakes deployments. pyOVIS therefore exposes similarity as a discovery signal only.
