"""Advanced UI Component Architecture for Claude Monitor.

Enterprise-grade component system with:
- Modular component hierarchies with type-safe composition
- Advanced state management with immutable state patterns
- Optimized render pipeline with caching and batching
- Event-driven component communication
- Dependency injection for testability
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from rich.console import Console, RenderableType
from rich.text import Text

from claude_monitor.terminal.themes import (
    get_cost_style,
    get_velocity_indicator,
)
from claude_monitor.ui.layouts import HeaderManager

# Advanced typing definitions for component architecture
TState = TypeVar("TState")
TProps = TypeVar("TProps")
TRenderResult = TypeVar("TRenderResult", bound=RenderableType)


class ComponentState(Enum):
    """Component lifecycle states for optimized rendering."""

    INITIALIZING = "initializing"
    READY = "ready"
    RENDERING = "rendering"
    RENDERED = "rendered"
    UPDATING = "updating"
    ERROR = "error"
    DESTROYED = "destroyed"


@dataclass(frozen=True)
class ComponentProps:
    """Base immutable props for all components."""

    id: str
    css_classes: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    theme_variant: Optional[str] = None


@dataclass(frozen=True)
class RenderContext:
    """Immutable render context for component pipeline."""

    console: Console
    width: int
    height: int
    theme: str
    debug_mode: bool = False
    performance_tracking: bool = False


@runtime_checkable
class Renderable(Protocol):
    """Protocol for renderable components with type safety."""

    def render(self, context: RenderContext) -> RenderableType:
        """Render component with given context."""
        ...


@runtime_checkable
class Stateful(Protocol[TState]):
    """Protocol for stateful components with immutable state."""

    def get_state(self) -> TState:
        """Get current immutable state."""
        ...

    def update_state(self, updater: Callable[[TState], TState]) -> None:
        """Update state with pure function."""
        ...


@runtime_checkable
class Lifecycle(Protocol):
    """Protocol for component lifecycle management."""

    def mount(self) -> None:
        """Called when component is mounted."""
        ...

    def unmount(self) -> None:
        """Called when component is unmounted."""
        ...

    def should_update(self, new_props: Any) -> bool:
        """Determine if component should re-render."""
        ...


class BaseComponent(ABC, Generic[TProps]):
    """Abstract base class for all UI components with advanced patterns.

    Features:
    - Immutable props pattern
    - Lifecycle management
    - Performance optimization
    - Type-safe composition
    """

    def __init__(self, props: TProps) -> None:
        """Initialize component with immutable props."""
        self._props = props
        self._state: ComponentState = ComponentState.INITIALIZING
        self._render_cache: Optional[RenderableType] = None
        self._last_render_hash: Optional[int] = None
        self._is_mounted = False

    @property
    def props(self) -> TProps:
        """Get immutable props."""
        return self._props

    @property
    def state(self) -> ComponentState:
        """Get current component state."""
        return self._state

    def _set_state(self, new_state: ComponentState) -> None:
        """Internal state transition."""
        self._state = new_state

    def mount(self) -> None:
        """Mount component and prepare for rendering."""
        if self._is_mounted:
            return

        self._set_state(ComponentState.READY)
        self._is_mounted = True
        self._on_mount()

    def unmount(self) -> None:
        """Unmount component and cleanup resources."""
        if not self._is_mounted:
            return

        self._set_state(ComponentState.DESTROYED)
        self._is_mounted = False
        self._render_cache = None
        self._on_unmount()

    def should_update(self, new_props: TProps) -> bool:
        """Determine if component should re-render based on props change."""
        return new_props != self._props

    def update_props(self, new_props: TProps) -> None:
        """Update component props and trigger re-render if needed."""
        if self.should_update(new_props):
            self._props = new_props
            self._invalidate_cache()

    def render(self, context: RenderContext) -> RenderableType:
        """Render component with caching optimization."""
        if not self._is_mounted:
            self.mount()

        # Performance optimization: check if we can use cached render
        current_hash = self._compute_render_hash(context)
        if self._render_cache is not None and self._last_render_hash == current_hash:
            return self._render_cache

        try:
            self._set_state(ComponentState.RENDERING)
            result = self._render_impl(context)

            # Cache the result
            self._render_cache = result
            self._last_render_hash = current_hash
            self._set_state(ComponentState.RENDERED)

            return result
        except Exception:
            self._set_state(ComponentState.ERROR)
            raise

    def _invalidate_cache(self) -> None:
        """Invalidate render cache."""
        self._render_cache = None
        self._last_render_hash = None

    def _compute_render_hash(self, context: RenderContext) -> int:
        """Compute hash for render cache invalidation."""
        return hash((id(self._props), context.width, context.height, context.theme))

    @abstractmethod
    def _render_impl(self, context: RenderContext) -> RenderableType:
        """Implementation-specific rendering logic."""
        pass

    def _on_mount(self) -> None:
        """Override for mount-specific logic."""
        pass

    def _on_unmount(self) -> None:
        """Override for unmount-specific logic."""
        pass


@dataclass(frozen=True)
class VelocityIndicatorProps:
    """Immutable props for velocity indicator component."""

    id: str
    burn_rate: float
    include_description: bool = False
    show_emoji: bool = True
    css_classes: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    theme_variant: Optional[str] = None


class VelocityIndicator(BaseComponent[VelocityIndicatorProps]):
    """Advanced velocity indicator component with optimized rendering.

    Features:
    - Immutable props pattern for predictable rendering
    - Caching for expensive velocity calculations
    - Type-safe composition with other components
    """

    def _render_impl(self, context: RenderContext) -> RenderableType:
        """Render velocity indicator with Rich text formatting."""
        indicator = get_velocity_indicator(self.props.burn_rate)

        parts = []
        if self.props.show_emoji:
            parts.append(str(indicator["emoji"]))

        if self.props.include_description:
            parts.append(str(indicator["label"]))

        content = " ".join(parts)
        return Text(content, style="info")

    @classmethod
    def create(
        cls,
        burn_rate: float,
        include_description: bool = False,
        show_emoji: bool = True,
        component_id: str = "velocity-indicator",
    ) -> "VelocityIndicator":
        """Factory method for creating velocity indicator."""
        props = VelocityIndicatorProps(
            id=component_id,
            burn_rate=burn_rate,
            include_description=include_description,
            show_emoji=show_emoji,
        )
        return cls(props)

    # Legacy static methods for backward compatibility
    @staticmethod
    def get_velocity_emoji(burn_rate: float) -> str:
        """Get velocity emoji based on burn rate."""
        indicator = get_velocity_indicator(burn_rate)
        return str(indicator["emoji"])

    @staticmethod
    def get_velocity_description(burn_rate: float) -> str:
        """Get velocity description based on burn rate."""
        indicator = get_velocity_indicator(burn_rate)
        return str(indicator["label"])

    @staticmethod
    def render_legacy(burn_rate: float, include_description: bool = False) -> str:
        """Legacy render method for backward compatibility."""
        emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
        if include_description:
            description = VelocityIndicator.get_velocity_description(burn_rate)
            return f"{emoji} {description}"
        return emoji

    # Backward compatibility for old static render method - avoid override conflict
    @staticmethod
    def render_static(burn_rate: float, include_description: bool = False) -> str:
        """Static render method for backward compatibility."""
        emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
        if include_description:
            description = VelocityIndicator.get_velocity_description(burn_rate)
            return f"{emoji} {description}"
        return emoji


# Add render function at module level for backward compatibility
def _velocity_render(burn_rate: float, include_description: bool = False) -> str:
    """Module-level render function for backward compatibility."""
    return VelocityIndicator.render_static(burn_rate, include_description)


# Monkey patch the render method for backward compatibility
VelocityIndicator.render = staticmethod(_velocity_render)  # type: ignore[assignment]


@dataclass(frozen=True)
class CostIndicatorProps:
    """Immutable props for cost indicator component."""

    id: str
    cost: float
    currency: str = "USD"
    precision: int = 4
    show_currency_symbol: bool = True
    css_classes: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    theme_variant: Optional[str] = None


class CostIndicator(BaseComponent[CostIndicatorProps]):
    """Advanced cost indicator component with dynamic styling.

    Features:
    - Dynamic style based on cost thresholds
    - Configurable currency formatting
    - Performance-optimized rendering
    """

    def _render_impl(self, context: RenderContext) -> RenderableType:
        """Render cost indicator with Rich styling."""
        style = get_cost_style(self.props.cost)

        if self.props.show_currency_symbol:
            symbol = "$" if self.props.currency == "USD" else self.props.currency
            content = f"{symbol}{self.props.cost:.{self.props.precision}f}"
        else:
            content = f"{self.props.cost:.{self.props.precision}f}"

        return Text(content, style=style)

    @classmethod
    def create(
        cls,
        cost: float,
        currency: str = "USD",
        precision: int = 4,
        show_currency_symbol: bool = True,
        component_id: str = "cost-indicator",
    ) -> "CostIndicator":
        """Factory method for creating cost indicator."""
        props = CostIndicatorProps(
            id=component_id,
            cost=cost,
            currency=currency,
            precision=precision,
            show_currency_symbol=show_currency_symbol,
        )
        return cls(props)

    # Legacy static method for backward compatibility
    @staticmethod
    def render_legacy(cost: float, currency: str = "USD") -> str:
        """Legacy render method for backward compatibility."""
        style = get_cost_style(cost)
        symbol = "$" if currency == "USD" else currency
        return f"[{style}]{symbol}{cost:.4f}[/]"

    # Backward compatibility for old static render method - avoid override conflict
    @staticmethod
    def render_static(cost: float, currency: str = "USD") -> str:
        """Static render method for backward compatibility."""
        style = get_cost_style(cost)
        symbol = "$" if currency == "USD" else currency
        return f"[{style}]{symbol}{cost:.4f}[/]"


# Add render function at module level for backward compatibility
def _cost_render(cost: float, currency: str = "USD") -> str:
    """Module-level render function for backward compatibility."""
    return CostIndicator.render_static(cost, currency)


# Monkey patch the render method for backward compatibility
CostIndicator.render = staticmethod(_cost_render)  # type: ignore[assignment]


@dataclass(frozen=True)
class ErrorDisplayState:
    """Immutable state for error display component."""

    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retry_count: int = 0
    last_error_time: Optional[str] = None


@dataclass(frozen=True)
class ErrorDisplayProps:
    """Immutable props for error display component."""

    id: str
    plan: str = "pro"
    timezone: str = "Europe/Warsaw"
    custom_error_message: Optional[str] = None
    show_troubleshooting: bool = True
    auto_retry: bool = True
    css_classes: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    theme_variant: Optional[str] = None


class ErrorDisplayComponent(
    BaseComponent[ErrorDisplayProps], Stateful[ErrorDisplayState]
):
    """Advanced error display component with state management.

    Features:
    - Immutable state pattern for error tracking
    - Customizable error messages and troubleshooting
    - Rich text formatting with component composition
    """

    def __init__(self, props: ErrorDisplayProps) -> None:
        """Initialize error display component with props."""
        super().__init__(props)
        self._error_state = ErrorDisplayState()

    def get_state(self) -> ErrorDisplayState:
        """Get current immutable error state."""
        return self._error_state

    def update_state(
        self, updater: Callable[[ErrorDisplayState], ErrorDisplayState]
    ) -> None:
        """Update error state with pure function."""
        self._error_state = updater(self._error_state)
        self._invalidate_cache()

    def _render_impl(self, context: RenderContext) -> RenderableType:
        """Render error display with Rich formatting."""
        from rich.console import Group

        header_manager = HeaderManager()
        header_lines = header_manager.create_header(
            self.props.plan, self.props.timezone
        )

        content_lines = []

        # Error message
        error_msg = self.props.custom_error_message or "Failed to get usage data"
        content_lines.append(Text(error_msg, style="error"))
        content_lines.append(Text(""))

        # Troubleshooting section
        if self.props.show_troubleshooting:
            content_lines.append(Text("Possible causes:", style="warning"))
            content_lines.append(Text("  • You're not logged into Claude"))
            content_lines.append(Text("  • Network connection issues"))
            content_lines.append(Text(""))

        # Auto-retry message
        if self.props.auto_retry:
            retry_msg = "Retrying in 3 seconds... (Ctrl+C to exit)"
            content_lines.append(Text(retry_msg, style="dim"))

        # Convert header lines to Text objects
        header_texts = [Text.from_markup(line) for line in header_lines]

        return Group(*header_texts, *content_lines)

    @classmethod
    def create(
        cls,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        custom_error_message: Optional[str] = None,
        component_id: str = "error-display",
    ) -> "ErrorDisplayComponent":
        """Factory method for creating error display."""
        props = ErrorDisplayProps(
            id=component_id,
            plan=plan,
            timezone=timezone,
            custom_error_message=custom_error_message,
        )
        return cls(props)

    # Legacy method for backward compatibility
    def format_error_screen(
        self, plan: str = "pro", timezone: str = "Europe/Warsaw"
    ) -> List[str]:
        """Legacy method for backward compatibility."""
        screen_buffer = []

        header_manager = HeaderManager()
        screen_buffer.extend(header_manager.create_header(plan, timezone))

        screen_buffer.append("[error]Failed to get usage data[/]")
        screen_buffer.append("")
        screen_buffer.append("[warning]Possible causes:[/]")
        screen_buffer.append("  • You're not logged into Claude")
        screen_buffer.append("  • Network connection issues")
        screen_buffer.append("")
        screen_buffer.append("[dim]Retrying in 3 seconds... (Ctrl+C to exit)[/]")

        return screen_buffer


@dataclass(frozen=True)
class LoadingScreenState:
    """Immutable state for loading screen component."""

    loading_stage: str = "initializing"
    progress_percentage: float = 0.0
    estimated_completion: Optional[str] = None


@dataclass(frozen=True)
class LoadingScreenProps:
    """Immutable props for loading screen component."""

    id: str
    plan: str = "pro"
    timezone: str = "Europe/Warsaw"
    custom_message: Optional[str] = None
    show_progress: bool = False
    show_spinner: bool = True
    css_classes: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    theme_variant: Optional[str] = None


class LoadingScreenComponent(
    BaseComponent[LoadingScreenProps], Stateful[LoadingScreenState]
):
    """Advanced loading screen component with state management.

    Features:
    - Dynamic loading stages with progress tracking
    - Customizable loading messages and spinners
    - Rich text formatting with animated elements
    """

    def __init__(self, props: LoadingScreenProps) -> None:
        """Initialize loading screen component with props."""
        super().__init__(props)
        self._loading_state = LoadingScreenState()

    def get_state(self) -> LoadingScreenState:
        """Get current immutable loading state."""
        return self._loading_state

    def update_state(
        self, updater: Callable[[LoadingScreenState], LoadingScreenState]
    ) -> None:
        """Update loading state with pure function."""
        self._loading_state = updater(self._loading_state)
        self._invalidate_cache()

    def _render_impl(self, context: RenderContext) -> RenderableType:
        """Render loading screen with Rich formatting."""
        from rich.console import Group

        header_manager = HeaderManager()
        header_lines = header_manager.create_header(
            self.props.plan, self.props.timezone
        )

        content_lines = []
        content_lines.append(Text(""))

        # Loading indicator
        if self.props.show_spinner:
            content_lines.append(Text("⏳ Loading...", style="info"))
        else:
            content_lines.append(Text("Loading...", style="info"))

        content_lines.append(Text(""))

        # Custom or default message
        if self.props.custom_message:
            content_lines.append(Text(self.props.custom_message, style="warning"))
        else:
            content_lines.append(Text("Fetching Claude usage data...", style="warning"))

        content_lines.append(Text(""))

        # Plan-specific messages
        if self.props.plan == "custom" and not self.props.custom_message:
            content_lines.append(
                Text(
                    "Calculating your P90 session limits from usage history...",
                    style="info",
                )
            )
            content_lines.append(Text(""))

        content_lines.append(Text("This may take a few seconds", style="dim"))

        # Convert header lines to Text objects
        header_texts = [Text.from_markup(line) for line in header_lines]

        return Group(*header_texts, *content_lines)

    @classmethod
    def create(
        cls,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        custom_message: Optional[str] = None,
        component_id: str = "loading-screen",
    ) -> "LoadingScreenComponent":
        """Factory method for creating loading screen."""
        props = LoadingScreenProps(
            id=component_id, plan=plan, timezone=timezone, custom_message=custom_message
        )
        return cls(props)

    # Legacy methods for backward compatibility
    def create_loading_screen(
        self,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        custom_message: Optional[str] = None,
    ) -> List[str]:
        """Legacy method for backward compatibility."""
        screen_buffer = []

        header_manager = HeaderManager()
        screen_buffer.extend(header_manager.create_header(plan, timezone))

        screen_buffer.append("")
        screen_buffer.append("[info]⏳ Loading...[/]")
        screen_buffer.append("")

        if custom_message:
            screen_buffer.append(f"[warning]{custom_message}[/]")
        else:
            screen_buffer.append("[warning]Fetching Claude usage data...[/]")

        screen_buffer.append("")

        if plan == "custom" and not custom_message:
            screen_buffer.append(
                "[info]Calculating your P90 session limits from usage history...[/]"
            )
            screen_buffer.append("")

        screen_buffer.append("[dim]This may take a few seconds[/]")

        return screen_buffer

    def create_loading_screen_renderable(
        self,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        custom_message: Optional[str] = None,
    ) -> Any:
        """Legacy method for backward compatibility."""
        screen_buffer = self.create_loading_screen(plan, timezone, custom_message)

        from claude_monitor.ui.display_controller import ScreenBufferManager

        buffer_manager = ScreenBufferManager()
        return buffer_manager.create_screen_renderable(screen_buffer)


@dataclass(frozen=True)
class SessionAnalysisState:
    """Immutable state for session analysis."""

    all_sessions: List[Dict[str, Any]] = field(default_factory=list)
    limit_sessions: List[Dict[str, Any]] = field(default_factory=list)
    current_session: Dict[str, Any] = field(default_factory=dict)
    percentiles_cache: Optional[Dict[str, Any]] = None
    last_analysis_timestamp: Optional[str] = None


@dataclass(frozen=True)
class AdvancedCustomLimitProps:
    """Immutable props for advanced custom limit display."""

    id: str
    blocks: Optional[List[Dict[str, Any]]] = None
    console: Optional[Console] = None
    show_detailed_analysis: bool = True
    cache_results: bool = True
    css_classes: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    theme_variant: Optional[str] = None


class AdvancedCustomLimitDisplay(
    BaseComponent[AdvancedCustomLimitProps], Stateful[SessionAnalysisState]
):
    """Advanced session analysis component with sophisticated caching.

    Features:
    - Immutable state management for session data
    - Intelligent caching of expensive calculations
    - Type-safe session analysis with percentile calculations
    """

    def __init__(self, props: AdvancedCustomLimitProps) -> None:
        """Initialize advanced custom limit display."""
        super().__init__(props)
        self._analysis_state = SessionAnalysisState()

    def get_state(self) -> SessionAnalysisState:
        """Get current immutable analysis state."""
        return self._analysis_state

    def update_state(
        self, updater: Callable[[SessionAnalysisState], SessionAnalysisState]
    ) -> None:
        """Update analysis state with pure function."""
        self._analysis_state = updater(self._analysis_state)
        self._invalidate_cache()

    def _render_impl(self, context: RenderContext) -> RenderableType:
        """Render advanced session analysis."""
        session_data = self._collect_session_data(self.props.blocks)
        percentiles = self._calculate_session_percentiles(
            session_data["limit_sessions"]
        )

        from rich.table import Table

        if not self.props.show_detailed_analysis:
            return Text(f"P90 Analysis: {len(session_data['limit_sessions'])} sessions")

        # Create detailed analysis table
        table = Table(title="Session Analysis")
        table.add_column("Metric", style="cyan")
        table.add_column("P50", style="green")
        table.add_column("P75", style="yellow")
        table.add_column("P90", style="red")

        table.add_row(
            "Tokens",
            str(percentiles["tokens"]["p50"]),
            str(percentiles["tokens"]["p75"]),
            str(percentiles["tokens"]["p90"]),
        )

        table.add_row(
            "Cost ($)",
            f"{percentiles['costs']['p50']:.2f}",
            f"{percentiles['costs']['p75']:.2f}",
            f"{percentiles['costs']['p90']:.2f}",
        )

        return table

    @classmethod
    def create(
        cls,
        console: Optional[Console] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        component_id: str = "advanced-custom-limit",
    ) -> "AdvancedCustomLimitDisplay":
        """Factory method for creating advanced custom limit display."""
        props = AdvancedCustomLimitProps(
            id=component_id, console=console, blocks=blocks
        )
        return cls(props)

    def _collect_session_data(
        self, blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Collect session data and identify limit sessions."""
        if not blocks:
            return {
                "all_sessions": [],
                "limit_sessions": [],
                "current_session": {"tokens": 0, "cost": 0.0, "messages": 0},
                "total_sessions": 0,
                "active_sessions": 0,
            }

        all_sessions = []
        limit_sessions = []
        current_session = {"tokens": 0, "cost": 0.0, "messages": 0}
        active_sessions = 0

        for block in blocks:
            if block.get("isGap", False):
                continue

            session = {
                "tokens": block.get("totalTokens", 0),
                "cost": block.get("costUSD", 0.0),
                "messages": block.get("sentMessagesCount", 0),
            }

            if block.get("isActive", False):
                active_sessions += 1
                current_session = session
            elif session["tokens"] > 0:
                all_sessions.append(session)

                if self._is_limit_session(session):
                    limit_sessions.append(session)

        return {
            "all_sessions": all_sessions,
            "limit_sessions": limit_sessions,
            "current_session": current_session,
            "total_sessions": len(all_sessions) + active_sessions,
            "active_sessions": active_sessions,
        }

    def _is_limit_session(self, session: Dict[str, Any]) -> bool:
        """Check if session hit a general limit."""
        tokens = session["tokens"]

        from claude_monitor.core.plans import (
            COMMON_TOKEN_LIMITS,
            LIMIT_DETECTION_THRESHOLD,
        )

        for limit in COMMON_TOKEN_LIMITS:
            if tokens >= limit * LIMIT_DETECTION_THRESHOLD:
                return True

        return False

    def _calculate_session_percentiles(
        self, sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate percentiles from session data."""
        if not sessions:
            return {
                "tokens": {"p50": 44000, "p75": 66000, "p90": 88000, "p95": 110000},
                "costs": {"p50": 100.0, "p75": 150.0, "p90": 200.0, "p95": 250.0},
                "messages": {"p50": 150, "p75": 200, "p90": 250, "p95": 300},
                "averages": {"tokens": 44000, "cost": 100.0, "messages": 150},
                "count": 0,
            }

        import numpy as np

        tokens = [s["tokens"] for s in sessions]
        costs = [s["cost"] for s in sessions]
        messages = [s["messages"] for s in sessions]

        # Import datetime for timestamp
        from datetime import datetime

        result = {
            "tokens": {
                "p50": int(np.percentile(tokens, 50)),
                "p75": int(np.percentile(tokens, 75)),
                "p90": int(np.percentile(tokens, 90)),
                "p95": int(np.percentile(tokens, 95)),
            },
            "costs": {
                "p50": float(np.percentile(costs, 50)),
                "p75": float(np.percentile(costs, 75)),
                "p90": float(np.percentile(costs, 90)),
                "p95": float(np.percentile(costs, 95)),
            },
            "messages": {
                "p50": int(np.percentile(messages, 50)),
                "p75": int(np.percentile(messages, 75)),
                "p90": int(np.percentile(messages, 90)),
                "p95": int(np.percentile(messages, 95)),
            },
            "averages": {
                "tokens": float(np.mean(tokens)),
                "cost": float(np.mean(costs)),
                "messages": float(np.mean(messages)),
            },
            "count": len(sessions),
        }

        # Cache percentiles if enabled
        if self.props.cache_results:

            def update_percentiles(state: SessionAnalysisState) -> SessionAnalysisState:
                return SessionAnalysisState(
                    all_sessions=state.all_sessions,
                    limit_sessions=state.limit_sessions,
                    current_session=state.current_session,
                    percentiles_cache=result,
                    last_analysis_timestamp=str(datetime.now()),
                )

            self.update_state(update_percentiles)

        return result


# Advanced Component Composition System


class ComponentRegistry:
    """Registry for managing component instances and dependencies."""

    def __init__(self) -> None:
        self._components: Dict[str, BaseComponent[Any]] = {}
        self._factories: Dict[str, Callable[..., BaseComponent[Any]]] = {}

    def register_factory(
        self, component_type: str, factory: Callable[..., BaseComponent[Any]]
    ) -> None:
        """Register a component factory."""
        self._factories[component_type] = factory

    def create_component(
        self, component_type: str, component_id: str, **kwargs: Any
    ) -> BaseComponent[Any]:
        """Create and register a component instance."""
        if component_type not in self._factories:
            raise ValueError(f"Unknown component type: {component_type}")

        factory = self._factories[component_type]
        component = factory(component_id=component_id, **kwargs)
        self._components[component_id] = component
        return component

    def get_component(self, component_id: str) -> Optional[BaseComponent[Any]]:
        """Get component by ID."""
        return self._components.get(component_id)

    def remove_component(self, component_id: str) -> None:
        """Remove and cleanup component."""
        if component_id in self._components:
            component = self._components[component_id]
            component.unmount()
            del self._components[component_id]


class ComponentComposer:
    """Advanced component composition with dependency injection."""

    def __init__(self, registry: ComponentRegistry) -> None:
        self._registry = registry
        self._render_pipeline: List[Callable[[RenderableType], RenderableType]] = []

    def add_render_middleware(
        self, middleware: Callable[[RenderableType], RenderableType]
    ) -> None:
        """Add middleware to render pipeline."""
        self._render_pipeline.append(middleware)

    def compose_components(
        self, component_specs: List[Dict[str, Any]], context: RenderContext
    ) -> RenderableType:
        """Compose multiple components into unified display."""
        from rich.console import Group

        rendered_components = []

        for spec in component_specs:
            component_id = spec.get("id")
            if not component_id:
                continue

            component = self._registry.get_component(component_id)
            if component is None:
                # Try to create component from spec
                component_type = spec.get("type")
                if component_type:
                    try:
                        component = self._registry.create_component(
                            component_type, component_id, **spec.get("props", {})
                        )
                    except (ValueError, TypeError):
                        continue
                else:
                    continue

            try:
                rendered = component.render(context)

                # Apply render pipeline middleware
                for middleware in self._render_pipeline:
                    rendered = middleware(rendered)

                rendered_components.append(rendered)
            except Exception:
                # Skip failed components gracefully
                continue

        return Group(*rendered_components)


# Global component registry instance
_component_registry = ComponentRegistry()


# Helper function to cast factory types
def _cast_factory(factory: Any) -> Callable[..., BaseComponent[Any]]:
    """Cast factory function to proper type."""
    return factory  # type: ignore[no-any-return]


# Register component factories
_component_registry.register_factory(
    "velocity_indicator", _cast_factory(VelocityIndicator.create)
)
_component_registry.register_factory(
    "cost_indicator", _cast_factory(CostIndicator.create)
)
_component_registry.register_factory(
    "error_display", _cast_factory(ErrorDisplayComponent.create)
)
_component_registry.register_factory(
    "loading_screen", _cast_factory(LoadingScreenComponent.create)
)
_component_registry.register_factory(
    "advanced_custom_limit", _cast_factory(AdvancedCustomLimitDisplay.create)
)


def get_component_registry() -> ComponentRegistry:
    """Get global component registry."""
    return _component_registry


def create_component_composer() -> ComponentComposer:
    """Create new component composer with global registry."""
    return ComponentComposer(_component_registry)


# Store original component classes before creating compatibility wrappers
_OriginalErrorDisplayComponent = ErrorDisplayComponent
_OriginalLoadingScreenComponent = LoadingScreenComponent
_OriginalAdvancedCustomLimitDisplay = AdvancedCustomLimitDisplay


# Compatibility Components for Display Controller
class CompatibilityErrorDisplayComponent:
    """Compatibility wrapper that maintains old constructor signature."""

    def __init__(self) -> None:
        """Initialize with default props."""
        self._default_props = ErrorDisplayProps(
            id="compat-error", plan="pro", timezone="Europe/Warsaw"
        )
        self._component = _OriginalErrorDisplayComponent(self._default_props)

    def format_error_screen(
        self, plan: str = "pro", timezone: str = "Europe/Warsaw"
    ) -> List[str]:
        """Format error screen with backward compatibility."""
        return self._component.format_error_screen(plan, timezone)


class CompatibilityLoadingScreenComponent:
    """Compatibility wrapper that maintains old constructor signature."""

    def __init__(self) -> None:
        """Initialize with default props."""
        self._default_props = LoadingScreenProps(
            id="compat-loading", plan="pro", timezone="Europe/Warsaw"
        )
        self._component = _OriginalLoadingScreenComponent(self._default_props)

    def create_loading_screen(
        self,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        custom_message: Optional[str] = None,
    ) -> List[str]:
        """Create loading screen with backward compatibility."""
        return self._component.create_loading_screen(plan, timezone, custom_message)

    def create_loading_screen_renderable(
        self,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        custom_message: Optional[str] = None,
    ) -> Any:
        """Create loading screen renderable with backward compatibility."""
        return self._component.create_loading_screen_renderable(
            plan, timezone, custom_message
        )


class CompatibilityAdvancedCustomLimitDisplay:
    """Compatibility wrapper that maintains old constructor signature."""

    def __init__(self, console: Optional[Console]) -> None:
        """Initialize with console parameter for backward compatibility."""
        self._default_props = AdvancedCustomLimitProps(
            id="compat-advanced", console=console
        )
        self._component = _OriginalAdvancedCustomLimitDisplay(self._default_props)

    def _collect_session_data(
        self, blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Collect session data with backward compatibility."""
        return self._component._collect_session_data(blocks)

    def _calculate_session_percentiles(
        self, sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate session percentiles with backward compatibility."""
        return self._component._calculate_session_percentiles(sessions)

    def _is_limit_session(self, session: Dict[str, Any]) -> bool:
        """Check if session is limit session with backward compatibility."""
        return self._component._is_limit_session(session)


# Legacy functions for backward compatibility
def format_error_screen(
    plan: str = "pro", timezone: str = "Europe/Warsaw"
) -> List[str]:
    """Legacy function - format error screen.

    Maintained for backward compatibility.
    """
    props = ErrorDisplayProps(id="legacy-error", plan=plan, timezone=timezone)
    component = _OriginalErrorDisplayComponent(props)
    return component.format_error_screen(plan, timezone)


# Legacy render functions that maintain old API
class LegacyComponentAPI:
    """Legacy API wrapper for backward compatibility."""

    @staticmethod
    def render_velocity_indicator(
        burn_rate: float, include_description: bool = False
    ) -> str:
        """Legacy velocity indicator render."""
        return VelocityIndicator.render_legacy(burn_rate, include_description)

    @staticmethod
    def render_cost_indicator(cost: float, currency: str = "USD") -> str:
        """Legacy cost indicator render."""
        return CostIndicator.render_legacy(cost, currency)


# Replace with compatibility versions for existing code
ErrorDisplayComponent = CompatibilityErrorDisplayComponent  # type: ignore[misc,assignment]
LoadingScreenComponent = CompatibilityLoadingScreenComponent  # type: ignore[misc,assignment]
AdvancedCustomLimitDisplay = CompatibilityAdvancedCustomLimitDisplay  # type: ignore[misc,assignment]


# Preserve old function names for backward compatibility
def velocity_indicator_render(
    burn_rate: float, include_description: bool = False
) -> str:
    """Legacy velocity indicator function."""
    return LegacyComponentAPI.render_velocity_indicator(burn_rate, include_description)


def cost_indicator_render(cost: float, currency: str = "USD") -> str:
    """Legacy cost indicator function."""
    return LegacyComponentAPI.render_cost_indicator(cost, currency)
