import time
import uuid
import math
import logging
from datetime import datetime, timezone
from sqlalchemy import select

from db.session import SessionLocal
from models.session import UserSession

logger = logging.getLogger(__name__)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates haversine distance between two coordinates in kilometers."""
    R = 6371.0  # Earth radius
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def check_impossible_travel(
    ip1: str, time1: datetime, ip2: str, time2: datetime, max_speed_kmh: float = 900.0
) -> bool:
    """
    Checks if travel between two IP login points is physically impossible.
    Defaults to 900 km/h speed threshold over less than a 2-hour window.
    """
    if ip1 == ip2:
        return False

    # Mock geolocations for demonstration
    # In production, this would query a MaxMind geoIP database
    geo_db = {
        "127.0.0.1": (37.7749, -122.4194),  # San Francisco
        "8.8.8.8": (37.751, -97.822),       # US Central
        "192.168.1.1": (40.7128, -74.0060)  # New York
    }
    
    loc1 = geo_db.get(ip1, (37.7749, -122.4194))
    loc2 = geo_db.get(ip2, (40.7128, -74.0060))
    
    distance = calculate_distance(loc1[0], loc1[1], loc2[0], loc2[1])
    time_diff_hours = abs((time2 - time1).total_seconds()) / 3600.0
    
    if time_diff_hours == 0:
        return distance > 0  # Travel distance > 0 with zero time difference is impossible
        
    speed = distance / time_diff_hours
    
    if speed > max_speed_kmh and time_diff_hours < 2.0:
        logger.warning(f"Impossible travel detected: {speed:.1f} km/h between {ip1} and {ip2} within {time_diff_hours:.2f} hours.")
        return True
        
    return False


class RiskBasedAuthenticationService:
    @classmethod
    def calculate_risk_score(cls, context: dict) -> float:
        """
        Calculates a risk score (0-100) based on multiple telemetry signals.
        """
        score = 0.0
        
        # 1. New Device (User Agent mismatch)
        if context.get("device_changed", False):
            score += 15.0
            
        # 2. Impossible Travel
        if context.get("impossible_travel_detected", False):
            score += 50.0
            
        # 3. VPN / Proxy detection
        if context.get("is_vpn", False):
            score += 25.0
            
        # 4. Tor Exit Node
        if context.get("is_tor", False):
            score += 35.0
            
        # 5. IP Reputation blacklist
        if context.get("is_blacklisted_ip", False):
            score += 20.0
            
        # 6. Historical failed logins
        failed_count = context.get("failed_logins_count", 0)
        score += min(30.0, failed_count * 10.0)
        
        return min(100.0, score)

    @classmethod
    def require_step_up_auth(cls, context: dict, threshold: float = 50.0) -> bool:
        """Returns True if the calculated risk score warrants a step-up OTP challenge."""
        risk_score = cls.calculate_risk_score(context)
        logger.info(f"Computed login risk score: {risk_score}% (Threshold: {threshold}%)")
        return risk_score >= threshold


def enforce_concurrent_session_limits(db, user_id: uuid.UUID, limit: int = 5):
    """
    Enforces maximum concurrent active sessions per user account.
    Automatically revokes the oldest active session if the limit is exceeded.
    """
    stmt = (
        select(UserSession)
        .where(UserSession.user_id == user_id, UserSession.is_revoked == False)
        .order_by(UserSession.created_at.asc())
    )
    active_sessions = list(db.scalars(stmt).all())
    
    if len(active_sessions) >= limit:
        excess_count = len(active_sessions) - limit + 1
        logger.info(f"User {user_id} exceeded session limit ({len(active_sessions)}/{limit}). Revoking oldest {excess_count} sessions.")
        
        for idx in range(excess_count):
            old_session = active_sessions[idx]
            old_session.is_revoked = True
            
        db.commit()
