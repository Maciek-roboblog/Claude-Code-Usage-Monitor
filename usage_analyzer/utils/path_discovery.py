"""Path discovery utilities for Claude data directories."""

import os
from pathlib import Path
from typing import List, Set, Tuple


def get_standard_claude_paths() -> List[str]:
    """Get list of standard Claude data directory paths to check."""
    return [
        "~/.claude/projects",
        "~/.config/claude/projects"
    ]


def discover_claude_data_paths(custom_paths: List[str] = None) -> List[Path]:
    """
    Discover all available Claude data directories.
    
    Args:
        custom_paths: Optional list of custom paths to check instead of standard ones
        
    Returns:
        List of Path objects for existing Claude data directories
    """
    if custom_paths:
        paths_to_check = custom_paths
    else:
        paths_to_check = get_standard_claude_paths()
    
    discovered_paths = []
    
    for path_str in paths_to_check:
        path = Path(path_str).expanduser().resolve()
        if path.exists() and path.is_dir():
            discovered_paths.append(path)
    
    return discovered_paths


def normalize_paths(paths: List[str]) -> List[Path]:
    """
    Normalize and expand user paths.
    
    Args:
        paths: List of path strings that may contain ~ or relative paths
        
    Returns:
        List of resolved Path objects
    """
    normalized = []
    for path_str in paths:
        path = Path(path_str).expanduser().resolve()
        normalized.append(path)
    return normalized


def find_jsonl_files_in_paths(data_paths: List[Path]) -> List[Path]:
    """
    Find all JSONL files across multiple data directories, avoiding duplicates.
    
    Args:
        data_paths: List of Path objects to search in
        
    Returns:
        List of unique JSONL file paths sorted by modification time
    """
    all_files = []
    seen_files: Set[Tuple[str, int, int]] = set()  # (name, size, mtime) for deduplication
    
    for data_path in data_paths:
        if not data_path.exists():
            continue
            
        jsonl_files = list(data_path.rglob("*.jsonl"))
        
        for file_path in jsonl_files:
            try:
                stat = file_path.stat()
                file_signature = (file_path.name, stat.st_size, int(stat.st_mtime))
                
                # Skip if we've seen a file with same name, size, and mtime
                if file_signature not in seen_files:
                    seen_files.add(file_signature)
                    all_files.append(file_path)
                    
            except OSError:
                # Skip files we can't stat
                continue
    
    # Sort by modification time for consistent processing order
    return sorted(all_files, key=lambda p: p.stat().st_mtime if p.exists() else 0)


def parse_path_list(path_string: str, separator: str = None) -> List[str]:
    """
    Parse a string containing multiple paths separated by delimiters.
    
    Args:
        path_string: String containing one or more paths
        separator: Path separator (defaults to auto-detection of ':' or ',')
        
    Returns:
        List of individual path strings
    """
    if not path_string or not path_string.strip():
        return []
    
    if separator is None:
        # Auto-detect separator
        if ':' in path_string and ',' not in path_string:
            separator = ':'
        elif ',' in path_string:
            separator = ','
        else:
            # Single path
            return [path_string.strip()]
    
    paths = [path.strip() for path in path_string.split(separator)]
    return [path for path in paths if path]  # Filter out empty strings


def get_default_data_paths() -> List[str]:
    """
    Get default data paths, checking environment variables first.
    
    Returns:
        List of data paths to use as defaults
    """
    # Check environment variable first
    env_paths = os.getenv("CLAUDE_DATA_PATHS")
    if env_paths:
        return parse_path_list(env_paths)
    
    # Check single path environment variable for backward compatibility
    single_path = os.getenv("CLAUDE_DATA_PATH")
    if single_path:
        return [single_path]
    
    # Return standard paths for auto-discovery
    return get_standard_claude_paths()


def auto_discover_best_paths() -> List[str]:
    """
    Auto-discover the best available Claude data paths.
    
    Returns:
        List of existing data paths, prioritizing standard locations
    """
    standard_paths = get_standard_claude_paths()
    discovered = discover_claude_data_paths(standard_paths)
    
    if discovered:
        return [str(path) for path in discovered]
    else:
        # Return first standard path as fallback even if it doesn't exist
        return [standard_paths[0]]


def validate_data_paths(paths: List[str]) -> Tuple[List[Path], List[str]]:
    """
    Validate a list of data paths, separating valid from invalid ones.
    
    Args:
        paths: List of path strings to validate
        
    Returns:
        Tuple of (valid_paths, invalid_paths)
    """
    valid_paths = []
    invalid_paths = []
    
    for path_str in paths:
        try:
            path = Path(path_str).expanduser().resolve()
            if path.exists() and path.is_dir():
                valid_paths.append(path)
            else:
                invalid_paths.append(path_str)
        except (OSError, ValueError):
            invalid_paths.append(path_str)
    
    return valid_paths, invalid_paths