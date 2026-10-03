# NexusTrust AI Lite - Feasible Implementation Plan

## Executive Summary
The original NexusTrust AI vision (homomorphic encryption, full kinematic simulation, forensic metallurgy) is **not feasible** for a hackathon timeline. This document outlines **NexusTrust AI Lite** - a pragmatic implementation that keeps the innovative multi-modal concept while working within 48 hours and current infrastructure (16GB RAM, CPU-only, Windows 11).

---

## Gap Analysis

### Original Vision vs Reality

| Component | Original Scope | Feasibility | Lite Version |
|-----------|---------------|-------------|--------------|
| **Network Graph** | Cross-carrier homomorphic encryption, ZK proofs | ❌ Impossible (requires industry partnerships, 3-6 months) | ✅ Local entity collision detection in SQLite (8 hours) |
| **Kinematic Simulation** | Full physics engine, vehicle databases, acoustic analysis | ❌ Impossible (requires $50K+ software, 6+ months) | ✅ Rule-based plausibility heuristics (12 hours) |
| **Forensic Metallurgy** | Molecular-level spectrometry, microscopic imaging | ❌ Research-level (1-2 years, specialized hardware) | ⚠️ Skip entirely |
| **Document/Deepfake** | Multi-modal semantic checks | ✅ Already 80% implemented in ClaimShield | ✅ Enhance existing (6 hours) |

---

## NexusTrust AI Lite Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                    NEXUSTRUST AI LITE PIPELINE                         │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                     [ Claim Bundle Ingestion ]
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
   ┌────▼────┐              ┌──────▼──────┐           ┌───────▼────────┐
   │ PILLAR 1│              │  PILLAR 2   │           │   PILLAR 3     │
   │ Network │              │  Physics    │           │   Deepfake     │
   │ Graph   │              │ Plausibility│           │   Detection    │
   │ (30%)   │              │   (40%)     │           │   (30%)        │
   └────┬────┘              └──────┬──────┘           └───────┬────────┘
        │                          │                           │
        │  Entity Collision        │  Sanity Checks           │  Multi-Modal
        │  Detection               │  - Damage-Speed          │  - Image Forensics
        │  - VIN frequency         │  - GPS-Location          │  - PDF Structure
        │  - Repair shop patterns  │  - Time-Lighting         │  - Face Matching
        │  - Medical facility      │  - Shadow Analysis       │  - Cross-Modal
        │                          │                           │
        └──────────────────────────┼───────────────────────────┘
                                   │
                          ┌────────▼────────┐
                          │ HYBRID SCORER   │
                          │ Dynamic Weights │
                          └────────┬────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
         ┌──────▼──────┐    ┌─────▼─────┐    ┌─────▼──────┐
         │ APPROVED    │    │ UNCERTAIN  │    │ FLAGGED    │
         │ (< 0.40)    │    │ (0.40-0.70)│    │ (> 0.70)   │
         │ Fast Track  │    │ Review     │    │ SIU Queue  │
         └─────────────┘    └────────────┘    └────────────┘
```

---

## Implementation Phases (48 Hours Total)

### Phase 1: Entity Graph Layer (8 hours)
**File**: `claimshield/signals/network/entity_graph.py`

```python
"""Local entity collision detection - simplified network analysis."""
import networkx as nx
import sqlite3
from datetime import datetime, timedelta

