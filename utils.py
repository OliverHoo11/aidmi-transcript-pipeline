"""
Utility functions for error handling, retries, and validation
"""

import asyncio
import logging
from typing import Callable, Any, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    *args,
    **kwargs
) -> Any:
    """
    Retry an async function with exponential backoff
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        *args, **kwargs: Arguments to pass to func
    
    Returns:
        Result from successful function call
    
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"All {max_retries} attempts failed")
    
    raise last_exception


def validate_segment_ids(segment_ids: list, valid_ids: set) -> list:
    """
    Validate that segment IDs exist in the transcript
    
    Args:
        segment_ids: List of segment IDs to validate
        valid_ids: Set of valid segment IDs from transcript
    
    Returns:
        List of validated segment IDs (invalid ones removed)
    """
    validated = [sid for sid in segment_ids if sid in valid_ids]
    
    if len(validated) < len(segment_ids):
        invalid = set(segment_ids) - set(validated)
        logger.warning(f"Removed invalid segment IDs: {invalid}")
    
    return validated


def calculate_token_estimate(text: str) -> int:
    """
    Estimate token count for text (rough approximation)
    ~1 token per 4 characters for English text
    
    Args:
        text: Text to estimate tokens for
    
    Returns:
        Estimated token count
    """
    return len(text) // 4


class TokenCounter:
    """Simple token usage tracker"""
    
    def __init__(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_embedding_tokens = 0
    
    def add_completion(self, prompt_tokens: int, completion_tokens: int):
        """Add completion API call tokens"""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
    
    def add_embedding(self, tokens: int):
        """Add embedding API call tokens"""
        self.total_embedding_tokens += tokens
    
    def get_total(self) -> int:
        """Get total tokens used"""
        return self.total_prompt_tokens + self.total_completion_tokens + self.total_embedding_tokens
    
    def get_summary(self) -> dict:
        """Get token usage summary"""
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "embedding_tokens": self.total_embedding_tokens,
            "total_tokens": self.get_total()
        }
    
    def reset(self):
        """Reset counters"""
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_embedding_tokens = 0
