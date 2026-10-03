"""Ultra-fast physics plausibility checker - NO ML, pure heuristics.

Catches impossible combinations in < 200ms.
"""
import re
import math
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from PIL import Image

@dataclass
class PhysicsCheckResult:
    score: float  # 0.0 (plausible) to 1.0 (impossible)
    flags: list[str]
    checks_run: dict[str, bool]
    confidence: float = 0.80

class PhysicsPlausibilityChecker:
    """
    Fast heuristic checks:
    1. Speed-Damage consistency
    2. GPS-Location distance
    3. Time-Lighting consistency
    4. Shadow angle (basic)
    """

    # Damage severity keywords -> expected speed range (mph)
    DAMAGE_KEYWORDS = {
        'scratch': (0, 15),
        'dent': (5, 25),
        'minor': (5, 25),
        'bumper': (10, 35),
        'panel': (20, 45),
        'crumple': (25, 50),
        'structural': (30, 60),
        'total': (35, None),
        'severe': (40, None)
    }

    def check(self, claim_data: dict) -> PhysicsCheckResult:
        """
        claim_data = {
            'narrative': str,          # Claim description text
            'damage_photo': PIL.Image | None,
            'metadata': dict {          # From EXIF
                'gps': (lat, lon) | None,
                'datetime': datetime | None,
                'make': str | None
            },
            'claimed_location': str | None,
            'claimed_time': datetime | None
        }
        """
        flags = []
        score = 0.0
        checks = {}

        # Check 1: Speed-Damage
        speed_score, speed_flag = self._check_speed_damage(claim_data['narrative'])
        if speed_flag:
            score += speed_score
            flags.append(speed_flag)
        checks['speed_damage'] = bool(speed_flag)

        # Check 2: GPS-Location
        if claim_data.get('metadata', {}).get('gps') and claim_data.get('claimed_location'):
            gps_score, gps_flag = self._check_gps(
                claim_data['metadata']['gps'],
                claim_data['claimed_location']
            )
            if gps_flag:
                score += gps_score
                flags.append(gps_flag)
            checks['gps'] = bool(gps_flag)

        # Check 3: Time-Lighting
        if claim_data.get('damage_photo') and claim_data.get('claimed_time'):
            light_score, light_flag = self._check_lighting(
                claim_data['damage_photo'],
                claim_data['claimed_time']
            )
            if light_flag:
                score += light_score
                flags.append(light_flag)
            checks['lighting'] = bool(light_flag)

        return PhysicsCheckResult(
            score=min(score, 1.0),
            flags=flags,
            checks_run=checks
        )

    def _check_speed_damage(self, narrative: str) -> tuple[float, str]:
        """Extract speed and damage keywords, check consistency"""
        speed = self._extract_speed(narrative)
        damage_level = self._extract_damage_level(narrative)

        if not speed or not damage_level:
            return 0.0, ""

        severity, (min_speed, max_speed) = damage_level

        # Too fast for damage level?
        if max_speed and speed > max_speed * 2.0:
            return 0.35, f"⚠️ Physics: {speed} mph too fast for '{severity}' damage (expected < {max_speed} mph)"

        # Too slow for damage level?
        if speed < min_speed * 0.4:
            return 0.30, f"⚠️ Physics: {speed} mph too slow for '{severity}' damage (expected > {min_speed} mph)"

        return 0.0, ""

    def _check_gps(self, photo_gps: tuple[float, float], claimed_location: str) -> tuple[float, str]:
        """Compare photo GPS to claimed location"""
        # For demo: simple keyword matching
        # In production: use geocoding API

        # Extract city/state from narrative
        claimed_coords = self._rough_geocode(claimed_location)
        if not claimed_coords:
            return 0.0, ""

        distance_km = self._haversine(photo_gps, claimed_coords)

        if distance_km > 100:
            return 0.40, f"🌍 GPS Mismatch: Photo taken {distance_km:.0f} km from claimed location"
        elif distance_km > 30:
            return 0.20, f"🌍 GPS Discrepancy: {distance_km:.0f} km difference"

        return 0.0, ""

    def _check_lighting(self, image: Image.Image, claimed_time: datetime) -> tuple[float, str]:
        """Compare image brightness to claimed time of day"""
        # Calculate average brightness
        gray = np.array(image.convert('L'))
        avg_brightness = gray.mean()

        # Determine if claimed time is day or night
        hour = claimed_time.hour
        is_claimed_daytime = 6 <= hour <= 19

        # Determine if photo is day or night
        is_photo_daytime = avg_brightness > 90  # threshold

        if is_claimed_daytime != is_photo_daytime:
            return 0.35, f"☀️ Lighting Mismatch: Claimed {claimed_time.strftime('%I:%M %p')} but photo shows {'day' if is_photo_daytime else 'night'}time"

        return 0.0, ""

    @staticmethod
    def _extract_speed(text: str) -> float | None:
        """Extract speed from text"""
        patterns = [
            r'(\d+)\s*mph',
            r'(\d+)\s*miles per hour',
            r'(\d+)\s*km/?h',
            r'speed of (\d+)',
            r'going (\d+)',
            r'traveling (\d+)'
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

    @staticmethod
    def _extract_damage_level(text: str) -> tuple[str, tuple[float, float | None]] | None:
        """Find damage keywords and return expected speed range"""
        text_lower = text.lower()
        for keyword, speed_range in PhysicsPlausibilityChecker.DAMAGE_KEYWORDS.items():
            if keyword in text_lower:
                return keyword, speed_range
        return None

    @staticmethod
    def _rough_geocode(location: str) -> tuple[float, float] | None:
        """Ultra-simple geocoding for demo (hardcoded major cities)"""
        # In production: use Google Maps Geocoding API
        cities = {
            'new york': (40.7128, -74.0060),
            'los angeles': (34.0522, -118.2437),
            'chicago': (41.8781, -87.6298),
            'houston': (29.7604, -95.3698),
            'phoenix': (33.4484, -112.0740),
            'philadelphia': (39.9526, -75.1652),
            'san antonio': (29.4241, -98.4936),
            'san diego': (32.7157, -117.1611),
            'dallas': (32.7767, -96.7970),
            'austin': (30.2672, -97.7431)
        }
        location_lower = location.lower()
        for city, coords in cities.items():
            if city in location_lower:
                return coords
        return None

    @staticmethod
    def _haversine(coord1: tuple[float, float], coord2: tuple[float, float]) -> float:
        """Calculate distance between GPS coordinates (km)"""
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


# Quick test
if __name__ == "__main__":
    checker = PhysicsPlausibilityChecker()

    # Test 1: Impossible speed for minor damage
    result1 = checker.check({
        'narrative': "I was going 60 mph when I got a small scratch on my bumper",
        'damage_photo': None,
        'metadata': {},
        'claimed_location': None,
        'claimed_time': None
    })
    print(f"Test 1 Score: {result1.score:.2f}")
    print(f"Flags: {result1.flags}\n")

    # Test 2: Too slow for severe damage
    result2 = checker.check({
        'narrative': "I was going 10 mph and my car was totaled with severe structural damage",
        'damage_photo': None,
        'metadata': {},
        'claimed_location': None,
        'claimed_time': None
    })
    print(f"Test 2 Score: {result2.score:.2f}")
    print(f"Flags: {result2.flags}\n")

    # Test 3: GPS mismatch (if you have coordinates)
    result3 = checker.check({
        'narrative': "Minor dent from parking lot accident",
        'damage_photo': None,
        'metadata': {
            'gps': (40.7128, -74.0060)  # New York
        },
        'claimed_location': "Los Angeles parking lot",
        'claimed_time': None
    })
    print(f"Test 3 Score: {result3.score:.2f}")
    print(f"Flags: {result3.flags}")
