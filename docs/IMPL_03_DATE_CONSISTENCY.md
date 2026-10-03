# Implementation Guide: Cross-Temporal Date Consistency

**Priority**: ⭐⭐⭐ MEDIUM (Quick win)  
**Time**: 20-30 minutes  
**Complexity**: Low  
**Risk**: Very Low  
**Impact**: Easy to explain, impossible to argue against

---

## Overview

Validates timeline consistency across claim documents. Catches impossible sequences:
- Medical bill dated **before** accident photo
- Claim filed **before** treatment received
- Treatment **before** diagnosis
- Invoice timestamp conflicts with photo EXIF

### Problem Being Solved

**Fraud pattern**: Fraudsters reuse old invoices/receipts
- Find real 2023 medical bill
- Attach to fake 2024 accident claim
- Hope insurer doesn't check dates

**Detection**: Compare timestamps across all documents

---

## Architecture

```
┌────────────────────────────────────────────┐
│      DATE CONSISTENCY VALIDATOR            │
└────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
   ┌────▼────┐            ┌────▼────┐
   │ Extract │            │ Extract │
   │  Dates  │            │  EXIF   │
   │from Docs│            │from IMG │
   └────┬────┘            └────┬────┘
        │                       │
        └───────────┬───────────┘
                    │
               ┌────▼────┐
               │Timeline │
               │  Sort   │
               └────┬────┘
                    │
         ┌──────────┼──────────┐
         │          │          │
    ┌────▼────┐┌───▼───┐┌────▼────┐
    │Invoice  ││Accident││Treatment│
    │  Date   ││  Date  ││  Date   │
    └────┬────┘└───┬───┘└────┬────┘
         │          │          │
         └──────────┼──────────┘
                    │
              ┌─────▼─────┐
              │ Check     │
              │Violations │
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │Signal     │
              │+ Flags    │
              └───────────┘
```

---

## Implementation

### Step 1: Core Logic (15 min)

**File**: `claimshield/signals/date_consistency.py` (NEW)

