import time
from typing import Dict
from mcp_gateway.config import Backend

class CircuitBreakerOpen(Exception):
    def __init__(self, backend_name: str):
        super().__init__(f"Circuit breaker is OPEN for backend {backend_name}")

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = 0.0

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        if self.state == "HALF_OPEN":
            # Only allow one test request
            return True
        return False

class ResilienceManager:
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, backend: Backend) -> CircuitBreaker:
        if backend.name not in self.breakers:
            self.breakers[backend.name] = CircuitBreaker()
        return self.breakers[backend.name]

# Global resilience manager
resilience_manager = ResilienceManager()
