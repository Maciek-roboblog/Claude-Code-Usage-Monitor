"""Advanced UI layout management system for Claude Monitor.

This module provides sophisticated layout management functionality including:
- Responsive layout composition systems
- Dynamic component positioning algorithms
- Rich integration with advanced layout patterns
- Flexible screen management and organization
- Type-safe layout composition and updates
"""

from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    Union,
    runtime_checkable,
)

try:
    from rich.align import Align
    from rich.console import Console, RenderableType
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:
    # Fallback types for systems without Rich
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from rich.align import Align
        from rich.console import Console, RenderableType
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    else:
        # Runtime fallbacks
        Console = type("Console", (), {})
        RenderableType = Any
        Layout = type("Layout", (), {})
        Panel = type("Panel", (), {})
        Table = type("Table", (), {})
        Text = type("Text", (), {})
        Align = type("Align", (), {})


class LayoutAlignment(Enum):
    """Layout alignment options."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class ResponsiveBreakpoint(Enum):
    """Responsive design breakpoints."""

    MOBILE = 40
    TABLET = 80
    DESKTOP = 120
    WIDE = 160


class LayoutMode(Enum):
    """Layout rendering modes."""

    STATIC = "static"
    DYNAMIC = "dynamic"
    RESPONSIVE = "responsive"
    ADAPTIVE = "adaptive"


@dataclass(frozen=True)
class LayoutConstraints:
    """Layout constraints for component positioning."""

    min_width: int = 0
    max_width: Optional[int] = None
    min_height: int = 0
    max_height: Optional[int] = None
    aspect_ratio: Optional[float] = None
    padding: Tuple[int, int, int, int] = (0, 0, 0, 0)  # top, right, bottom, left
    margin: Tuple[int, int, int, int] = (0, 0, 0, 0)  # top, right, bottom, left


@dataclass
class LayoutDimensions:
    """Layout dimensions and positioning information."""

    width: int
    height: int
    x: int = 0
    y: int = 0

    @property
    def area(self) -> int:
        """Calculate layout area."""
        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio."""
        return self.width / self.height if self.height > 0 else 0.0


class LayoutPosition(NamedTuple):
    """Precise layout positioning."""

    x: int
    y: int
    z_index: int = 0


@runtime_checkable
class LayoutComponent(Protocol):
    """Protocol for layout-aware components."""

    def render(
        self, dimensions: LayoutDimensions, console: Console
    ) -> Union[RenderableType, str]:
        """Render component with given dimensions."""
        ...

    def get_preferred_size(self, available: LayoutDimensions) -> LayoutDimensions:
        """Get preferred size for this component."""
        ...

    def can_resize(self) -> bool:
        """Check if component supports resizing."""
        ...


@runtime_checkable
class ResponsiveComponent(Protocol):
    """Protocol for responsive layout components."""

    def adapt_to_breakpoint(self, breakpoint: ResponsiveBreakpoint) -> None:
        """Adapt component to responsive breakpoint."""
        ...

    def get_breakpoint_constraints(
        self, breakpoint: ResponsiveBreakpoint
    ) -> LayoutConstraints:
        """Get layout constraints for specific breakpoint."""
        ...


