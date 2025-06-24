"""
Simplified Session Block Identifier

Core algorithm for grouping Claude usage entries into time-based session blocks.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from usage_analyzer.models.data_structures import SessionBlock, TokenCounts, UsageEntry


class SessionBlockIdentifier:
    """Groups usage entries into 5-hour session blocks."""
    
    def __init__(self, session_duration_hours: int = 5):
        """Initialize with session duration."""
        self.session_duration_hours = session_duration_hours
        self.session_duration = timedelta(hours=session_duration_hours)
    
    def identify_blocks(self, entries: List[UsageEntry]) -> List[SessionBlock]:
        """Process entries and create session blocks."""
        if not entries:
            return []
        
        blocks = []
        current_block = None
        
        for entry in entries:
            # Check if we need a new block
            if current_block is None or self._should_create_new_block(current_block, entry):
                # Close current block
                if current_block:
                    self._finalize_block(current_block)
                    blocks.append(current_block)
                    
                    # Check for gap
                    gap = self._check_for_gap(current_block, entry)
                    if gap:
                        blocks.append(gap)
                
                # Create new block
                current_block = self._create_new_block(entry)
            
            # Add entry to current block
            self._add_entry_to_block(current_block, entry)
        
        # Finalize last block
        if current_block:
            self._finalize_block(current_block)
            blocks.append(current_block)
        
        # Mark active blocks
        self._mark_active_blocks(blocks)
        
        return blocks
    
    def _should_create_new_block(self, block: SessionBlock, entry: UsageEntry) -> bool:
        """Check if new block is needed."""
        # Time boundary exceeded
        if entry.timestamp >= block.end_time:
            return True
        
        # Inactivity gap detected
        if block.entries and (entry.timestamp - block.entries[-1].timestamp) >= self.session_duration:
            return True
        
        return False
    
    def _round_to_hour(self, timestamp: datetime) -> datetime:
        """Round timestamp to the nearest full hour in UTC."""
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        elif timestamp.tzinfo != timezone.utc:
            timestamp = timestamp.astimezone(timezone.utc)
        
        return timestamp.replace(minute=0, second=0, microsecond=0)
    
    def _create_new_block(self, entry: UsageEntry) -> SessionBlock:
        """Create a new session block."""
        start_time = self._round_to_hour(entry.timestamp)
        end_time = start_time + self.session_duration
        block_id = start_time.isoformat()

        return SessionBlock(
            id=block_id,
            start_time=start_time,
            end_time=end_time,
            entries=[],
            token_counts=TokenCounts(),
            cost_usd=0.0,
            models=[]
        )
    
    def _add_entry_to_block(self, block: SessionBlock, entry: UsageEntry):
        """Add entry to block and aggregate data per model."""
        block.entries.append(entry)
        
        # Get model name (use 'unknown' if missing)
        model = entry.model or 'unknown'
        
        # Initialize per-model stats if not exists
        if model not in block.per_model_stats:
            block.per_model_stats[model] = {
                'input_tokens': 0,
                'output_tokens': 0,
                'cache_creation_tokens': 0,
                'cache_read_tokens': 0,
                'cost_usd': 0.0,
                'entries_count': 0
            }
        
        # Update per-model stats
        model_stats = block.per_model_stats[model]
        model_stats['input_tokens'] += entry.input_tokens
        model_stats['output_tokens'] += entry.output_tokens
        model_stats['cache_creation_tokens'] += entry.cache_creation_tokens
        model_stats['cache_read_tokens'] += entry.cache_read_tokens
        model_stats['cost_usd'] += entry.cost_usd or 0.0
        model_stats['entries_count'] += 1
        
        # Update aggregated token counts (sum across all models)
        block.token_counts.input_tokens += entry.input_tokens
        block.token_counts.output_tokens += entry.output_tokens
        block.token_counts.cache_creation_tokens += entry.cache_creation_tokens
        block.token_counts.cache_read_tokens += entry.cache_read_tokens
        
        # Update aggregated cost (sum across all models)
        if entry.cost_usd:
            block.cost_usd += entry.cost_usd
        
        # Model tracking (prevent duplicates)
        if model and model not in block.models:
            block.models.append(model)
    
    def _finalize_block(self, block: SessionBlock):
        """Set actual end time."""
        if block.entries:
            block.actual_end_time = block.entries[-1].timestamp
    
    def _check_for_gap(self, last_block: SessionBlock, next_entry: UsageEntry) -> Optional[SessionBlock]:
        """Check for inactivity gap between blocks."""
        if not last_block.actual_end_time:
            return None
        
        gap_duration = next_entry.timestamp - last_block.actual_end_time
        
        if gap_duration >= self.session_duration:
            gap_time_str = last_block.actual_end_time.isoformat()
            gap_id = f"gap-{gap_time_str}"
            
            return SessionBlock(
                id=gap_id,
                start_time=last_block.actual_end_time,
                end_time=next_entry.timestamp,
                actual_end_time=None,
                is_gap=True,
                entries=[],
                token_counts=TokenCounts(),
                cost_usd=0.0,
                models=[]
            )
        
        return None
    
    def _mark_active_blocks(self, blocks: List[SessionBlock]):
        """Mark blocks as active if they're still ongoing."""
        current_time = datetime.now(timezone.utc)
        
        for block in blocks:
            if not block.is_gap and block.end_time > current_time:
                block.is_active = True