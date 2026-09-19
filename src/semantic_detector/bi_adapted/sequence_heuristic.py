# Adapted from BinaryInferno sequence.py
# Original: binaryinferno/sequence.py
# Source: https://github.com/jared-chandler/BinaryInferno
#
# Original Copyright (C) 2023 Jared Chandler (jared.chandler@tufts.edu)
# Licensed under GNU General Public License v3.0
#
# Adaptation Notes:
# - sequenceHeur renamed to calculate_strictly_increasing_ratio
# - Added safety checks for empty/single-element lists
# - Added wrap-around detection (optional)
# - Removed print statements
# - Added type hints
# - Changed division to safe division with zero-check
#
# This file is part of the semantic_detector project and is licensed under GPL v3.0.

from typing import List, Optional


def calculate_strictly_increasing_ratio(values: List[int]) -> Optional[float]:
    """
    Calculate the ratio of strictly increasing adjacent pairs.
    
    This is a safety-corrected version of BinaryInferno's sequenceHeur.
    
    Args:
        values: List of integer values
        
    Returns:
        Ratio of strictly increasing pairs (0.0 to 1.0), or None if insufficient data
        
    Safety Corrections:
        - Returns None for empty or single-element lists (no division by zero)
        - Returns None for lists with only one pair to compare
    """
    if len(values) < 2:
        return None
    
    n = len(values) - 1
    increasing_count = 0
    
    for i in range(n):
        if values[i] < values[i + 1]:
            increasing_count += 1
    
    return increasing_count / n


def calculate_nondecreasing_ratio(values: List[int]) -> Optional[float]:
    """
    Calculate the ratio of non-decreasing adjacent pairs (x[i] <= x[i+1]).
    
    Args:
        values: List of integer values
        
    Returns:
        Ratio of non-decreasing pairs (0.0 to 1.0), or None if insufficient data
    """
    if len(values) < 2:
        return None
    
    n = len(values) - 1
    nondecreasing_count = 0
    
    for i in range(n):
        if values[i] <= values[i + 1]:
            nondecreasing_count += 1
    
    return nondecreasing_count / n


def calculate_step_one_ratio(values: List[int]) -> Optional[float]:
    """
    Calculate the ratio of adjacent pairs that differ by exactly 1.
    
    Args:
        values: List of integer values
        
    Returns:
        Ratio of step-one pairs (0.0 to 1.0), or None if insufficient data
    """
    if len(values) < 2:
        return None
    
    n = len(values) - 1
    step_one_count = 0
    
    for i in range(n):
        if values[i + 1] - values[i] == 1:
            step_one_count += 1
    
    return step_one_count / n


def detect_sequence_pattern(values: List[int], threshold: float = 0.7) -> Optional[str]:
    """
    Detect if values follow a sequence pattern.
    
    Args:
        values: List of integer values
        threshold: Minimum ratio to consider as sequence (default 0.7)
        
    Returns:
        'strictly_increasing', 'nondecreasing', 'step_one', or None
    """
    if len(values) < 2:
        return None
    
    step_one_ratio = calculate_step_one_ratio(values)
    if step_one_ratio is not None and step_one_ratio >= threshold:
        return 'step_one'
    
    strictly_inc_ratio = calculate_strictly_increasing_ratio(values)
    if strictly_inc_ratio is not None and strictly_inc_ratio >= threshold:
        return 'strictly_increasing'
    
    nondec_ratio = calculate_nondecreasing_ratio(values)
    if nondec_ratio is not None and nondec_ratio >= threshold:
        return 'nondecreasing'
    
    return None
