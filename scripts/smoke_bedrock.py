"""Smoke test: Claude text + Nova Canvas inpainting via Bedrock bearer token.
Run:  python scripts/smoke_bedrock.py path/to/photo.jpg
"""
import base64, json, os, sys
import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
TEXT_MODEL = os.environ.get("BEDROCK_TEXT_MODEL_ID")
IMG_MODEL = os.environ.get("BEDROCK_IMAGE_MODEL_ID", "amazon.nova-canvas-v1:0")

def client():
    # Recent boto3 picks up AWS_BEARER_TOKEN_BEDROCK automatically. If the installed
    # version does not, inject the header via an event hook.
    c = boto3.client("bedrock-runtime", region_name=REGION)
    tok = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    if tok:
        def _add(request, **kw):
            request.headers["Authorization"] = f"Bearer {tok}"
        c.meta.events.register("before-send.bedrock-runtime.*", _add)
    return c

def text(c):
    if not TEXT_MODEL:
        print("BEDROCK_TEXT_MODEL_ID unset; skipping text test"); return
    r = c.converse(modelId=TEXT_MODEL,
                   messages=[{"role": "user", "content": [{"text": "Reply with OK."}]}],
                   inferenceConfig={"temperature": 0, "maxTokens": 10})
    print("text:", r["output"]["message"]["content"][0]["text"])

def inpaint(c, path):
    img = base64.b64encode(open(path, "rb").read()).decode()
    body = {"taskType": "INPAINTING",
            "inPaintingParams": {"image": img,
                                 "maskPrompt": "the largest flat surface",
                                 "text": "large dent and deep scratches in the paint, photorealistic"},
            "imageGenerationConfig": {"numberOfImages": 1, "quality": "standard",
                                      "cfgScale": 7.0, "seed": 42}}
    r = c.invoke_model(modelId=IMG_MODEL, body=json.dumps(body),
                       contentType="application/json", accept="application/json")
    out = json.loads(r["body"].read())
    b = base64.b64decode(out["images"][0])
    open("smoke_inpaint.png", "wb").write(b)
    print("inpaint: wrote smoke_inpaint.png", len(b), "bytes")

if __name__ == "__main__":
    c = client()
    text(c)
    if len(sys.argv) > 1:
        inpaint(c, sys.argv[1])
