"""
Rate Limiter Service
IP-based rate limiting to prevent abuse
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict
import threading

# Configuration
MAX_FILES_PER_REQUEST = 25
MAX_CONVERSIONS_PER_DAY = 100
RATE_LIMIT_WINDOW_SECONDS = 86400  # 24 hours


@dataclass
class IPUsage:
    conversions_today: int = 0
    last_reset: float = field(default_factory=time.time)
    

class RateLimiter:
    """
    Simple in-memory IP-based rate limiter.
    Tracks conversions per IP address with daily limits.
    """
    
    def __init__(self):
        self._usage: Dict[str, IPUsage] = defaultdict(IPUsage)
        self._lock = threading.Lock()
    
    def _get_client_usage(self, ip: str) -> IPUsage:
        """Get or create usage record for an IP."""
        with self._lock:
            usage = self._usage[ip]
            
            # Reset if a new day
            now = time.time()
            if now - usage.last_reset > RATE_LIMIT_WINDOW_SECONDS:
                usage.conversions_today = 0
                usage.last_reset = now
            
            return usage
    
    def check_limit(self, ip: str, file_count: int = 1) -> tuple[bool, str]:
        """
        Check if the request is within limits.
        
        Returns:
            (allowed, message) tuple
        """
        # Check per-request file limit
        if file_count > MAX_FILES_PER_REQUEST:
            return False, f"Maximum {MAX_FILES_PER_REQUEST} files per request"
        
        # Check daily limit
        usage = self._get_client_usage(ip)
        
        if usage.conversions_today + file_count > MAX_CONVERSIONS_PER_DAY:
            remaining = MAX_CONVERSIONS_PER_DAY - usage.conversions_today
            if remaining <= 0:
                return False, f"Daily limit reached ({MAX_CONVERSIONS_PER_DAY} conversions). Resets in {self._time_until_reset(usage)} hours."
            else:
                return False, f"This would exceed your daily limit. You have {remaining} conversions remaining today."
        
        return True, "OK"
    
    def record_usage(self, ip: str, file_count: int = 1):
        """Record successful conversions for an IP."""
        with self._lock:
            usage = self._usage[ip]
            usage.conversions_today += file_count
    
    def get_remaining(self, ip: str) -> int:
        """Get remaining conversions for today."""
        usage = self._get_client_usage(ip)
        return max(0, MAX_CONVERSIONS_PER_DAY - usage.conversions_today)
    
    def _time_until_reset(self, usage: IPUsage) -> int:
        """Get hours until reset."""
        elapsed = time.time() - usage.last_reset
        remaining_seconds = max(0, RATE_LIMIT_WINDOW_SECONDS - elapsed)
        return int(remaining_seconds / 3600)
    
    def cleanup_old_entries(self):
        """Remove stale entries to prevent memory leaks."""
        with self._lock:
            now = time.time()
            stale_ips = [
                ip for ip, usage in self._usage.items()
                if now - usage.last_reset > RATE_LIMIT_WINDOW_SECONDS * 2
            ]
            for ip in stale_ips:
                del self._usage[ip]


# Singleton instance
rate_limiter = RateLimiter()
