# Supporting literature

Each entry: what it is, what **exactly** it supports in ClaimShield, and the honest limit.
Lead with the first four if a judge asks. Do not overclaim beyond the "supports" line.

## Core detection

**[1] Ricker, Lukovnikov, Fischer. "AEROBLADE: Training-Free Detection of Latent
Diffusion Images Using Autoencoder Reconstruction Error." CVPR 2024.**
https://arxiv.org/abs/2401.17879 · code: https://github.com/jonasricker/aeroblade
- Supports: signal I1. Generated images reconstruct through the LDM autoencoder with
  lower error than real images; LPIPS layer 2 is the best distance; min over several AEs;
  the error map can localize inpainted regions; the same mechanism gives coarse
  attribution to the generating AE.
- Limit: latent-diffusion only; models sharing an AE are indistinguishable (SD1.1 vs 1.5);
  degrades under heavy recompression. Hence I2, I3 and the robustness table.

**[2] Ojha, Li, Lee. "Towards Universal Fake Image Detectors that Generalize Across
Generative Models." CVPR 2023.** https://arxiv.org/abs/2302.10174
- Supports: signal I2 and the general design choice of *not* training a deep artifact
  classifier. A linear probe / nearest-neighbour on frozen CLIP ViT features generalizes
  to unseen generator families far better than trained CNNs, and is robust to blur and
  JPEG.
- Limit: still needs some labelled fakes for the probe; we train on our own generated set
  and hold out Flux.

**[3] Guillaro, Cozzolino, Sud, Dufour, Verdoliva. "TruFor: Leveraging All-Round Clues
for Trustworthy Image Forgery Detection and Localization." CVPR 2023.**
https://arxiv.org/abs/2212.10957 · https://grip-unina.github.io/TruFor/
- Supports: signal I3. Learned noise-sensitive fingerprint trained only on real images
  (self-supervised), fused with RGB; outputs a localization map, an integrity score and a
  **reliability map** — which we use to suppress low-confidence regions in the UI.
- Limit: weights and licence must be checked; fallbacks are MVSS-Net / CAT-Net.

**[4] Nickel, Kiela. "Poincaré Embeddings for Learning Hierarchical Representations."
NeurIPS 2017.** https://arxiv.org/abs/1705.08039
- Status in v3: **not used.** The family map is a hierarchical softmax over the generator
  tree. Keep this citation only on a one-line future-work bullet. Do not put a Poincaré
  disk on screen.

## Supporting / secondary

**[5] Larue, Štruc, Peer, Vu. "Learning the Manifold of Authenticity: Hybrid-Curvature
Representation Learning for Generalizable Deepfake Detection." IEEE Access 2026.**
- Status in v3: future-work bullet only.

**[6] Sheth et al. "Curved Worlds, Clear Boundaries" (RHYME). arXiv:2511.10793.**
- Status in v3: future-work bullet only.

**[7] Zhao et al. "Learning Self-Consistency for Deepfake Detection" (PCL). ICCV 2021.**
https://arxiv.org/abs/2012.09311
- Supports: the principle that consistency-based signals (noise residual, copy-move,
  claim-level checks) generalize better than pattern memorization.

**[8] Tang, Key, Ellis. "WorldCoder." NeurIPS 2024.** https://arxiv.org/abs/2402.12275
- Supports: the one architecture-slide sentence on representing "how real evidence
  behaves" as auditable code (document field logic, claim consistency) beside learned
  detectors. Do not say "world model" more than once in the demo.

## Standards and platform

**[9] C2PA Technical Specification (v2.x).** https://spec.c2pa.org/ · Python:
`c2pa-python` (https://github.com/contentauth/c2pa-python)
- Supports: signal I4-C2PA. Adobe Firefly, OpenAI image models and Google Imagen embed
  signed manifests with `digitalSourceType = trainedAlgorithmicMedia`; Midjourney does not.
  A manifest is positive provenance; absence proves nothing; verify the signature.

**[10] Amazon Nova Canvas — Bedrock InvokeModel, `INPAINTING` task with `maskPrompt` /
`maskImage`, `IMAGE_VARIATION`, `TEXT_IMAGE`.**
https://docs.aws.amazon.com/nova/latest/userguide/image-gen-access.html
- Supports: the arena's live attack path with no GPU dependency.

## Removed from the earlier list, and why
- Ha & Schmidhuber (World Models), Meta CWM, Web World Models, Resemble DETECT-World:
  they justified a "world model" framing that we have narrowed to auditable consistency
  code. Keep at most WorldCoder [8]. Judges from an insurance IT firm will not reward RL
  world-model citations for an image-forensics product, and a sceptical ML judge will
  ask what the citation actually supports.
- FaceForensics++-style face detectors: wrong modality for claim imagery. Face models are
  used only in the identity lane (InsightFace/ArcFace).
