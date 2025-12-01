#!/usr/bin/env python3
"""
Date Utilities for Date Dimension Integration
---------------------------------------------
Provides functions to parse date_collected strings and generate date_key values
for linking price_history records to the date_dim table.

Date Format: "YYYYMMDD_HHMMSS" → date_key: YYYYMMDD (integer)
Example: "20251108_120316" → 20251108
"""

import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def parse_date_key(date_collected: str) -> Optional[int]:
    """
    Parse date_collected string and extract date_key (YYYYMMDD as integer).
    
    Args:
        date_collected: String in format "YYYYMMDD_HHMMSS"
        
    Returns:
        Integer date_key (YYYYMMDD) or None if parsing fails
        
    Examples:
        >>> parse_date_key("20251108_120316")
        20251108
        >>> parse_date_key("20240315_093045")
        20240315
        >>> parse_date_key("invalid")
        None
    """
    if not isinstance(date_collected, str):
        logger.warning(f"Invalid date_collected type: {type(date_collected)}")
        return None
    
    # Pattern: YYYYMMDD_HHMMSS
    match = re.match(r'^(\d{8})_\d{6}$', date_collected.strip())
    if match:
        date_key = int(match.group(1))
        # Validate it's a reasonable date (year between 2020-2030)
        year = date_key // 10000
        if 2020 <= year <= 2030:
            return date_key
        else:
            logger.warning(f"Invalid year in date_key: {date_key}")
            return None
    
    logger.warning(f"Could not parse date_collected: {date_collected}")
    return None


def generate_date_dim_entries(start_date_key: int, end_date_key: int) -> list:
    """
    Generate date dimension entries for a range of dates.
    
    Args:
        start_date_key: Starting date (YYYYMMDD as integer)
        end_date_key: Ending date (YYYYMMDD as integer)
        
    Returns:
        List of dictionaries with date dimension attributes
    """
    from datetime import datetime, timedelta
    
    entries = []
    start_date = datetime.strptime(str(start_date_key), '%Y%m%d')
    end_date = datetime.strptime(str(end_date_key), '%Y%m%d')
    
    current_date = start_date
    while current_date <= end_date:
        date_key = int(current_date.strftime('%Y%m%d'))
        
        entry = {
            'date_key': date_key,
            'full_date': current_date.strftime('%Y-%m-%d'),
            'year': current_date.year,
            'quarter': (current_date.month - 1) // 3 + 1,
            'month': current_date.month,
            'month_name': current_date.strftime('%B'),
            'week': int(current_date.strftime('%U')) + 1,
            'day_of_month': current_date.day,
            'day_of_week': current_date.isoweekday(),  # Monday=1, Sunday=7
            'day_name': current_date.strftime('%A'),
            'is_weekend': 1 if current_date.weekday() >= 5 else 0,
            'year_month': current_date.strftime('%Y-%m'),
            'year_quarter': f"{current_date.year}-Q{(current_date.month - 1) // 3 + 1}"
        }
        
        entries.append(entry)
        current_date += timedelta(days=1)
    
    return entries


def add_date_key_to_dataframe(df, date_column='date_collected'):
    """
    Add date_key column to a pandas DataFrame based on date_collected.
    
    Args:
        df: pandas DataFrame with date_collected column
        date_column: Name of the column containing date strings
        
    Returns:
        DataFrame with added date_key column
    """
    import pandas as pd
    
    if date_column not in df.columns:
        logger.error(f"Column '{date_column}' not found in DataFrame")
        return df
    
    logger.info(f"Parsing {len(df)} date_collected values to generate date_key...")
    df['date_key'] = df[date_column].apply(parse_date_key)
    
    # Report any failed parses
    failed = df['date_key'].isna().sum()
    if failed > 0:
        logger.warning(f"Failed to parse {failed} out of {len(df)} dates")
    else:
        logger.info(f"Successfully parsed all {len(df)} dates")
    
    return df


if __name__ == "__main__":
    # Test the functions
    logging.basicConfig(level=logging.INFO)
    
    print("Testing parse_date_key():")
    test_cases = [
        "20251108_120316",
        "20240315_093045",
        "20230101_000000",
        "invalid_date",
        "20501231_235959"  # Future date, should fail validation
    ]
    
    for test in test_cases:
        result = parse_date_key(test)
        print(f"  {test} → {result}")
    
    print("\nTesting generate_date_dim_entries():")
    entries = generate_date_dim_entries(20251101, 20251105)
    for entry in entries:
        print(f"  {entry['date_key']}: {entry['full_date']} ({entry['day_name']}) - Q{entry['quarter']} - Week {entry['week']}")
