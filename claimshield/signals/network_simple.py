"""Ultra-simple entity collision detector for hackathon demo.

NO DEPENDENCIES beyond stdlib + pandas. Runs in < 500ms.
"""
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

@dataclass
class EntityCollisionResult:
    score: float  # 0.0 (clean) to 1.0 (high collision)
    flags: list[str]
    entity_counts: dict[str, int]
    confidence: float = 0.85

class EntityCollisionDetector:
    """
    Tracks VIN, repair shop, medical facility across claims.
    Flags suspicious repetition patterns.
    """

    def __init__(self, history_file: Path = None):
        self.history_file = history_file or Path(__file__).parent.parent.parent / "data" / "claim_history.json"
        self.history = self._load_history()

    def _load_history(self) -> list[dict]:
        """Load historical claims (or create empty)"""
        if not self.history_file.exists():
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text("[]")
            return []
        return json.loads(self.history_file.read_text())

    def analyze(self, claim_data: dict) -> EntityCollisionResult:
        """
        claim_data = {
            'vin': str,
            'repair_shop': str,
            'medical_facility': str | None,
            'claimant_name': str  # will be hashed
        }
        """
        entities = {
            'vin': claim_data.get('vin', '').strip().upper(),
            'repair_shop': self._normalize(claim_data.get('repair_shop', '')),
            'medical_facility': self._normalize(claim_data.get('medical_facility', '')),
            'name_hash': self._hash_name(claim_data.get('claimant_name', ''))
        }

        # Count recent occurrences (last 180 days)
        cutoff = datetime.now() - timedelta(days=180)
        recent_claims = [
            c for c in self.history
            if datetime.fromisoformat(c['timestamp']) > cutoff
        ]

        counts = self._count_entities(recent_claims, entities)
        flags = []
        score = 0.0

        # Scoring logic
        if counts['vin'] > 2:
            score += 0.40
            flags.append(f"⚠️ VIN appeared in {counts['vin']} recent claims (MAJOR RED FLAG)")

        if counts['repair_shop'] > 12:
            score += 0.25
            flags.append(f"🔧 Repair shop: {counts['repair_shop']} claims (possible fraud ring)")
        elif counts['repair_shop'] > 8:
            score += 0.15
            flags.append(f"🔧 Repair shop: {counts['repair_shop']} claims (elevated activity)")

        if counts['medical_facility'] > 15:
            score += 0.25
            flags.append(f"🏥 Medical facility: {counts['medical_facility']} claims (possible fraud ring)")

        # Network clustering bonus: same VIN + same shop = definite fraud ring
        if counts['vin'] > 1 and counts['repair_shop'] > 5:
            score += 0.30
            flags.append("🚨 COLLISION RING DETECTED: Shared VIN + overused repair shop")

        # Add this claim to history
        self._save_claim(entities)

        return EntityCollisionResult(
            score=min(score, 1.0),
            flags=flags,
            entity_counts=counts
        )

    def _count_entities(self, claims: list[dict], current: dict) -> dict[str, int]:
        """Count how many times each entity appears"""
        counts = defaultdict(int)
        for claim in claims:
            if claim.get('vin') == current['vin']:
                counts['vin'] += 1
            if claim.get('repair_shop') == current['repair_shop']:
                counts['repair_shop'] += 1
            if claim.get('medical_facility') == current['medical_facility']:
                counts['medical_facility'] += 1
        return dict(counts)

    def _save_claim(self, entities: dict):
        """Append current claim to history"""
        self.history.append({
            **entities,
            'timestamp': datetime.now().isoformat()
        })
        # Keep last 1000 claims only
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        self.history_file.write_text(json.dumps(self.history, indent=2))

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize shop/facility names"""
        import re
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
        text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
        return text

    @staticmethod
    def _hash_name(name: str) -> str:
        """SHA256 hash for privacy"""
        return hashlib.sha256(name.encode()).hexdigest()[:16]


# Quick test
if __name__ == "__main__":
    detector = EntityCollisionDetector()

    # Simulate a fraud ring
    print("Testing fraud ring detection...\n")

    # Claim 1: Clean
    result1 = detector.analyze({
        'vin': '1HGBH41JXMN109186',
        'repair_shop': 'Honest Auto Body Shop',
        'medical_facility': 'County General Hospital',
        'claimant_name': 'John Doe'
    })
    print(f"Claim 1 Score: {result1.score:.2f}")
    print(f"Flags: {result1.flags}\n")

    # Claim 2: Same VIN (suspicious)
    result2 = detector.analyze({
        'vin': '1HGBH41JXMN109186',  # SAME VIN
        'repair_shop': 'Quick Fix Auto',
        'medical_facility': 'Downtown Clinic',
        'claimant_name': 'Jane Smith'
    })
    print(f"Claim 2 Score: {result2.score:.2f}")
    print(f"Flags: {result2.flags}\n")

    # Claim 3: Same VIN AGAIN (fraud ring)
    result3 = detector.analyze({
        'vin': '1HGBH41JXMN109186',  # SAME VIN THIRD TIME
        'repair_shop': 'Speedy Repairs',
        'medical_facility': 'City Medical',
        'claimant_name': 'Bob Johnson'
    })
    print(f"Claim 3 Score: {result3.score:.2f}")
    print(f"Flags: {result3.flags}")