class LayoutCalculator:
    """Advanced layout calculation algorithms."""

    @staticmethod
    def calculate_flexbox_layout(
        container: LayoutDimensions,
        components: List[LayoutComponent],
        direction: str = "row",
        justify: str = "start",
        align: str = "stretch",
    ) -> List[LayoutDimensions]:
        """Calculate flexbox-style layout for components."""
        if not components:
            return []

        if direction == "row":
            return LayoutCalculator._calculate_row_layout(
                container, components, justify, align
            )
        else:
            return LayoutCalculator._calculate_column_layout(
                container, components, justify, align
            )

    @staticmethod
    def _calculate_row_layout(
        container: LayoutDimensions,
        components: List[LayoutComponent],
        justify: str,
        align: str,
    ) -> List[LayoutDimensions]:
        """Calculate row-based layout."""
        component_width = container.width // len(components)
        layouts = []

        for i, component in enumerate(components):
            x_offset = i * component_width
            if justify == "center":
                x_offset += (container.width - len(components) * component_width) // 2
            elif justify == "end":
                x_offset += container.width - len(components) * component_width

            height = container.height
            y_offset = 0
            if align == "center":
                preferred = component.get_preferred_size(container)
                height = min(preferred.height, container.height)
                y_offset = (container.height - height) // 2

            layouts.append(
                LayoutDimensions(
                    width=component_width, height=height, x=x_offset, y=y_offset
                )
            )

        return layouts

    @staticmethod
    def _calculate_column_layout(
        container: LayoutDimensions,
        components: List[LayoutComponent],
        justify: str,
        align: str,
    ) -> List[LayoutDimensions]:
        """Calculate column-based layout."""
        component_height = container.height // len(components)
        layouts = []

        for i, component in enumerate(components):
            y_offset = i * component_height
            if justify == "center":
                y_offset += (container.height - len(components) * component_height) // 2
            elif justify == "end":
                y_offset += container.height - len(components) * component_height

            width = container.width
            x_offset = 0
            if align == "center":
                preferred = component.get_preferred_size(container)
                width = min(preferred.width, container.width)
                x_offset = (container.width - width) // 2

            layouts.append(
                LayoutDimensions(
                    width=width, height=component_height, x=x_offset, y=y_offset
                )
            )

        return layouts

    @staticmethod
    def calculate_grid_layout(
        container: LayoutDimensions, rows: int, cols: int, gap: int = 0
    ) -> List[List[LayoutDimensions]]:
        """Calculate grid-based layout."""
        available_width = container.width - (cols - 1) * gap
        available_height = container.height - (rows - 1) * gap

        cell_width = available_width // cols
        cell_height = available_height // rows

        grid = []
        for row in range(rows):
            row_layouts = []
            for col in range(cols):
                x = col * (cell_width + gap)
                y = row * (cell_height + gap)
                row_layouts.append(
                    LayoutDimensions(width=cell_width, height=cell_height, x=x, y=y)
                )
            grid.append(row_layouts)

        return grid


class ResponsiveLayoutManager:
    """Advanced responsive layout management."""

    def __init__(self) -> None:
        """Initialize responsive layout manager."""
        self._breakpoints: Dict[ResponsiveBreakpoint, LayoutConstraints] = {}
        self._current_breakpoint: Optional[ResponsiveBreakpoint] = None
        self._components: List[Union[LayoutComponent, ResponsiveComponent]] = []

    def add_breakpoint(
        self, breakpoint: ResponsiveBreakpoint, constraints: LayoutConstraints
    ) -> None:
        """Add responsive breakpoint with constraints."""
        self._breakpoints[breakpoint] = constraints

    def register_component(
        self, component: Union[LayoutComponent, ResponsiveComponent]
    ) -> None:
        """Register component for responsive management."""
        self._components.append(component)

    def update_viewport(self, width: int, height: int) -> ResponsiveBreakpoint:
        """Update viewport and determine current breakpoint."""
        # Determine breakpoint based on width
        if width <= ResponsiveBreakpoint.MOBILE.value:
            breakpoint = ResponsiveBreakpoint.MOBILE
        elif width <= ResponsiveBreakpoint.TABLET.value:
            breakpoint = ResponsiveBreakpoint.TABLET
        elif width <= ResponsiveBreakpoint.DESKTOP.value:
            breakpoint = ResponsiveBreakpoint.DESKTOP
        else:
            breakpoint = ResponsiveBreakpoint.WIDE

        if breakpoint != self._current_breakpoint:
            self._current_breakpoint = breakpoint
            self._adapt_components_to_breakpoint(breakpoint)

        return breakpoint

    def _adapt_components_to_breakpoint(self, breakpoint: ResponsiveBreakpoint) -> None:
        """Adapt all responsive components to new breakpoint."""
        for component in self._components:
            if isinstance(component, ResponsiveComponent):
                component.adapt_to_breakpoint(breakpoint)

    def get_current_constraints(self) -> Optional[LayoutConstraints]:
        """Get constraints for current breakpoint."""
        if self._current_breakpoint:
            return self._breakpoints.get(self._current_breakpoint)
        return None


