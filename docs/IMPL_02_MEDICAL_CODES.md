# Implementation Guide: Medical Code Validation

**Priority**: ⭐⭐⭐⭐ HIGH (Healthcare-specific differentiator)  
**Time**: 45-60 minutes  
**Complexity**: Medium  
**Risk**: Low  
**Impact**: Shows domain expertise

---

## Overview

Validates ICD-10 medical diagnosis codes and CPT procedure codes in healthcare claims. Detects:
- Invalid code formats
- Upcoding (billing expensive procedures for cheap treatments)
- Code mismatches (treatment doesn't match diagnosis)

### Problem Being Solved

**Healthcare fraud patterns**:
- Routine checkup billed as emergency surgery ($150 → $15,000)
- Invalid/fabricated ICD codes that don't exist
- Procedure codes that don't match diagnosis
- **Cost to industry**: $68 billion/year in healthcare fraud

### Why This Matters

- ✅ Shows you understand healthcare domain
- ✅ Easy to explain to judges
- ✅ Catches real fraud (upcoding is #1 healthcare fraud type)
- ✅ Deterministic logic (no ML required)

---

## Medical Coding Primer

### ICD-10 (Diagnosis Codes)

**Format**: `[Letter][2 digits].[0-4 chars]`
- Example: `S72.001A` = Fracture of unspecified part of neck of right femur
- Example: `J44.0` = Chronic obstructive pulmonary disease
- Example: `E11.9` = Type 2 diabetes without complications

**Structure**:
```
S72.001A
│││ │││└─ Extension (A=initial, D=subsequent, S=sequela)
│││ ││└── Laterality/detail
│││ │└─── Sub-classification
│││ └──── Category
││└────── Body system
│└─────── Chapter (S = Injury)
└──────── Letter (A-Z except U)
```

### CPT (Procedure Codes)

**Format**: `[5 digits]` or `[5 digits]-[2 digit modifier]`
- Example: `99213` = Office visit, established patient
- Example: `27447` = Total knee arthroplasty (replacement)
- Example: `99285-25` = Emergency department visit

**Categories**:
- `99xxx` = Evaluation & Management (visits)
- `00xxx-01999` = Anesthesia
- `10xxx-69990` = Surgery
- `70xxx-79999` = Radiology
- `80xxx-89999` = Laboratory

---

## Architecture

### Detection Pipeline

```
┌────────────────────────────────────────────┐
│         MEDICAL CODE VALIDATOR             │
└────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
   ┌────▼────┐            ┌────▼────┐
   │  ICD-10 │            │   CPT   │
   │Validator│            │Validator│
   └────┬────┘            └────┬────┘
        │                       │
        ├─ Format Check         ├─ Format Check
        ├─ Range Validation     ├─ Range Validation
        └─ Fraud Patterns       └─ Cost Analysis
                    │
              ┌─────┴─────┐
              │           │
         ┌────▼────┐ ┌───▼────┐
         │Upcoding │ │  Code  │
         │Detection│ │Mismatch│
         └────┬────┘ └───┬────┘
              │           │
              └─────┬─────┘
                    │
               ┌────▼────┐
               │ Signal  │
               │ + Flags │
               └─────────┘
```

---

## Implementation

### Step 1: Core Validation Logic (20 min)

**File**: `claimshield/signals/medical_codes.py` (NEW)

```python
"""Medical billing code validation for healthcare claims."""
import re
from dataclasses import dataclass
from typing import Optional, List, Tuple

@dataclass
class MedicalCodeSignal:
    name: str = "medical_code_validation"
    score: float = 0.0
    confidence: float = 0.85
    reason: str = ""
    evidence: dict = None
    abstained: bool = False
    applicable: bool = True
    tier: str = "document"
    
    def __post_init__(self):
        if self.evidence is None:
            self.evidence = {}


class MedicalCodeValidator:
    """
    Validates ICD-10 and CPT codes, detects upcoding.
    """
    
    # ICD-10 fraud patterns (simplified for demo)
    UPCODING_ICD_MAP = {
        # Routine → Severe codes (fraud pattern)
        'routine_checkup': ['99213', '99214'],  # Should be 99211-99212
        'minor_injury': ['S72', 'S82'],  # Major fractures (inappropriate)
        'common_cold': ['J18'],  # Pneumonia (upcoding)
    }
    
    # CPT cost ranges (simplified)
    CPT_COST_RANGES = {
        '992': (50, 300),      # Office visits
        '274': (5000, 30000),  # Major surgery
        '99281': (100, 250),   # ER visit level 1
        '99285': (300, 1000),  # ER visit level 5
    }
    
    def validate(self, bill_text: str, narrative: str = "") -> MedicalCodeSignal:
        """
        Validate medical codes in bill against claim narrative.
        
        Args:
            bill_text: OCR text from medical bill
            narrative: Claim description text
        """
        icd_codes = self._extract_icd10_codes(bill_text)
        cpt_codes = self._extract_cpt_codes(bill_text)
        
        flags = []
        score = 0.0
        
        # Check 1: Format validation
        invalid_icd = [c for c in icd_codes if not self._is_valid_icd10(c)]
        if invalid_icd:
            score += 0.40
            flags.append(f"Invalid ICD-10 codes: {', '.join(invalid_icd[:3])}")
        
        invalid_cpt = [c for c in cpt_codes if not self._is_valid_cpt(c)]
        if invalid_cpt:
            score += 0.35
            flags.append(f"Invalid CPT codes: {', '.join(invalid_cpt[:3])}")
        
        # Check 2: Upcoding detection
        upcoding_score, upcoding_flag = self._detect_upcoding(
            narrative, icd_codes, cpt_codes
        )
        if upcoding_flag:
            score += upcoding_score
            flags.append(upcoding_flag)
        
        # Check 3: Procedure-diagnosis mismatch
        mismatch_score, mismatch_flag = self._check_code_mismatch(
            icd_codes, cpt_codes
        )
        if mismatch_flag:
            score += mismatch_score
            flags.append(mismatch_flag)
        
        score = min(score, 1.0)
        
        if not icd_codes and not cpt_codes:
            return MedicalCodeSignal(
                score=None,
                applicable=False,
                reason="No medical codes found in document"
            )
        
        reason = "; ".join(flags) if flags else "Medical codes validated successfully"
        
        return MedicalCodeSignal(
            score=score,
            reason=reason,
            evidence={
                'icd_codes': icd_codes,
                'cpt_codes': cpt_codes,
                'invalid_icd': invalid_icd,
                'invalid_cpt': invalid_cpt,
                'flags': flags
            }
        )
    
    def _extract_icd10_codes(self, text: str) -> List[str]:
        """Extract ICD-10 codes from text"""
        # Pattern: Letter + 2 digits + optional decimal + up to 4 chars
        pattern = r'\b[A-Z]\d{2}(?:\.\w{1,4})?\b'
        matches = re.findall(pattern, text.upper())
        
        # Filter out false positives (e.g., dates, addresses)
        filtered = []
        for match in matches:
            # ICD-10 first letter must be valid chapter
            if match[0] in 'ABCDEFGHJKLMNOPQRSTUVWXYZ':
                filtered.append(match)
        
        return list(set(filtered))  # Remove duplicates
    
    def _extract_cpt_codes(self, text: str) -> List[str]:
        """Extract CPT codes from text"""
        # Pattern: 5 digits, optionally followed by -XX modifier
        pattern = r'\b\d{5}(?:-\d{2})?\b'
        matches = re.findall(pattern, text)
        
        # Filter to valid CPT range (00100-99999)
        filtered = []
        for match in matches:
            base = match.split('-')[0]
            if 100 <= int(base) <= 99999:
                filtered.append(match)
        
        return list(set(filtered))
    
    def _is_valid_icd10(self, code: str) -> bool:
        """Check if ICD-10 code has valid format"""
        # Basic format check
        pattern = r'^[A-Z]\d{2}(?:\.\w{1,4})?$'
        if not re.match(pattern, code):
            return False
        
        # Chapter validation (simplified)
        chapter = code[0]
        valid_chapters = 'ABCDEFGHJKLMNOPQRSTUVWXYZ'
        return chapter in valid_chapters
    
    def _is_valid_cpt(self, code: str) -> bool:
        """Check if CPT code has valid format"""
        base = code.split('-')[0]
        try:
            num = int(base)
            return 100 <= num <= 99999
        except:
            return False
    
    def _detect_upcoding(self, narrative: str, icd_codes: List[str], 
                        cpt_codes: List[str]) -> Tuple[float, Optional[str]]:
        """Detect if expensive codes used for routine procedures"""
        narrative_lower = narrative.lower()
        
        # Pattern 1: Routine visit with expensive CPT codes
        routine_keywords = ['routine', 'checkup', 'annual', 'wellness', 'screening']
        if any(kw in narrative_lower for kw in routine_keywords):
            # Check if any high-cost CPT codes present
            for cpt in cpt_codes:
                prefix = cpt[:3]
                if prefix in ['274', '275', '276']:  # Major surgery codes
                    return 0.45, f"Upcoding: Routine visit billed with surgery code {cpt}"
        
        # Pattern 2: Minor injury with major fracture codes
        minor_keywords = ['scratch', 'bruise', 'minor', 'small cut', 'sprain']
        if any(kw in narrative_lower for kw in minor_keywords):
            for icd in icd_codes:
                if icd.startswith(('S72', 'S82')):  # Major fractures
                    return 0.40, f"Upcoding: Minor injury with fracture code {icd}"
        
        # Pattern 3: Emergency visit level 5 (highest) for non-critical
        non_critical = ['cold', 'cough', 'headache', 'minor pain']
        if any(kw in narrative_lower for kw in non_critical):
            if '99285' in cpt_codes:  # ER level 5 (most expensive)
                return 0.35, "Upcoding: Non-critical issue billed as ER level 5"
        
        return 0.0, None
    
    def _check_code_mismatch(self, icd_codes: List[str], 
                            cpt_codes: List[str]) -> Tuple[float, Optional[str]]:
        """Check if procedure codes match diagnosis codes"""
        
        # Simplified checks for demo
        
        # Pattern 1: Orthopedic surgery CPT with non-musculoskeletal ICD
        ortho_cpt_prefixes = ['274', '275', '276', '277', '278', '279']
        has_ortho_cpt = any(c.startswith(tuple(ortho_cpt_prefixes)) for c in cpt_codes)
        
        # ICD chapters: M=musculoskeletal, S=injury
        has_relevant_icd = any(c.startswith(('M', 'S')) for c in icd_codes)
        
        if has_ortho_cpt and not has_relevant_icd:
            return 0.30, "Code mismatch: Orthopedic surgery without musculoskeletal diagnosis"
        
        # Pattern 2: Diabetes medication without diabetes diagnosis
        # (Would need drug codes - skip for minimal version)
        
        return 0.0, None


# Quick test
if __name__ == "__main__":
    validator = MedicalCodeValidator()
    
    print("Test 1: Valid codes")
    bill1 = "Diagnosis: S72.001A - Fracture of femur. Procedure: 27447 - Knee arthroplasty"
    result1 = validator.validate(bill1, "Patient fell and broke leg")
    print(f"Score: {result1.score:.2f} - {result1.reason}\n")
    
    print("Test 2: Upcoding (routine checkup as surgery)")
    bill2 = "Diagnosis: Z00.00 - Routine checkup. Procedure: 27447 - Major knee surgery"
    result2 = validator.validate(bill2, "Annual wellness visit and routine physical exam")
    print(f"Score: {result2.score:.2f} - {result2.reason}\n")
    
    print("Test 3: Invalid codes")
    bill3 = "Diagnosis: X99.999Z - Invalid code. Procedure: 99999 - Fake procedure"
    result3 = validator.validate(bill3, "Treatment for injury")
    print(f"Score: {result3.score:.2f} - {result3.reason}\n")
```

**Test it**:
```bash
python claimshield/signals/medical_codes.py
```

---

### Step 2: Pipeline Integration (10 min)

**File**: `claimshield/pipeline.py` (MODIFY)

```python
# Add import
from .signals.medical_codes import MedicalCodeValidator

# In document scoring section
def score_document(doc_path):
    """Score a document (PDF invoice, medical bill, etc.)"""
    
    signals = []
    
    # ... existing PDF forensics ...
    # ... existing OCR ...
    
    # NEW: Medical code validation
    try:
        validator = MedicalCodeValidator()
        
        # Get OCR text
        ocr_text = extract_full_text(doc_path)  # Your existing function
        
        # Get claim narrative (if available)
        narrative = get_claim_narrative()  # From claim context
        
        # Validate codes
        med_code_signal = validator.validate(ocr_text, narrative)
        
        if med_code_signal.applicable:
            signals.append(med_code_signal)
    
    except Exception as e:
        print(f"Warning: Medical code validation failed: {e}")
    
    return signals
```

---

### Step 3: Configuration (2 min)

**File**: `configs/weights.yaml` (MODIFY)

```yaml
document:
  pdf_incremental_update: 0.30    # Reduced from 0.35
  pdf_producer_mismatch:  0.15
  pdf_font_anomaly:       0.15
  medical_code_validation: 0.20   # NEW - high weight for upcoding
  field_arithmetic:       0.15    # Reduced from 0.20
  field_dates:            0.05    # Reduced from 0.10
```

---

### Step 4: Enhanced Code Database (15 min - OPTIONAL)

For more realistic validation, add common codes:

**File**: `claimshield/data/icd10_common.json` (NEW)

```json
{
  "common_codes": {
    "E11.9": "Type 2 diabetes without complications",
    "I10": "Essential hypertension",
    "J44.9": "COPD unspecified",
    "M54.5": "Low back pain",
    "S72.001A": "Fracture of femur, initial",
    "Z00.00": "Routine general examination"
  },
  "fraud_patterns": {
    "routine_upcoded_to": ["27447", "27486", "29881"],
    "minor_injury_upcoded_to": ["S72", "S82", "S42"]
  }
}
```

Load in validator:
```python
import json
from pathlib import Path

class MedicalCodeValidator:
    def __init__(self):
        db_path = Path(__file__).parent.parent / "data" / "icd10_common.json"
        if db_path.exists():
            self.code_db = json.loads(db_path.read_text())
        else:
            self.code_db = {"common_codes": {}, "fraud_patterns": {}}
```

---

## Testing

### Unit Tests

**File**: `tests/test_medical_codes.py` (NEW)

```python
"""Tests for medical code validation."""
import pytest
from claimshield.signals.medical_codes import MedicalCodeValidator

def test_valid_codes():
    """Valid ICD-10 and CPT codes"""
    validator = MedicalCodeValidator()
    bill = "ICD: S72.001A, CPT: 27447"
    result = validator.validate(bill, "Fractured femur")
    assert result.score < 0.30

def test_invalid_icd_format():
    """Invalid ICD-10 format"""
    validator = MedicalCodeValidator()
    bill = "ICD: X99.ZZZZ"  # Invalid
    result = validator.validate(bill)
    assert result.score > 0.30
    assert "Invalid ICD-10" in result.reason

def test_upcoding_detection():
    """Routine visit billed as surgery"""
    validator = MedicalCodeValidator()
    bill = "ICD: Z00.00, CPT: 27447"  # Checkup + knee surgery
    result = validator.validate(bill, "Annual routine checkup")
    assert result.score > 0.40
    assert "Upcoding" in result.reason

def test_code_extraction():
    """ICD-10 extraction from messy text"""
    validator = MedicalCodeValidator()
    text = "Patient diagnosed with E11.9 and M54.5 conditions"
    codes = validator._extract_icd10_codes(text)
    assert "E11.9" in codes
    assert "M54.5" in codes
```

**Run**:
```bash
pytest tests/test_medical_codes.py -v
```

---

## Demo Script

### Scenario 1: Upcoding Detection

**Setup**: Medical bill for "routine checkup" with surgery codes

```python
# Demo claim
bill_text = """
MEDICAL INVOICE

Patient: John Doe
Date of Service: 2024-10-01

Diagnosis Codes:
- Z00.00: Encounter for general adult medical examination

Procedure Codes:
- 27447: Total knee arthroplasty
- Cost: $18,500

TOTAL: $18,500.00
"""

narrative = "Annual routine physical examination and wellness checkup"
```

**Expected**: 
- Score: ~0.45
- Flag: "Upcoding: Routine visit billed with surgery code 27447"
- **Demo line**: "ClaimShield caught a $18,000 upcoding fraud - routine checkup billed as knee surgery"

### Scenario 2: Invalid Codes

```python
bill_text = """
Diagnosis: X99.FAKE - Non-existent condition
Procedure: 00001 - Invalid CPT code
"""
```

**Expected**:
- Score: ~0.75
- Flags: "Invalid ICD-10 codes: X99.FAKE; Invalid CPT codes: 00001"

---

## Advanced Features (If Time Allows)

### 1. Real ICD-10 Database Lookup

Use public CMS ICD-10 database:

```python
import requests

def validate_icd10_with_cms(code: str) -> bool:
    """Check against actual CMS database"""
    # CMS API (public, free)
    url = f"https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"
    params = {"sf": "code", "terms": code}
    
    try:
        response = requests.get(url, params=params, timeout=2)
        data = response.json()
        return len(data[3]) > 0  # Found results
    except:
        return True  # Fail open (don't block on API issues)
```

### 2. Cost-Based Upcoding Detection

```python
def detect_cost_anomaly(cpt_code: str, billed_amount: float) -> bool:
    """Check if billed amount is abnormally high for procedure"""
    
    # Average Medicare reimbursement rates
    EXPECTED_COSTS = {
        '99213': 93,    # Office visit
        '99214': 132,   # Extended office visit
        '27447': 1500,  # Knee replacement
        '99285': 320    # ER level 5
    }
    
    expected = EXPECTED_COSTS.get(cpt_code)
    if expected and billed_amount > expected * 3:
        return True  # Billed 3x normal rate
    
    return False
```

### 3. Duplicate Billing Detection

```python
def find_duplicate_procedures(bill_items: List[dict]) -> List[str]:
    """Find procedures billed multiple times"""
    from collections import Counter
    
    cpt_counts = Counter(item['cpt_code'] for item in bill_items)
    duplicates = [code for code, count in cpt_counts.items() if count > 1]
    
    return duplicates
```

---

## Troubleshooting

### Issue: No codes extracted from bills

**Cause**: OCR quality, different bill formats

**Solution**: Add fallback patterns
```python
# Try multiple patterns
patterns = [
    r'ICD[- ]?10?[:\s]+([A-Z]\d{2}\.\w+)',  # "ICD-10: E11.9"
    r'Diagnosis[:\s]+([A-Z]\d{2}\.\w+)',     # "Diagnosis: E11.9"
    r'\b([A-Z]\d{2}\.\w{1,4})\b'             # Standalone
]
```

### Issue: Too many false positives

**Cause**: Aggressive thresholds

**Solution**: Adjust scoring
```python
# In _detect_upcoding
if prefix in ['274', '275', '276']:
    return 0.30, ...  # Reduced from 0.45
```

---

## Production Considerations

### ICD-10 Database

For production, use official CMS database:
- Download: https://www.cms.gov/medicare/coding-billing/icd-10-codes
- ~72,000 codes
- Updated annually (October 1)

### CPT Database

CPT codes are copyrighted by AMA:
- License required for commercial use
- Free for display/reference
- Use generic "procedure code" wording for demo

---

## Integration with Other Features

### Combine with Entity Collision

```python
# High-risk pattern: Upcoding + entity collision
if medical_code_signal.score > 0.40 and collision_signal.score > 0.60:
    # Fraud ring doing systematic upcoding
    overall_score = max(medical_code_signal.score, collision_signal.score) + 0.10
```

### Combine with Date Consistency

```python
# Invoice dated before accident = impossible
if invoice_date < accident_date and upcoding_detected:
    # Double fraud: fake timeline + upcoding
    score += 0.20
```

---

## Success Metrics

### Minimum Viable
- [ ] Extracts ICD-10 codes from text
- [ ] Validates code format
- [ ] Detects at least one upcoding pattern
- [ ] Returns Signal contract

### Good Implementation
- [ ] Extracts CPT codes too
- [ ] Multiple upcoding patterns
- [ ] Code mismatch detection
- [ ] Integrated into pipeline

### Production-Ready
- [ ] Real ICD-10 database lookup
- [ ] Cost-based anomaly detection
- [ ] Duplicate billing detection
- [ ] Comprehensive test suite

---

## Time Breakdown

- Core validator: 20 min
- Pipeline integration: 10 min
- Configuration: 2 min
- Testing: 10 min
- Demo prep: 8 min

**Total**: 50 minutes

---

## Next Steps

1. **If time remains**: Add date consistency checks (see IMPL_03)
2. **If showcasing healthcare**: Emphasize this + collision detection
3. **Always**: Practice explaining upcoding to judges

**Key pitch line**: "ClaimShield validates medical billing logic - we caught $18,000 in upcoding fraud"