class EntityCollisionDetector:
    def __init__(self, db_path="data/claims_history.db"):
        self.db = sqlite3.connect(db_path)
        self.graph = nx.Graph()
        self._init_db()
    
    def _init_db(self):
        """Create historical claims database"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS historical_claims (
                claim_id TEXT PRIMARY KEY,
                vin TEXT,
                repair_shop TEXT,
                medical_facility TEXT,
                claimant_name_hash TEXT,
                timestamp DATETIME,
                final_score REAL
            )
        """)
    
    def analyze_claim(self, claim_data: dict) -> tuple[float, list[str]]:
        """
        Returns (collision_score, flags)
        collision_score: 0.0 (clean) to 1.0 (high collision risk)
        """
        entities = self._extract_entities(claim_data)
        flags = []
        collision_score = 0.0
        
        # Check 1: VIN frequency (last 90 days)
        vin_count = self._count_recent_claims(
            'vin', entities['vin'], days=90
        )
        if vin_count > 2:
            collision_score += 0.35
            flags.append(f"VIN appeared in {vin_count} claims (90 days)")
        
        # Check 2: Repair shop overuse
        shop_count = self._count_recent_claims(
            'repair_shop', entities['repair_shop'], days=180
        )
        if shop_count > 10:
            collision_score += 0.30
            flags.append(f"Repair shop in {shop_count} claims (6 months)")
        
        # Check 3: Medical facility pattern
        facility_count = self._count_recent_claims(
            'medical_facility', entities['medical_facility'], days=180
        )
        if facility_count > 15:
            collision_score += 0.25
            flags.append(f"Medical facility in {facility_count} claims")
        
        # Check 4: Graph clustering (shared entities)
        cluster_score = self._analyze_graph_clustering(entities)
        if cluster_score > 0.7:
            collision_score += 0.20
            flags.append("High entity clustering detected")
        
        return min(collision_score, 1.0), flags
    
    def _extract_entities(self, claim_data: dict) -> dict:
        """Extract entities from claim documents (OCR + parsing)"""
        # Uses existing OCR from claimshield/signals/documents/ocr.py
        from ..documents.ocr import extract_text
        
        entities = {
            'vin': self._extract_vin(claim_data),
            'repair_shop': self._extract_shop_name(claim_data),
            'medical_facility': self._extract_medical_name(claim_data),
            'claimant_name_hash': self._hash_name(claim_data.get('claimant_name'))
        }
        return entities
    
    def _count_recent_claims(self, field: str, value: str, days: int) -> int:
        """Count claims with matching entity in time window"""
        cutoff = datetime.now() - timedelta(days=days)
        result = self.db.execute(
            f"SELECT COUNT(*) FROM historical_claims WHERE {field} = ? AND timestamp > ?",
            (value, cutoff)
        ).fetchone()
        return result[0] if result else 0
```

**Integration point**: `claimshield/pipeline.py` - add as new signal lane

**Testing**: Synthetic claim database with known collision patterns

---

### Phase 2: Physics Plausibility Checker (12 hours)
**File**: `claimshield/signals/physics/plausibility.py`

```python
"""Physics-based plausibility heuristics for auto claims."""
import re
import math
from datetime import datetime
import numpy as np
from PIL import Image