class HeaderManager(LayoutComponent):
    """Advanced header layout manager with responsive design."""

    def __init__(
        self,
        separator_char: str = "=",
        separator_length: int = 60,
        alignment: LayoutAlignment = LayoutAlignment.CENTER,
    ) -> None:
        """Initialize header manager.

        Args:
            separator_char: Character for separators
            separator_length: Default separator length
            alignment: Header text alignment
        """
        self.separator_char = separator_char
        self.separator_length = separator_length
        self.alignment = alignment
        self._cached_header: Optional[Union[Panel, str]] = None
        self._last_dimensions: Optional[LayoutDimensions] = None

    def render(
        self, dimensions: LayoutDimensions, console: Console
    ) -> Union[RenderableType, str]:
        """Render header with given dimensions.

        Args:
            dimensions: Available layout dimensions
            console: Rich console for rendering

        Returns:
            Rendered header as Rich Panel or fallback string
        """
        # Use caching for performance
        if self._cached_header is None or self._last_dimensions != dimensions:
            self._cached_header = self._create_responsive_header(dimensions)
            self._last_dimensions = dimensions

        return self._cached_header if self._cached_header is not None else ""

    def get_preferred_size(self, available: LayoutDimensions) -> LayoutDimensions:
        """Get preferred size for header.

        Args:
            available: Available dimensions

        Returns:
            Preferred header dimensions
        """
        # Header prefers full width, minimal height
        return LayoutDimensions(
            width=available.width,
            height=min(6, available.height),  # Header needs ~6 lines
            x=0,
            y=0,
        )

    def can_resize(self) -> bool:
        """Check if header supports resizing.

        Returns:
            True - header is resizable
        """
        return True

    def _create_responsive_header(
        self, dimensions: LayoutDimensions
    ) -> Union[Panel, str]:
        """Create responsive header based on available dimensions.

        Args:
            dimensions: Available layout dimensions

        Returns:
            Responsive header panel
        """
        # Adapt separator length to available width
        effective_separator_length = min(
            self.separator_length,
            max(20, dimensions.width - 4),  # Account for panel borders
        )

        # Choose sparkles based on available width
        if dimensions.width >= 80:
            sparkles = "✦ ✧ ✦ ✧"
        elif dimensions.width >= 60:
            sparkles = "✦ ✧"
        else:
            sparkles = "✦"

        title = "CLAUDE CODE USAGE MONITOR"

        # Adapt title for narrow screens
        if dimensions.width < 50:
            title = "CLAUDE MONITOR"
        elif dimensions.width < 40:
            title = "MONITOR"

        header_content = self._build_header_content(
            sparkles, title, effective_separator_length
        )

        try:
            return Panel(
                header_content,
                style="bold blue",
                border_style="bright_blue",
                padding=(0, 1),
                expand=False,
                width=dimensions.width,
            )
        except Exception:
            # Fallback for systems without Rich
            return str(header_content)

    def _build_header_content(
        self, sparkles: str, title: str, sep_length: int
    ) -> Union[Text, str]:
        """Build header content with proper alignment.

        Args:
            sparkles: Sparkle decorations
            title: Header title
            sep_length: Separator length

        Returns:
            Formatted header text
        """
        separator = self.separator_char * sep_length

        # Create header text with alignment
        try:
            header_text = Text()

            # Title line with sparkles
            title_line = f"{sparkles} {title} {sparkles}"
            header_text.append(title_line, style="header")
            header_text.append("\n")

            # Separator line
            header_text.append(separator, style="table.border")

            # Apply alignment
            if self.alignment == LayoutAlignment.CENTER:
                header_text.justify = "center"
            elif self.alignment == LayoutAlignment.RIGHT:
                header_text.justify = "right"
            else:
                header_text.justify = "left"

            return header_text
        except Exception:
            # Fallback to simple string if Rich is not available
            title_line = f"{sparkles} {title} {sparkles}"
            return f"{title_line}\n{separator}"

    def create_header(
        self, plan: str = "pro", timezone: str = "Europe/Warsaw"
    ) -> List[str]:
        """Create stylized header with sparkles (legacy method).

        Args:
            plan: Current plan name
            timezone: Display timezone

        Returns:
            List of formatted header lines
        """
        sparkles = "✦ ✧ ✦ ✧"
        title = "CLAUDE CODE USAGE MONITOR"
        separator = self.separator_char * self.separator_length

        return [
            f"[header]{sparkles}[/] [header]{title}[/] [header]{sparkles}[/]",
            f"[table.border]{separator}[/]",
            f"[ {plan.lower()} | {timezone.lower()} ]",
            "",
        ]


