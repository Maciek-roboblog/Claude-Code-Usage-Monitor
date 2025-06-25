"""Theme detection logic for automatic light/dark theme selection."""

import os
import sys
import subprocess
from typing import Optional
from .themes import ThemeType


class ThemeDetector:
    """Detects appropriate theme based on terminal environment."""
    
    def __init__(self):
        self._cached_theme: Optional[ThemeType] = None
    
    def detect_theme(self, force_detection: bool = False) -> ThemeType:
        """Detect the appropriate theme for the current terminal.
        
        Args:
            force_detection: Force re-detection even if cached
            
        Returns:
            ThemeType enum value
        """
        if self._cached_theme is not None and not force_detection:
            return self._cached_theme
            
        detected = self._detect_theme_impl()
        self._cached_theme = detected
        return detected
    
    def _detect_theme_impl(self) -> ThemeType:
        """Implementation of theme detection logic."""
        # Method 1: Check environment variables
        env_theme = self._detect_from_environment()
        if env_theme is not None:
            return env_theme
            
        # Method 2: Check terminal program
        program_theme = self._detect_from_terminal_program()
        if program_theme is not None:
            return program_theme
            
        # Method 3: Advanced terminal background detection
        bg_theme = self._detect_from_terminal_background()
        if bg_theme is not None:
            return bg_theme
            
        # Method 4: Check COLORFGBG variable
        colorfgbg_theme = self._detect_from_colorfgbg()
        if colorfgbg_theme is not None:
            return colorfgbg_theme
            
        # Method 5: Platform-specific detection
        platform_theme = self._detect_from_platform()
        if platform_theme is not None:
            return platform_theme
            
        # Default fallback - most terminals are dark
        return ThemeType.DARK
    
    def _detect_from_environment(self) -> Optional[ThemeType]:
        """Detect theme from environment variables."""
        # Check for explicit theme setting
        claude_theme = os.environ.get('CLAUDE_MONITOR_THEME', '').lower()
        if claude_theme in ('light', 'dark'):
            return ThemeType.LIGHT if claude_theme == 'light' else ThemeType.DARK
            
        # Check terminal-specific variables
        if os.environ.get('ITERM_PROFILE'):
            # iTerm2 sets this - check for common light profile names
            profile = os.environ.get('ITERM_PROFILE', '').lower()
            if any(word in profile for word in ['light', 'bright', 'white']):
                return ThemeType.LIGHT
            elif any(word in profile for word in ['dark', 'black']):
                return ThemeType.DARK
                
        return None
    
    def _detect_from_terminal_program(self) -> Optional[ThemeType]:
        """Detect theme from terminal program identification."""
        term_program = os.environ.get('TERM_PROGRAM', '').lower()
        
        # VS Code integrated terminal
        if term_program == 'vscode':
            # VS Code usually reflects the editor theme
            # Check for theme hints in environment
            if 'VSCODE_DARK' in os.environ or 'dark' in os.environ.get('COLORTERM', '').lower():
                return ThemeType.DARK
            elif 'VSCODE_LIGHT' in os.environ or 'light' in os.environ.get('COLORTERM', '').lower():
                return ThemeType.LIGHT
                
        # Windows Terminal
        elif 'windowsterminal' in term_program:
            # Default to dark for Windows Terminal
            return ThemeType.DARK
            
        return None
    
    def _detect_from_colorfgbg(self) -> Optional[ThemeType]:
        """Detect theme from COLORFGBG environment variable."""
        colorfgbg = os.environ.get('COLORFGBG', '')
        if not colorfgbg:
            return None
            
        try:
            # COLORFGBG format: "foreground;background"
            if ';' in colorfgbg:
                fg, bg = colorfgbg.split(';', 1)
                bg_num = int(bg)
                
                # Background colors 0-7 are typically dark
                # Background colors 8-15 are typically light
                if bg_num <= 7:
                    return ThemeType.DARK
                else:
                    return ThemeType.LIGHT
        except (ValueError, IndexError):
            pass
            
        return None
    
    def _detect_from_terminal_background(self) -> Optional[ThemeType]:
        """Advanced terminal background color detection using escape sequences."""
        if not sys.stdout.isatty():
            return None
            
        try:
            # Query terminal background color using OSC 11
            # This is a more advanced method but may not work in all terminals
            import termios
            import tty
            import select
            
            # Save current terminal settings
            old_settings = termios.tcgetattr(sys.stdin)
            
            try:
                # Set terminal to raw mode
                tty.setraw(sys.stdin.fileno())
                
                # Send OSC 11 query (query background color)
                sys.stdout.write('\033]11;?\033\\')
                sys.stdout.flush()
                
                # Wait for response with timeout
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    response = ''
                    while True:
                        if select.select([sys.stdin], [], [], 0.05)[0]:
                            char = sys.stdin.read(1)
                            response += char
                            # Look for end of OSC response
                            if char == '\\' and response.endswith('\033\\'):
                                break
                            if len(response) > 50:  # Prevent infinite loop
                                break
                        else:
                            break
                    
                    # Parse response: \033]11;rgb:RRRR/GGGG/BBBB\033\
                    if 'rgb:' in response:
                        try:
                            rgb_part = response.split('rgb:')[1].split('\033')[0]
                            r, g, b = rgb_part.split('/')
                            # Convert hex to decimal
                            r_val = int(r[:2], 16) if len(r) >= 2 else 0
                            g_val = int(g[:2], 16) if len(g) >= 2 else 0  
                            b_val = int(b[:2], 16) if len(b) >= 2 else 0
                            
                            # Calculate luminance
                            luminance = (0.299 * r_val + 0.587 * g_val + 0.114 * b_val) / 255
                            
                            # Threshold: > 0.5 is light, <= 0.5 is dark
                            return ThemeType.LIGHT if luminance > 0.5 else ThemeType.DARK
                            
                        except (ValueError, IndexError):
                            pass
                            
            finally:
                # Restore terminal settings
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                
        except (ImportError, OSError, termios.error):
            # termios not available or operation failed
            pass
            
        return None
    
    def _detect_terminal_capabilities(self) -> dict:
        """Detect terminal color capabilities."""
        capabilities = {
            'colors': 0,
            'truecolor': False,
            'force_color': False
        }
        
        # Check TERM environment variable
        term = os.environ.get('TERM', '')
        if '256color' in term:
            capabilities['colors'] = 256
        elif 'color' in term:
            capabilities['colors'] = 8
            
        # Check for truecolor support
        colorterm = os.environ.get('COLORTERM', '')
        if colorterm in ('truecolor', '24bit'):
            capabilities['truecolor'] = True
            capabilities['colors'] = 16777216
            
        # Check for forced color
        if os.environ.get('FORCE_COLOR') or os.environ.get('CLICOLOR_FORCE'):
            capabilities['force_color'] = True
            
        return capabilities
    
    def _detect_from_platform(self) -> Optional[ThemeType]:
        """Platform-specific theme detection."""
        if sys.platform == 'darwin':  # macOS
            return self._detect_macos_theme()
        elif sys.platform.startswith('win'):  # Windows
            return self._detect_windows_theme()
        elif sys.platform.startswith('linux'):  # Linux
            return self._detect_linux_theme()
            
        return None
    
    def _detect_macos_theme(self) -> Optional[ThemeType]:
        """Detect macOS system theme."""
        try:
            # Check system appearance
            result = subprocess.run([
                'defaults', 'read', '-g', 'AppleInterfaceStyle'
            ], capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0 and 'dark' in result.stdout.lower():
                return ThemeType.DARK
            else:
                # No dark mode setting found = light mode
                return ThemeType.LIGHT
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
            
        return None
    
    def _detect_windows_theme(self) -> Optional[ThemeType]:
        """Detect Windows system theme."""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                return ThemeType.LIGHT if value == 1 else ThemeType.DARK
        except (ImportError, OSError, FileNotFoundError):
            pass
            
        return None
    
    def _detect_linux_theme(self) -> Optional[ThemeType]:
        """Detect Linux desktop theme."""
        # Check GNOME theme
        if os.environ.get('XDG_CURRENT_DESKTOP', '').lower() == 'gnome':
            try:
                result = subprocess.run([
                    'gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'
                ], capture_output=True, text=True, timeout=2)
                
                if result.returncode == 0:
                    theme = result.stdout.strip().lower()
                    if 'dark' in theme:
                        return ThemeType.DARK
                    elif 'light' in theme:
                        return ThemeType.LIGHT
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass
        
        return None
    
    def get_debug_info(self) -> dict:
        """Get debug information about theme detection."""
        return {
            'detected_theme': self.detect_theme().value,
            'environment_vars': {
                'CLAUDE_MONITOR_THEME': os.environ.get('CLAUDE_MONITOR_THEME'),
                'TERM_PROGRAM': os.environ.get('TERM_PROGRAM'),
                'ITERM_PROFILE': os.environ.get('ITERM_PROFILE'), 
                'COLORFGBG': os.environ.get('COLORFGBG'),
                'COLORTERM': os.environ.get('COLORTERM'),
                'XDG_CURRENT_DESKTOP': os.environ.get('XDG_CURRENT_DESKTOP'),
                'TERM': os.environ.get('TERM'),
                'FORCE_COLOR': os.environ.get('FORCE_COLOR'),
                'CLICOLOR_FORCE': os.environ.get('CLICOLOR_FORCE'),
            },
            'platform': sys.platform,
            'terminal_capabilities': self._detect_terminal_capabilities(),
            'is_tty': sys.stdout.isatty(),
            'detection_methods': [
                'environment_vars',
                'terminal_program',
                'terminal_background',
                'colorfgbg',
                'platform_specific'
            ]
        }