class PhysicsPlausibilityChecker:
    
    # Lookup tables (simplified)
    DAMAGE_SPEED_MATRIX = {
        'minor_dent': (5, 25),      # mph range
        'bumper_crack': (10, 35),
        'panel_deformation': (20, 45),
        'structural_damage': (30, 60),
        'total_loss': (40, None)
    }
    
    def check_plausibility(self, claim_narrative: str, 
                          damage_photos: list[Image.Image],
                          metadata: dict) -> tuple[float, list[str]]:
        """
        Returns (plausibility_score, flags)
        plausibility_score: 0.0 (plausible) to 1.0 (implausible)
        """
        flags = []
        score = 0.0
        
        # Check 1: Speed-Damage Consistency
        speed_damage_score, speed_flag = self._check_speed_damage(
            claim_narrative, damage_photos
        )
        score += speed_damage_score
        if speed_flag:
            flags.append(speed_flag)
        
        # Check 2: GPS-Location Consistency
        gps_score, gps_flag = self._check_gps_location(
            claim_narrative, metadata
        )
        score += gps_score
        if gps_flag:
            flags.append(gps_flag)
        
        # Check 3: Time-Lighting Consistency
        time_score, time_flag = self._check_time_lighting(
            claim_narrative, damage_photos, metadata
        )
        score += time_score
        if time_flag:
            flags.append(time_flag)
        
        # Check 4: Impact Direction vs Damage Pattern
        direction_score, direction_flag = self._check_impact_direction(
            claim_narrative, damage_photos
        )
        score += direction_score
        if direction_flag:
            flags.append(direction_flag)
        
        return min(score, 1.0), flags
    
    def _check_speed_damage(self, narrative: str, 
                           photos: list[Image.Image]) -> tuple[float, str]:
        """Compare claimed speed to estimated damage severity"""
        # Extract speed from narrative
        speed = self._extract_speed(narrative)
        if speed is None:
            return 0.0, ""
        
        # Estimate damage severity from photos (ML classifier)
        damage_level = self._estimate_damage_severity(photos)
        
        # Check consistency
        expected_range = self.DAMAGE_SPEED_MATRIX.get(damage_level)
        if expected_range:
            min_speed, max_speed = expected_range
            if max_speed and speed > max_speed * 1.5:
                return 0.30, f"Speed ({speed} mph) too high for {damage_level}"
            elif speed < min_speed * 0.5:
                return 0.25, f"Speed ({speed} mph) too low for {damage_level}"
        
        return 0.0, ""
    
    def _check_gps_location(self, narrative: str, 
                           metadata: dict) -> tuple[float, str]:
        """Compare EXIF GPS to claimed location"""
        exif_gps = metadata.get('gps_coordinates')
        if not exif_gps:
            return 0.0, ""  # No GPS data available
        
        claimed_location = self._extract_location(narrative)
        if not claimed_location:
            return 0.0, ""
        
        # Geocode claimed location and calculate distance
        claimed_coords = self._geocode(claimed_location)
        distance_km = self._haversine_distance(exif_gps, claimed_coords)
        
        if distance_km > 50:
            return 0.35, f"GPS mismatch: photo taken {distance_km:.1f} km from claimed location"
        elif distance_km > 10:
            return 0.15, f"GPS discrepancy: {distance_km:.1f} km difference"
        
        return 0.0, ""
    
    def _check_time_lighting(self, narrative: str, 
                            photos: list[Image.Image],
                            metadata: dict) -> tuple[float, str]:
        """Compare claimed time to photo lighting conditions"""
        claimed_time = self._extract_time(narrative)
        if not claimed_time:
            return 0.0, ""
        
        # Analyze brightness histogram
        avg_brightness = self._estimate_brightness(photos[0])
        
        # Simple heuristic: daytime vs nighttime
        is_daytime_claim = 6 <= claimed_time.hour <= 19
        is_daytime_photo = avg_brightness > 100  # 0-255 scale
        
        if is_daytime_claim != is_daytime_photo:
            return 0.30, f"Time-lighting mismatch: claimed {claimed_time.strftime('%I:%M %p')} but photo shows {'day' if is_daytime_photo else 'night'}"
        
        return 0.0, ""
    
    def _extract_speed(self, text: str) -> float | None:
        """Extract speed from narrative using regex"""
        patterns = [
            r'(\d+)\s*mph',
            r'(\d+)\s*miles per hour',
            r'(\d+)\s*km/h',
            r'speed of (\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                speed = float(match.group(1))
                # Convert km/h to mph if needed
                if 'km' in pattern:
                    speed *= 0.621371
                return speed
        return None
    
    def _estimate_damage_severity(self, photos: list[Image.Image]) -> str:
        """Classify damage severity from photos"""
        # Could use existing CLIP embeddings or simple CNN classifier
        # Simplified: analyze damage coverage percentage
        
        # For now, placeholder logic
        # In real implementation: use damage detection model
        return 'panel_deformation'  # Medium damage
    
    def _estimate_brightness(self, image: Image.Image) -> float:
        """Calculate average brightness of image"""
        gray = image.convert('L')
        return np.array(gray).mean()
    
    @staticmethod
    def _haversine_distance(coord1: tuple, coord2: tuple) -> float:
        """Calculate distance between GPS coordinates in km"""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
```

**Integration**: Add as new signal in fast tier

**Time budget**:
- Speed-damage: 3 hours
- GPS-location: 2 hours  
- Time-lighting: 2 hours
- Impact direction: 2 hours
- Testing: 3 hours

---

### Phase 3: Enhanced Cross-Modal Integration (6 hours)
**File**: `claimshield/signals/cross_modal/semantic_check.py`

```python
"""Cross-modal semantic consistency checker."""
from typing import Dict
import torch
from ..clip_probe import get_clip_embedding  # Existing
from ..documents.ocr import extract_text      # Existing

class CrossModalSemanticChecker:
    
    SCENE_DAMAGE_MAP = {
        'front_collision': ['front bumper', 'hood', 'headlight', 'grille'],
        'rear_collision': ['rear bumper', 'trunk', 'taillight'],
        'side_impact': ['door', 'side panel', 'mirror', 'window'],
        'rollover': ['roof', 'pillars', 'multiple panels']
    }
    
    def check_semantic_consistency(self,
                                   invoice_text: str,
                                   accident_photo: Image.Image,
                                   claim_narrative: str) -> tuple[float, str]:
        """
        Check if invoice damage description matches photo evidence
        Returns (mismatch_score, reason)
        """
        # Extract damage descriptions
        invoice_damage = self._extract_damage_from_invoice(invoice_text)
        narrative_impact_type = self._extract_impact_type(claim_narrative)
        
        # Get visual scene embedding from existing CLIP
        photo_embedding = get_clip_embedding(accident_photo)
        
        # Classify impact type from photo
        photo_impact_type = self._classify_impact_from_embedding(photo_embedding)
        
        # Check consistency
        if narrative_impact_type != photo_impact_type:
            return 0.40, f"Impact type mismatch: narrative says '{narrative_impact_type}' but photo shows '{photo_impact_type}'"
        
        # Check if invoice damage matches expected damage zones
        expected_zones = self.SCENE_DAMAGE_MAP.get(narrative_impact_type, [])
        invoice_zones = self._extract_damage_zones(invoice_damage)
        
        unexpected_zones = set(invoice_zones) - set(expected_zones)
        if unexpected_zones:
            return 0.30, f"Unexpected damage zones in invoice: {', '.join(unexpected_zones)} for {narrative_impact_type}"
        
        return 0.0, "Cross-modal consistency verified"
```

---

### Phase 4: Integrated Scoring (4 hours)
**File**: `claimshield/scoring/nexustrust_composite.py`

```python
"""NexusTrust AI Lite composite scorer."""
from dataclasses import dataclass

@dataclass
class NexusTrustScore:
    network_score: float          # 0-1, entity collision risk
    physics_score: float          # 0-1, plausibility check
    deepfake_score: float         # 0-1, existing ClaimShield
    identity_score: float         # 0-1, face matching
    overall: float                # Final weighted score
    flags: list[str]              # All flags from all pillars
    recommendation: str           # APPROVED | REVIEW | FLAGGED

def compute_nexustrust_score(signals: dict) -> NexusTrustScore:
    """
    Hybrid scoring with dynamic weights
    Base: 0.30 network + 0.40 physics + 0.20 deepfake + 0.10 identity
    """
    W_NETWORK = 0.30
    W_PHYSICS = 0.40
    W_DEEPFAKE = 0.20
    W_IDENTITY = 0.10
    
    # Extract scores from signals
    network_score = signals.get('entity_collision', {}).get('score', 0.5)
    physics_score = signals.get('physics_plausibility', {}).get('score', 0.5)
    deepfake_score = signals.get('image_deepfake', {}).get('score', 0.5)
    identity_score = signals.get('face_match', {}).get('score', 0.5)
    
    # Critical override: if ANY pillar shows critical evidence, escalate
    critical_threshold = 0.85
    if any([
        network_score >= critical_threshold,
        physics_score >= critical_threshold,
        deepfake_score >= critical_threshold
    ]):
        overall = max(network_score, physics_score, deepfake_score)
        flags = ["CRITICAL: High-confidence fraud signal detected"]
        recommendation = "FLAGGED"
    else:
        # Weighted average
        overall = (
            network_score * W_NETWORK +
            physics_score * W_PHYSICS +
            deepfake_score * W_DEEPFAKE +
            identity_score * W_IDENTITY
        )
        
        # Decision bands
        if overall < 0.40:
            recommendation = "APPROVED"
        elif overall < 0.70:
            recommendation = "REVIEW"
        else:
            recommendation = "FLAGGED"
        
        flags = []
    
    # Collect all flags
    for signal_name, signal_data in signals.items():
        if 'flags' in signal_data:
            flags.extend(signal_data['flags'])
    
    return NexusTrustScore(
        network_score=network_score,
        physics_score=physics_score,
        deepfake_score=deepfake_score,
        identity_score=identity_score,
        overall=overall,
        flags=flags,
        recommendation=recommendation
    )
```

---

### Phase 5: UI Updates (6 hours)
**Update**: `claimshield/ui/app.py`

Add new tabs:
- **Network Analysis**: Entity graph visualization (networkx → plotly)
- **Physics Check**: Speed-damage matrix, GPS map, lighting analysis
- **Integrated Score**: New gauge with 4 pillars

---

## Testing Strategy (8 hours)

### Test Cases Required:

1. **Clean Claim** (should score < 0.40)
   - Consistent entities
   - Physics-plausible
   - Real photos
   - Matching documents

2. **Collision Ring** (network score > 0.80)
   - Same VIN in 5 claims
   - Overused repair shop

3. **Physics Fraud** (physics score > 0.75)
   - "Car totaled at 15 mph"
   - GPS 100km from claimed location

4. **Deepfake Documents** (deepfake score > 0.85)
   - AI-generated damage photos
   - Tampered PDFs

5. **Multi-Signal Fraud** (overall > 0.90)
   - All pillars flag

---

## Hardware Constraints & Optimizations

Given your system (16GB RAM, CPU-only):

### Memory Management:
```python
# Only load physics models when needed
@lru_cache(maxsize=1)
def get_damage_classifier():
    return load_model('damage_severity_vit.pt')

# Clear CLIP cache after scoring
torch.cuda.empty_cache()  # Even on CPU, clears buffers
```

### Execution Time Targets:
- Entity collision check: < 1 second (SQLite lookup)
- Physics plausibility: < 3 seconds (rule-based)
- Deepfake (existing): ~8 seconds (already optimized)
- **Total p95**: < 12 seconds (acceptable for hackathon)

---

## Pitch Deck Modifications

### Slide 1: Problem Statement
**Before**: "Multi-carrier syndicate collusion costs $X billion"  
**After**: "Insurance fraud exploits gaps between document verification, physics plausibility, and entity patterns"

### Slide 2: Innovation
**Before**: "Homomorphic encryption + kinematic simulation"  
**After**: 
- "**Entity Collision Detection**: Identifies suspicious patterns across repair shops, VINs, and medical facilities"
- "**Physics Plausibility Heuristics**: Catches impossible damage-speed-location combinations"
- "**Multi-Modal Deepfake**: State-of-art document and image forensics"

### Slide 3: Architecture (Keep Complex Diagram)
Show the aspirational full NexusTrust AI diagram, but annotate:
- "Phase 1 MVP: Entity graphs + physics heuristics"
- "Phase 2 Roadmap: Full kinematic simulation"
- "Phase 3 Research: Homomorphic encryption integration"

**Key Messaging**: "We built the MVP that proves the architecture is viable"

---

## What You Get

### Implementable in 48 Hours:
✅ Entity collision detection (local graph analysis)  
✅ Physics plausibility checks (8 rule-based heuristics)  
✅ Enhanced cross-modal semantic verification  
✅ Integrated 4-pillar scoring system  
✅ Updated Streamlit UI with new visualizations  
✅ Comprehensive test suite  

### Keeps Your Pitch Innovative:
✅ "Multi-modal fraud detection across three orthogonal pillars"  
✅ "Catches fraud rings through entity collision analysis"  
✅ "Physics-based verification that can't be faked"  
✅ "Scalable architecture ready for production deployment"  

### Honest About Scope:
✅ "MVP demonstrates architectural approach"  
✅ "Production version would integrate with carrier APIs"  
✅ "Roadmap includes full kinematic simulation"  

---

## Implementation Timeline

| Hours | Phase | Deliverable |
|-------|-------|-------------|
| 0-8   | Entity Graph | `signals/network/entity_graph.py` + tests |
| 8-20  | Physics Checker | `signals/physics/plausibility.py` + tests |
| 20-26 | Cross-Modal | Enhanced `signals/cross_modal/` |
| 26-30 | Scoring | `scoring/nexustrust_composite.py` |
| 30-36 | UI Updates | New tabs in `ui/app.py` |
| 36-44 | Testing | Full integration test suite |
| 44-48 | Polish | Documentation, demo script, pitch deck |

---

## Risk Mitigation

### If Time Runs Out:
**Kill Switches** (in priority order):
1. ✂️ Cross-modal enhancements (Phase 3) - existing code works
2. ✂️ UI visualizations (Phase 5) - show console output
3. ✂️ Some physics checks (keep Speed-Damage + GPS only)

**Core Must-Haves**:
- ✅ Entity collision detection (differentiator)
- ✅ At least 3 physics heuristics
- ✅ Integrated scoring with new weights
- ✅ Working end-to-end demo

---

## Conclusion

**Original NexusTrust AI**: Brilliant concept, impossible timeline  
**NexusTrust AI Lite**: Keeps 70% of the innovation, 100% implementable

The key insight: Judges don't need you to BUILD a full kinematic physics engine. They need you to PROVE you understand the problem space deeply enough to architect a novel solution. Your lite version demonstrates:

1. **Systems thinking**: Multi-pillar architecture
2. **Technical depth**: Physics heuristics show domain knowledge
3. **Practical engineering**: Works on consumer hardware
4. **Scalability**: Clear path from MVP to production

You can pitch the full vision, show the lite implementation, and have a roadmap slide showing how it scales to the full architecture.

**Recommendation**: Implement NexusTrust AI Lite over next 48 hours, keep the aspirational pitch deck, be honest about what's MVP vs roadmap.
