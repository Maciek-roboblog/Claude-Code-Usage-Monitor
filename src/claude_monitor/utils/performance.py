"""Performance monitoring utilities for Claude Monitor.

This module provides performance monitoring capabilities including:
- CPU and memory usage detection
- Execution time measurement
- System load monitoring
- Performance threshold management
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

import psutil


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""

    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    execution_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerformanceThresholds:
    """Performance threshold configuration."""

    cpu_warning: float = 70.0  # CPU % warning threshold
    cpu_critical: float = 85.0  # CPU % critical threshold
    memory_warning: float = 80.0  # Memory % warning threshold
    memory_critical: float = 90.0  # Memory % critical threshold
    execution_warning_ms: float = 50.0  # Execution time warning (ms)
    execution_critical_ms: float = 100.0  # Execution time critical (ms)


class PerformanceMonitor:
    """System performance monitoring and metrics collection."""

    def __init__(self, thresholds: Optional[PerformanceThresholds] = None):
        """Initialize performance monitor.

        Args:
            thresholds: Performance thresholds configuration
        """
        self.thresholds = thresholds or PerformanceThresholds()
        self._metrics_history: Dict[str, list] = {}
        self._lock = threading.Lock()
        self._process = psutil.Process()

    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current system performance metrics.

        Returns:
            Current performance metrics
        """
        try:
            # Get CPU usage (non-blocking)
            cpu_percent = self._process.cpu_percent()

            # Get memory info
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB

            # Get system memory percentage
            system_memory = psutil.virtual_memory()
            memory_percent = system_memory.percent

            return PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_mb,
                timestamp=time.time(),
            )
        except Exception:
            # Return default metrics if process monitoring fails
            return PerformanceMetrics()

    def get_system_load(self) -> float:
        """Get current system CPU load average.

        Returns:
            System load average (0-100%)
        """
        try:
            return float(psutil.cpu_percent(interval=0.1))
        except Exception:
            return 0.0

    def is_high_load(self) -> bool:
        """Check if system is under high load.

        Returns:
            True if system load exceeds warning threshold
        """
        current_load = self.get_system_load()
        return current_load > self.thresholds.cpu_warning

    def is_critical_load(self) -> bool:
        """Check if system is under critical load.

        Returns:
            True if system load exceeds critical threshold
        """
        current_load = self.get_system_load()
        return current_load > self.thresholds.cpu_critical

    @contextmanager
    def measure_execution_time(self, operation_name: str = "operation"):
        """Context manager to measure execution time.

        Args:
            operation_name: Name of the operation being measured

        Yields:
            Performance metrics with execution time
        """
        start_time = time.perf_counter()
        metrics = self.get_current_metrics()

        try:
            yield metrics
        finally:
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            # Update metrics with execution time
            metrics.execution_time_ms = execution_time_ms

            # Store in history
            with self._lock:
                if operation_name not in self._metrics_history:
                    self._metrics_history[operation_name] = []

                self._metrics_history[operation_name].append(metrics)

                # Keep only last 100 measurements per operation
                if len(self._metrics_history[operation_name]) > 100:
                    self._metrics_history[operation_name] = self._metrics_history[
                        operation_name
                    ][-100:]

    def get_average_execution_time(self, operation_name: str) -> float:
        """Get average execution time for an operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Average execution time in milliseconds
        """
        with self._lock:
            if operation_name not in self._metrics_history:
                return 0.0

            metrics_list = self._metrics_history[operation_name]
            if not metrics_list:
                return 0.0

            total_time = sum(m.execution_time_ms for m in metrics_list)
            return float(total_time) / float(len(metrics_list))

    def get_performance_warning(self) -> Optional[str]:
        """Get performance warning message if thresholds exceeded.

        Returns:
            Warning message or None if performance is acceptable
        """
        metrics = self.get_current_metrics()
        warnings = []

        if metrics.cpu_percent > self.thresholds.cpu_critical:
            warnings.append(f"Critical CPU usage: {metrics.cpu_percent:.1f}%")
        elif metrics.cpu_percent > self.thresholds.cpu_warning:
            warnings.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")

        if metrics.memory_percent > self.thresholds.memory_critical:
            warnings.append(f"Critical memory usage: {metrics.memory_percent:.1f}%")
        elif metrics.memory_percent > self.thresholds.memory_warning:
            warnings.append(f"High memory usage: {metrics.memory_percent:.1f}%")

        if warnings:
            return " | ".join(warnings)

        return None

    def should_reduce_refresh_rate(self) -> bool:
        """Check if refresh rate should be reduced due to performance.

        Returns:
            True if performance suggests reducing refresh rate
        """
        return self.is_high_load() or self.get_performance_warning() is not None

    def get_recommended_refresh_rate(self, current_rate: float) -> float:
        """Get recommended refresh rate based on current performance.

        Args:
            current_rate: Current refresh rate in seconds

        Returns:
            Recommended refresh rate in seconds
        """
        if self.is_critical_load():
            # Double the refresh rate (reduce frequency) for critical load
            return min(current_rate * 2.0, 10.0)
        elif self.is_high_load():
            # Increase refresh rate by 50% for high load
            return min(current_rate * 1.5, 5.0)

        return current_rate

    def clear_history(self, operation_name: Optional[str] = None):
        """Clear performance metrics history.

        Args:
            operation_name: Specific operation to clear, or None for all
        """
        with self._lock:
            if operation_name:
                self._metrics_history.pop(operation_name, None)
            else:
                self._metrics_history.clear()


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance.

    Returns:
        Global PerformanceMonitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def measure_performance(operation_name: str = "operation"):
    """Decorator to measure function execution performance.

    Args:
        operation_name: Name of the operation being measured

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            monitor = get_performance_monitor()
            with monitor.measure_execution_time(operation_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator
