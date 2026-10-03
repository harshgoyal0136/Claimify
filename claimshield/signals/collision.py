"""Entity collision detector - MINIMAL VERSION for hackathon demo.

No dependencies, runs in < 100ms, stores in simple JSON.
"""
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

@dataclass
class CollisionSignal:
    name: str = "entity_collision"
    score: float = 0.0  # 0 = clean, 1 = fraud ring
    confidence: float = 0.85
    reason: str = ""
    evidence: dict = None
    abstained: bool = False
    applicable: bool = True
    tier: str = "claim"

    def __post_init__(self):
        if self.evidence is None:
            self.evidence = {}


def detect_collision(vin: str = None, repair_shop: str = None,
                    medical_facility: str = None, claimant_name: str = None) -> CollisionSignal:
    """
    Ultra-fast collision detection. Returns Signal contract.

    Usage:
        signal = detect_collision(
            vin="1HGBH41JXMN109186",
            repair_shop="Quick Fix Auto Body",
            medical_facility="Downtown Medical Center",
            claimant_name="John Doe"
        )
    """
    db_path = Path(__file__).parent.parent.parent / "data" / "collision_db.json"

    # Load history
    if db_path.exists():
        history = json.loads(db_path.read_text())
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        history = []

    # Count recent occurrences (last 180 days)
    cutoff = (datetime.now() - timedelta(days=180)).isoformat()
    recent = [c for c in history if c.get('timestamp', '') > cutoff]

    # Normalize inputs
    vin = (vin or "").strip().upper()
    shop = _normalize(repair_shop or "")
    facility = _normalize(medical_facility or "")
    name_hash = _hash(claimant_name or "")

    # Count matches
    vin_count = sum(1 for c in recent if c.get('vin') == vin and vin)
    shop_count = sum(1 for c in recent if c.get('shop') == shop and shop)
    facility_count = sum(1 for c in recent if c.get('facility') == facility and facility)

    # Score (simple additive)
    score = 0.0
    flags = []

    if vin_count >= 3:
        score += 0.45
        flags.append(f"VIN in {vin_count} recent claims (FRAUD RING)")
    elif vin_count == 2:
        score += 0.25
        flags.append(f"VIN in {vin_count} recent claims")

    if shop_count >= 15:
        score += 0.30
        flags.append(f"Repair shop in {shop_count} claims (HIGH ACTIVITY)")
    elif shop_count >= 10:
        score += 0.15
        flags.append(f"Repair shop in {shop_count} claims")

    if facility_count >= 20:
        score += 0.25
        flags.append(f"Medical facility in {facility_count} claims (HIGH ACTIVITY)")

    # Combo bonus: same VIN + overused shop = definite ring
    if vin_count >= 2 and shop_count >= 8:
        score = max(score, 0.90)
        flags.append("🚨 COLLISION RING: VIN + repair shop pattern")

    score = min(score, 1.0)

    # Save to history
    history.append({
        'vin': vin,
        'shop': shop,
        'facility': facility,
        'name_hash': name_hash,
        'timestamp': datetime.now().isoformat()
    })

    # Keep last 500 claims only
    if len(history) > 500:
        history = history[-500:]

    db_path.write_text(json.dumps(history, indent=2))

    # Build reason
    if flags:
        reason = "; ".join(flags)
    else:
        reason = "No collision patterns detected"

    return CollisionSignal(
        score=score,
        reason=reason,
        evidence={
            'vin_count': vin_count,
            'shop_count': shop_count,
            'facility_count': facility_count,
            'flags': flags
        }
    )


def _normalize(text: str) -> str:
    """Normalize shop/facility names"""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def _hash(text: str) -> str:
    """SHA256 hash for privacy"""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# Quick self-test
if __name__ == "__main__":
    print("Testing collision detector...\n")

    # Claim 1: Clean
    s1 = detect_collision(
        vin="1HGBH41JXMN109186",
        repair_shop="Honest Auto Body",
        claimant_name="John Doe"
    )
    print(f"Claim 1: {s1.score:.2f} - {s1.reason}\n")

    # Claim 2: Same VIN
    s2 = detect_collision(
        vin="1HGBH41JXMN109186",  # SAME
        repair_shop="Different Shop",
        claimant_name="Jane Smith"
    )
    print(f"Claim 2: {s2.score:.2f} - {s2.reason}\n")

    # Claim 3: Same VIN again (should trigger)
    s3 = detect_collision(
        vin="1HGBH41JXMN109186",  # SAME THIRD TIME
        repair_shop="Quick Fix",
        claimant_name="Bob Johnson"
    )
    print(f"Claim 3: {s3.score:.2f} - {s3.reason}\n")
    print(f"Evidence: {s3.evidence}")
