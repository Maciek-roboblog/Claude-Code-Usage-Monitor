"""Compact refresh manager for performance-optimized refresh rate management.

Manages refresh intervals, system load detection, and performance warnings
for the compact display mode.
"""

import logging
import time
from typing import Optional

from claude_monitor.utils.performance import (
    PerformanceThresholds,
    get_performance_monitor,
)

logger = logging.getLogger(__name__)


class CompactRefreshManager:
    """Manages refresh rate dynamically based on system performance.

    Provides intelligent refresh rate adjustment for compact display mode,
    balancing performance and responsiveness.
    """

    DEFAULT_REFRESH_RATE = 10.0
    MIN_REFRESH_RATE = 0.1
    MAX_REFRESH_RATE = 300.0

    def __init__(
        self,
        refresh_rate: float = DEFAULT_REFRESH_RATE,
        performance_thresholds: Optional[PerformanceThresholds] = None,
    ):
        """Initialize the refresh manager with performance monitoring."""
        self.base_refresh_rate = self._validate_refresh_rate(refresh_rate)
        self.current_refresh_rate = self.base_refresh_rate

        # Performance monitoring
        self.performance_monitor = get_performance_monitor()
        self.performance_thresholds = performance_thresholds or PerformanceThresholds()

        # Simple state
        self.last_adjustment_time = 0.0
        self.adjustment_cooldown = 30.0  # 30 seconds between adjustments

    def _validate_refresh_rate(self, refresh_rate: float) -> float:
        """Validate and normalize the refresh rate."""

        if not isinstance(refresh_rate, (int, float)):
            logger.warning(
                f"Invalid refresh rate type: {type(refresh_rate)}, using default"
            )
            return self.DEFAULT_REFRESH_RATE

        rate = float(refresh_rate)

        if rate < self.MIN_REFRESH_RATE:
            logger.warning(
                f"Refresh rate {rate} too low, using minimum {self.MIN_REFRESH_RATE}"
            )
            return self.MIN_REFRESH_RATE
        elif rate > self.MAX_REFRESH_RATE:
            logger.warning(
                f"Refresh rate {rate} too high, using maximum {self.MAX_REFRESH_RATE}"
            )
            return self.MAX_REFRESH_RATE

        return rate

    def get_refresh_interval(self) -> float:
        """Get the current refresh interval."""
        return self.current_refresh_rate

    def should_warn_performance(self) -> bool:
        """Check if a performance warning should be displayed."""
        try:
            metrics = self.performance_monitor.get_current_metrics()

            # Apply performance-based thresholds
            if metrics.cpu_percent > 85.0:
                return True
            if metrics.memory_percent > 90.0:
                return True

            return False
        except Exception:
            return False

    def get_performance_warning(self) -> Optional[str]:
        """Get the performance warning message if needed."""
        if not self.should_warn_performance():
            return None

        try:
            metrics = self.performance_monitor.get_current_metrics()

            warnings = []
            if metrics.cpu_percent > 85.0:
                warnings.append(f"High CPU: {metrics.cpu_percent:.1f}%")
            if metrics.memory_percent > 90.0:
                warnings.append(f"High memory: {metrics.memory_percent:.1f}%")

            return " | ".join(warnings) if warnings else None
        except Exception:
            return "Performance monitoring unavailable"

    def adjust_for_load(self) -> float:
        """Adjust the refresh rate based on system load.

        Returns optimized refresh interval based on current system performance.
        """
        current_time = time.time()

        # Simple cooldown to avoid too frequent adjustments
        if current_time - self.last_adjustment_time < self.adjustment_cooldown:
            return self.current_refresh_rate

        try:
            metrics = self.performance_monitor.get_current_metrics()
            system_load = self.performance_monitor.get_system_load()

            # Calculate adjustment using performance-based multipliers
            multiplier = 1.0

            # Adjustments based on CPU
            if system_load > 90:
                multiplier = 2.0  # Slow down significantly
            elif system_load > 75:
                multiplier = 1.5  # Slow down moderately
            elif metrics.memory_percent > 85:
                multiplier = 1.3  # Slightly slow down for memory

            # Apply adjustment
            new_rate = self.base_refresh_rate * multiplier
            new_rate = self._validate_refresh_rate(new_rate)

            if new_rate != self.current_refresh_rate:
                logger.debug(
                    f"Refresh rate adjusted: {self.current_refresh_rate:.1f}s → {new_rate:.1f}s"
                )
                self.current_refresh_rate = new_rate
                self.last_adjustment_time = current_time

            return self.current_refresh_rate

        except Exception as e:
            logger.warning(f"Failed to adjust refresh rate: {e}")
            return self.current_refresh_rate

    def get_refresh_recommendations(self) -> dict:
        """Get simple recommendations for optimization."""
        try:
            metrics = self.performance_monitor.get_current_metrics()
            system_load = self.performance_monitor.get_system_load()

            recommendations = []

            if system_load > 80:
                recommendations.append("Consider increasing the refresh interval")
            elif (
                system_load < 30 and self.current_refresh_rate > self.base_refresh_rate
            ):
                recommendations.append("You may reduce the refresh interval")

            if metrics.memory_percent > 85:
                recommendations.append(
                    "High memory - less frequent monitoring recommended"
                )

            return {
                "current_rate": self.current_refresh_rate,
                "base_rate": self.base_refresh_rate,
                "system_load": system_load,
                "recommendations": recommendations,
            }
        except Exception:
            return {
                "current_rate": self.current_refresh_rate,
                "base_rate": self.base_refresh_rate,
                "recommendations": ["Performance monitoring unavailable"],
            }

    def reset_to_base_rate(self) -> None:
        """Reset the refresh rate to its base value."""
        if self.current_refresh_rate != self.base_refresh_rate:
            logger.debug(
                f"Reset refresh rate: {self.current_refresh_rate:.1f}s → {self.base_refresh_rate:.1f}s"
            )
            self.current_refresh_rate = self.base_refresh_rate
            self.last_adjustment_time = 0.0