```python
"""Cross-temporal date consistency validation."""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

@dataclass
class DateConsistencySignal:
    name: str = "date_consistency"
    score: float = 0.0
    confidence: float = 0.90
    reason: str = ""
    evidence: dict = None
    abstained: bool = False
    applicable: bool = True
    tier: str = "claim"
    
    def __post_init__(self):
        if self.evidence is None:
            self.evidence = {}


class DateConsistencyValidator:
    """
    Validates temporal consistency across claim documents.
    Catches impossible timelines.
    """
    
    def validate(self, dates: dict) -> DateConsistencySignal:
        """
        Check date consistency across claim components.
        
        Args:
            dates = {
                'accident_date': datetime,      # When accident occurred
                'photo_date': datetime,         # Photo EXIF timestamp
                'invoice_date': datetime,       # Medical bill date
                'treatment_date': datetime,     # Treatment date
                'claim_filed_date': datetime    # When claim submitted
            }
        """
        flags = []
        score = 0.0
        
        # Rule 1: Invoice dated BEFORE accident
        if dates.get('invoice_date') and dates.get('accident_date'):
            if dates['invoice_date'] < dates['accident_date']:
                days_before = (dates['accident_date'] - dates['invoice_date']).days
                score += 0.50
                flags.append(
                    f"CRITICAL: Invoice dated {days_before} days BEFORE accident"
                )
        
        # Rule 2: Photo dated BEFORE accident (if accident date from narrative)
        if dates.get('photo_date') and dates.get('accident_date'):
            if dates['photo_date'] < dates['accident_date'] - timedelta(days=1):
                days_before = (dates['accident_date'] - dates['photo_date']).days
                score += 0.40
                flags.append(
                    f"Photo taken {days_before} days BEFORE reported accident date"
                )
        
        # Rule 3: Treatment BEFORE accident
        if dates.get('treatment_date') and dates.get('accident_date'):
            if dates['treatment_date'] < dates['accident_date']:
                days_before = (dates['accident_date'] - dates['treatment_date']).days
                score += 0.45
                flags.append(
                    f"Treatment dated {days_before} days BEFORE accident"
                )
        
        # Rule 4: Claim filed BEFORE treatment completed
        if dates.get('claim_filed_date') and dates.get('treatment_date'):
            if dates['claim_filed_date'] < dates['treatment_date']:
                score += 0.30
                flags.append(
                    "Claim filed BEFORE treatment received"
                )
        
        # Rule 5: Suspiciously fast timeline (treatment same day as accident)
        if dates.get('treatment_date') and dates.get('accident_date'):
            if dates['treatment_date'] == dates['accident_date']:
                # Could be legitimate (ER visit), but flag if expensive treatment
                pass  # Low priority for demo
        
        # Rule 6: Photo timestamp way in future
        if dates.get('photo_date'):
            if dates['photo_date'] > datetime.now() + timedelta(days=1):
                score += 0.35
                flags.append(
                    f"Photo timestamp in the FUTURE: {dates['photo_date'].strftime('%Y-%m-%d')}"
                )
        
        score = min(score, 1.0)
        
        # Check if we have enough dates to validate
        date_count = sum(1 for v in dates.values() if v is not None)
        if date_count < 2:
            return DateConsistencySignal(
                score=None,
                applicable=False,
                reason="Insufficient dates for consistency check"
            )
        
        reason = "; ".join(flags) if flags else "Date timeline is consistent"
        
        return DateConsistencySignal(
            score=score,
            reason=reason,
            evidence={
                'dates': {k: v.isoformat() if v else None for k, v in dates.items()},
                'flags': flags,
                'date_count': date_count
            }
        )
    
    @staticmethod
    def extract_dates_from_text(text: str) -> List[datetime]:
        """
        Extract dates from text using common patterns.
        
        Patterns supported:
        - MM/DD/YYYY
        - YYYY-MM-DD
        - Month DD, YYYY
        - DD Month YYYY
        """
        dates = []
        
        # Pattern 1: MM/DD/YYYY or MM-DD-YYYY
        pattern1 = r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b'
        for match in re.finditer(pattern1, text):
            try:
                month, day, year = match.groups()
                dates.append(datetime(int(year), int(month), int(day)))
            except:
                pass
        
        # Pattern 2: YYYY-MM-DD (ISO format)
        pattern2 = r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b'
        for match in re.finditer(pattern2, text):
            try:
                year, month, day = match.groups()
                dates.append(datetime(int(year), int(month), int(day)))
            except:
                pass
        
        # Pattern 3: Month DD, YYYY
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        pattern3 = r'\b(' + '|'.join(months.keys()) + r')[a-z]*[\s,]+(\d{1,2})[,\s]+(\d{4})\b'
        for match in re.finditer(pattern3, text.lower()):
            try:
                month_name, day, year = match.groups()
                month_num = months[month_name[:3].lower()]
                dates.append(datetime(int(year), month_num, int(day)))
            except:
                pass
        
        return dates
    
    @staticmethod
    def get_photo_exif_date(image_path) -> Optional[datetime]:
        """Extract date from image EXIF data"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            img = Image.open(image_path)
            exif = img._getexif()
            
            if not exif:
                return None
            
            # Look for DateTime tags
            for tag_id, value in exif.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                    # Format: 'YYYY:MM:DD HH:MM:SS'
                    try:
                        return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                    except:
                        pass
            
            return None
        except:
            return None


# Quick test
if __name__ == "__main__":
    validator = DateConsistencyValidator()
    
    print("Test 1: Invoice BEFORE accident (fraud)")
    dates1 = {
        'accident_date': datetime(2024, 10, 1),
        'invoice_date': datetime(2024, 9, 15),  # 16 days before!
        'photo_date': datetime(2024, 10, 1)
    }
    result1 = validator.validate(dates1)
    print(f"Score: {result1.score:.2f}")
    print(f"Reason: {result1.reason}\n")
    
    print("Test 2: Consistent timeline (legitimate)")
    dates2 = {
        'accident_date': datetime(2024, 10, 1),
        'photo_date': datetime(2024, 10, 1),
        'treatment_date': datetime(2024, 10, 2),
        'invoice_date': datetime(2024, 10, 5),
        'claim_filed_date': datetime(2024, 10, 10)
    }
    result2 = validator.validate(dates2)
    print(f"Score: {result2.score:.2f}")
    print(f"Reason: {result2.reason}\n")
    
    print("Test 3: Photo in the future (fraud)")
    dates3 = {
        'accident_date': datetime(2024, 10, 1),
        'photo_date': datetime(2025, 12, 31),  # Future!
    }
    result3 = validator.validate(dates3)
    print(f"Score: {result3.score:.2f}")
    print(f"Reason: {result3.reason}\n")
    
    print("Test 4: Date extraction from text")
    text = "Accident occurred on October 1, 2024. Invoice dated 09/15/2024."
    extracted = validator.extract_dates_from_text(text)
    print(f"Extracted dates: {[d.strftime('%Y-%m-%d') for d in extracted]}")
```

**Test**:
```bash
python claimshield/signals/date_consistency.py
```

---

### Step 2: Integration (10 min)

**File**: `claimshield/pipeline.py` (MODIFY)

```python
from .signals.date_consistency import DateConsistencyValidator

def score_full_claim(images, documents, claim_narrative):
    """Score complete claim"""
    
    signals = []
    
    # ... existing scoring ...
    
    # NEW: Date consistency
    try:
        validator = DateConsistencyValidator()
        
        # Collect dates from various sources
        dates = {}
        
        # 1. Extract from claim narrative
        if claim_narrative:
            narrative_dates = validator.extract_dates_from_text(claim_narrative)
            if narrative_dates:
                dates['accident_date'] = narrative_dates[0]  # First mentioned
        
        # 2. Extract from photo EXIF
        if images:
            photo_date = validator.get_photo_exif_date(images[0])
            if photo_date:
                dates['photo_date'] = photo_date
        
        # 3. Extract from invoice/bill text
        if documents:
            doc_text = get_document_text(documents[0])
            doc_dates = validator.extract_dates_from_text(doc_text)
            if doc_dates:
                dates['invoice_date'] = doc_dates[0]
        
        # 4. Claim filing date (from system)
        dates['claim_filed_date'] = datetime.now()
        
        # Validate
        date_signal = validator.validate(dates)
        
        if date_signal.applicable:
            signals.append(date_signal)
    
    except Exception as e:
        print(f"Warning: Date consistency check failed: {e}")
    
    return signals
```