class ScreenManager:
    """Advanced screen layout manager with dynamic composition."""

    def __init__(
        self,
        console: Optional[Console] = None,
        mode: LayoutMode = LayoutMode.RESPONSIVE,
    ) -> None:
        """Initialize screen manager.

        Args:
            console: Rich console instance
            mode: Layout rendering mode
        """
        self.console = console or Console()
        self.mode = mode
        self.screen_width = 80
        self.screen_height = 24
        self.margin_left = 0
        self.margin_right = 0
        self.margin_top = 0
        self.margin_bottom = 0

        # Advanced layout management
        self._layout_cache: Dict[str, Layout] = {}
        self._component_registry: Dict[str, LayoutComponent] = {}
        self._responsive_manager = ResponsiveLayoutManager()
        self._layout_tree: Optional[Layout] = None
        self._update_callbacks: List[Callable[[LayoutDimensions], None]] = []

    def set_screen_dimensions(self, width: int, height: int) -> None:
        """Set screen dimensions for layout calculations.

        Args:
            width: Screen width in characters
            height: Screen height in lines
        """
        old_width, old_height = self.screen_width, self.screen_height
        self.screen_width = width
        self.screen_height = height

        # Update responsive manager
        self._responsive_manager.update_viewport(width, height)

        # Invalidate layout cache if dimensions changed significantly
        if abs(old_width - width) > 10 or abs(old_height - height) > 5:
            self._layout_cache.clear()

        # Notify update callbacks
        current_dimensions = self.get_available_dimensions()
        for callback in self._update_callbacks:
            callback(current_dimensions)

    def set_margins(
        self, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0
    ) -> None:
        """Set screen margins.

        Args:
            left: Left margin in characters
            right: Right margin in characters
            top: Top margin in lines
            bottom: Bottom margin in lines
        """
        self.margin_left = left
        self.margin_right = right
        self.margin_top = top
        self.margin_bottom = bottom

        # Clear cache when margins change
        self._layout_cache.clear()

    def get_available_dimensions(self) -> LayoutDimensions:
        """Get available dimensions after accounting for margins.

        Returns:
            Available layout dimensions
        """
        return LayoutDimensions(
            width=max(0, self.screen_width - self.margin_left - self.margin_right),
            height=max(0, self.screen_height - self.margin_top - self.margin_bottom),
            x=self.margin_left,
            y=self.margin_top,
        )

    def register_component(self, name: str, component: LayoutComponent) -> None:
        """Register a layout component.

        Args:
            name: Component identifier
            component: Layout component to register
        """
        self._component_registry[name] = component
        self._responsive_manager.register_component(component)

    def create_adaptive_layout(
        self, components: Dict[str, LayoutComponent], layout_spec: str = "auto"
    ) -> Layout:
        """Create adaptive layout with registered components.

        Args:
            components: Components to include in layout
            layout_spec: Layout specification ("auto", "grid", "flex")

        Returns:
            Rich Layout object
        """
        cache_key = (
            f"{layout_spec}_{len(components)}_{self.screen_width}x{self.screen_height}"
        )

        if cache_key in self._layout_cache:
            return self._layout_cache[cache_key]

        available = self.get_available_dimensions()
        layout = Layout(name="root")

        if layout_spec == "grid" and len(components) > 1:
            layout = self._create_grid_layout(components, available)
        elif layout_spec == "flex":
            layout = self._create_flex_layout(components, available)
        else:
            layout = self._create_auto_layout(components, available)

        self._layout_cache[cache_key] = layout
        self._layout_tree = layout
        return layout

    def _create_grid_layout(
        self, components: Dict[str, LayoutComponent], available: LayoutDimensions
    ) -> Layout:
        """Create grid-based layout.

        Args:
            components: Components to layout
            available: Available dimensions

        Returns:
            Grid layout
        """
        layout = Layout(name="grid_root")

        # Calculate optimal grid dimensions
        component_count = len(components)
        if component_count <= 2:
            rows, cols = 1, component_count
        elif component_count <= 4:
            rows, cols = 2, 2
        else:
            rows = int(component_count**0.5)
            cols = (component_count + rows - 1) // rows

        # Create grid structure
        for row in range(rows):
            row_layout = Layout(name=f"row_{row}")
            layout.split_column(row_layout)

            row_components = list(components.items())[row * cols : (row + 1) * cols]
            for name, component in row_components:
                cell_layout = Layout(
                    component.render(
                        LayoutDimensions(
                            width=available.width // cols,
                            height=available.height // rows,
                        ),
                        self.console,
                    ),
                    name=name,
                )
                row_layout.split_row(cell_layout)

        return layout

    def _create_flex_layout(
        self, components: Dict[str, LayoutComponent], available: LayoutDimensions
    ) -> Layout:
        """Create flexible layout.

        Args:
            components: Components to layout
            available: Available dimensions

        Returns:
            Flexible layout
        """
        layout = Layout(name="flex_root")

        component_layouts = LayoutCalculator.calculate_flexbox_layout(
            available,
            list(components.values()),
            direction="column",
            justify="start",
            align="stretch",
        )

        for (name, component), dimensions in zip(components.items(), component_layouts):
            component_layout = Layout(
                component.render(dimensions, self.console),
                name=name,
                size=dimensions.height,
            )
            layout.split_column(component_layout)

        return layout

    def _create_auto_layout(
        self, components: Dict[str, LayoutComponent], available: LayoutDimensions
    ) -> Layout:
        """Create automatic layout.

        Args:
            components: Components to layout
            available: Available dimensions

        Returns:
            Automatic layout
        """
        layout = Layout(name="auto_root")

        # Simple column layout for auto mode
        for name, component in components.items():
            preferred = component.get_preferred_size(available)
            component_layout = Layout(
                component.render(preferred, self.console),
                name=name,
                size=preferred.height if preferred.height > 0 else None,
            )
            layout.split_column(component_layout)

        return layout

    def add_update_callback(self, callback: Callable[[LayoutDimensions], None]) -> None:
        """Add callback for layout updates.

        Args:
            callback: Callback function to execute on layout updates
        """
        self._update_callbacks.append(callback)

    def refresh_layout(self) -> None:
        """Force refresh of the current layout."""
        self._layout_cache.clear()
        if self._layout_tree:
            # Trigger re-rendering of current layout
            available = self.get_available_dimensions()
            for callback in self._update_callbacks:
                callback(available)

    def create_full_screen_layout(self, content_sections: List[List[str]]) -> List[str]:
        """Create full screen layout with multiple content sections (legacy method).

        Args:
            content_sections: List of content sections, each being a list of lines

        Returns:
            Combined screen layout as list of lines
        """
        screen_buffer = []

        screen_buffer.extend([""] * self.margin_top)

        for i, section in enumerate(content_sections):
            if i > 0:
                screen_buffer.append("")

            for line in section:
                padded_line = " " * self.margin_left + line
                screen_buffer.append(padded_line)

        screen_buffer.extend([""] * self.margin_bottom)

        return screen_buffer


