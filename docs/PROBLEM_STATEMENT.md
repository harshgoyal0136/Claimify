# PS2 — AI-Powered Synthetic Identity & Deepfake Claim Detection System

Source: Adrosonic Build problem statement PDF. Condensed, with the parts that drive
scoring decisions bolded.

## Constraints
- 24-hour hackathon, team of 2–4, **pre-trained models allowed**, **working UI required**.
- "Purely rule-based approaches are discouraged." (A rule layer beside trained detectors is
  fine; a rule layer alone is not.)
- "Models should demonstrate the ability to **generalize across unseen or novel fraud
  patterns**."
- "Teams are expected to **generate synthetic or tampered data** for training and
  validation." Only a limited set of authentic images is provided.
- "Robust enough to handle **low-resolution images, noise, compression artifacts, and
  partially incomplete inputs**."
- Inputs named: accident photos, vehicle damage images, medical reports, identity
  documents. Generators named: Midjourney, Adobe Firefly, open-source deepfake models.
- **Scope is images and documents. Video is not mentioned anywhere.**

## Scope
- **A. Image manipulation detection (core)** — classify authentic vs AI-generated /
  manipulated, confidence score, threshold flag, *optionally highlight suspicious regions*.
- **B. Document tampering detection (core)** — PDF or image documents; inconsistent
  fonts, altered values, metadata anomalies; OCR (pytesseract or similar) + rule-based or
  ML checks; flag suspicious fields **with a reason**.
- **C. Risk scoring (core)** — image authenticity score, document authenticity score, and
  **overall fraud likelihood**, with interpretable reasons. "Show why a score was assigned."
- **D. Demo interface (core)** — upload files, see fraud score, flagged indicators, short
  plain-English explanation. Streamlit / Gradio / React+Flask all fine.
- **E. Identity comparison (bonus)** — compare faces across ID documents and selfies;
  detect mismatch or morphing.

## Evaluation weights
| Criterion | Weight | What it means on the day |
|---|---|---|
| Detection accuracy on sample data | 25% | Judges will upload their own images. One confident wrong call on a real photo costs more than five correct fakes. |
| Risk scoring logic & explainability | 25% | "Why is this 73?" needs a deterministic, repeatable answer. |
| UI / demo quality | 20% | Upload → result in seconds, no crashes, reads like a claims tool. |
| Code quality & architecture | 15% | Modular, README, tests. |
| Innovation & bonus | 15% | Identity comparison named first; novel techniques. |

## Demo requirements (10 minutes)
1. Upload an image; show detection output and confidence.
2. Upload a document; show tampering flags and reasons.
3. Show composite risk (low / medium / high) with explanation.
4. Walk through architecture and key decisions.
5. If implemented, show identity mismatch detection.

## What this means for us
- 50% of the score is accuracy + explainability → deterministic scoring, calibrated
  thresholds, abstain band, an eval table.
- "Generalize to unseen" + "generate your own data" → the red-team arena with a held-out
  generator family is a direct answer to two rubric lines.
- Judges are an insurance IT consultancy → the invoice "time machine" and claim-level
  consistency checks are what they will recognise as real fraud.
- Identity comparison is explicitly listed → two hours, must do.