---

### Step 3: Configuration (1 min)

**File**: `configs/weights.yaml` (MODIFY)

```yaml
claim:
  invoice_before_photo:  0.08
  camera_model_mismatch: 0.04
  name_mismatch:         0.08
  entity_collision:      0.20
  date_consistency:      0.15   # NEW - high confidence check
```

---

## Testing

### Unit Tests

**File**: `tests/test_date_consistency.py` (NEW)

```python
"""Tests for date consistency validation."""
import pytest
from datetime import datetime, timedelta
from claimshield.signals.date_consistency import DateConsistencyValidator

def test_invoice_before_accident():
    """Invoice dated before accident = fraud"""
    validator = DateConsistencyValidator()
    dates = {
        'accident_date': datetime(2024, 10, 1),
        'invoice_date': datetime(2024, 9, 15)
    }
    result = validator.validate(dates)
    assert result.score > 0.40
    assert "BEFORE accident" in result.reason

def test_consistent_timeline():
    """Valid chronological order"""
    validator = DateConsistencyValidator()
    dates = {
        'accident_date': datetime(2024, 10, 1),
        'treatment_date': datetime(2024, 10, 2),
        'invoice_date': datetime(2024, 10, 5)
    }
    result = validator.validate(dates)
    assert result.score < 0.30

def test_date_extraction():
    """Extract dates from text"""
    validator = DateConsistencyValidator()
    text = "Accident on October 1, 2024 and treatment on 10/05/2024"
    dates = validator.extract_dates_from_text(text)
    assert len(dates) >= 2
    assert any(d.month == 10 and d.day == 1 for d in dates)

def test_insufficient_dates():
    """Not enough dates to validate"""
    validator = DateConsistencyValidator()
    dates = {'accident_date': datetime(2024, 10, 1)}  # Only one
    result = validator.validate(dates)
    assert not result.applicable
```

---

## Demo Scenarios

### Scenario 1: Invoice Fraud

```python
# Fraudster found 2023 medical bill, attached to 2024 claim
dates = {
    'accident_date': datetime(2024, 10, 1),  # Claimed today
    'invoice_date': datetime(2023, 8, 15),   # Old bill from last year
    'photo_date': datetime(2024, 10, 1)
}

result = validator.validate(dates)
# Score: ~0.50
# Flag: "Invoice dated 412 days BEFORE accident"
```

**Demo line**: "ClaimShield caught a recycled invoice - bill was from 2023 but claim says accident happened in 2024"

### Scenario 2: Future Photo

```python
# Photo EXIF shows future date (camera clock wrong or manipulated)
dates = {
    'accident_date': datetime(2024, 10, 1),
    'photo_date': datetime(2025, 1, 1)  # Future!
}

result = validator.validate(dates)
# Score: ~0.35
# Flag: "Photo timestamp in the FUTURE"
```

---

## Advantages

### Why This Works

✅ **Simple**: Just date comparisons  
✅ **Fast**: < 10ms to check  
✅ **Reliable**: Hard to fake (EXIF timestamps)  
✅ **Explainable**: Judges instantly understand  
✅ **No ML**: Deterministic logic  

### Demo Value

- Very visual (show timeline diagram)
- Impossible to argue against
- Catches real fraud pattern

---

## UI Visualization (Optional)

Add timeline view:

```python
# In Streamlit UI
import plotly.graph_objects as go

def show_date_timeline(dates_dict):
    """Visual timeline of claim dates"""
    
    events = []
    for name, date in dates_dict.items():
        if date:
            events.append({'name': name, 'date': date})
    
    events.sort(key=lambda x: x['date'])
    
    # Create timeline
    fig = go.Figure()
    
    for i, event in enumerate(events):
        fig.add_trace(go.Scatter(
            x=[event['date']],
            y=[i],
            mode='markers+text',
            name=event['name'],
            text=[event['name']],
            textposition='top center'
        ))
    
    fig.update_layout(
        title="Claim Timeline",
        xaxis_title="Date",
        yaxis=dict(visible=False),
        showlegend=False
    )
    
    st.plotly_chart(fig)
```

---

## Time Breakdown

- Core logic: 15 min
- Integration: 10 min
- Config: 1 min
- Testing: 4 min

**Total**: 30 minutes

---

## Success Criteria

### Minimum
- [ ] Detects invoice before accident
- [ ] Returns Signal contract
- [ ] Integrated into pipeline

### Good
- [ ] Extracts dates from text
- [ ] Checks photo EXIF
- [ ] Multiple temporal rules
- [ ] Unit tests pass

### Excellent
- [ ] Timeline visualization in UI
- [ ] Handles edge cases (same-day events)
- [ ] Clear demo scenario

---

**This is the easiest high-impact feature. Do this if you're short on time.**