# Layout composition utilities
class LayoutComposer:
    """Utility class for composing complex layouts."""

    @staticmethod
    def create_dashboard_layout(
        header: LayoutComponent,
        sidebar: Optional[LayoutComponent] = None,
        main_content: Optional[LayoutComponent] = None,
        footer: Optional[LayoutComponent] = None,
    ) -> Dict[str, LayoutComponent]:
        """Create dashboard-style layout composition.

        Args:
            header: Header component
            sidebar: Optional sidebar component
            main_content: Optional main content component
            footer: Optional footer component

        Returns:
            Dictionary of positioned components
        """
        layout_components: Dict[str, LayoutComponent] = {"header": header}

        if sidebar:
            layout_components["sidebar"] = sidebar
        if main_content:
            layout_components["main"] = main_content
        if footer:
            layout_components["footer"] = footer

        return layout_components

    @staticmethod
    def create_split_layout(
        left: LayoutComponent, right: LayoutComponent, split_ratio: float = 0.5
    ) -> Dict[str, LayoutComponent]:
        """Create split-pane layout.

        Args:
            left: Left pane component
            right: Right pane component
            split_ratio: Split ratio (0.0 to 1.0)

        Returns:
            Dictionary of split components
        """
        return {"left_pane": left, "right_pane": right}

    @staticmethod
    def create_tabbed_layout(
        tabs: Dict[str, LayoutComponent], active_tab: str
    ) -> Dict[str, LayoutComponent]:
        """Create tabbed layout.

        Args:
            tabs: Dictionary of tab components
            active_tab: Currently active tab

        Returns:
            Dictionary with active tab component
        """
        if active_tab in tabs:
            return {"active_content": tabs[active_tab]}

        # Return first available tab or empty dict if no tabs
        if tabs:
            first_component = list(tabs.values())[0]
            return {"active_content": first_component}

        # Create a dummy component for empty case
        class EmptyComponent:
            def render(
                self, dimensions: LayoutDimensions, console: Console
            ) -> Union[RenderableType, str]:
                return ""

            def get_preferred_size(
                self, available: LayoutDimensions
            ) -> LayoutDimensions:
                return LayoutDimensions(width=0, height=0)

            def can_resize(self) -> bool:
                return True

        return {"active_content": EmptyComponent()}


__all__ = [
    "LayoutAlignment",
    "ResponsiveBreakpoint",
    "LayoutMode",
    "LayoutConstraints",
    "LayoutDimensions",
    "LayoutPosition",
    "LayoutComponent",
    "ResponsiveComponent",
    "LayoutCalculator",
    "ResponsiveLayoutManager",
    "HeaderManager",
    "ScreenManager",
    "LayoutComposer",
]
