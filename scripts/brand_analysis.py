#!/usr/bin/env python3
"""
Brand Analysis Script for Raw Extraction Data

This script analyzes the title field from raw extraction CSV files to identify:
1. Brand names and variations
2. Brand abbreviations
3. Inconsistencies in brand representation
4. Common patterns in naming conventions
"""

import pandas as pd
import re
from collections import Counter, defaultdict
import string

def extract_potential_brands(title):
    """
    Extract potential brand names from product titles using various patterns.
    """
    brands = set()
    
    # Clean the title
    title_clean = title.strip()
    
    # Pattern 1: First word(s) that are capitalized (likely brand)
    words = title_clean.split()
    if words:
        # First word is often the brand
        first_word = words[0]
        if first_word and first_word[0].isupper():
            brands.add(first_word)
    
    # Pattern 2: All caps words (could be brand abbreviations)
    caps_pattern = r'\b[A-Z]{2,}\b'
    caps_matches = re.findall(caps_pattern, title_clean)
    brands.update(caps_matches)
    
    # Pattern 3: Capitalized words that appear at the beginning
    # Look for sequences of capitalized words at the start
    cap_sequence = []
    for word in words:
        if word and word[0].isupper() and not word.isupper():
            cap_sequence.append(word)
        else:
            break
    
    if cap_sequence:
        # Add individual words and combinations
        brands.update(cap_sequence)
        if len(cap_sequence) > 1:
            brands.add(' '.join(cap_sequence))
    
    # Pattern 4: Words in quotes or special formatting
    quoted_pattern = r'["\']([^"\']+)["\']'
    quoted_matches = re.findall(quoted_pattern, title_clean)
    brands.update(quoted_matches)
    
    # Pattern 5: Common brand patterns with &, +, etc.
    brand_connector_pattern = r'\b([A-Z][a-z]+(?:\s*[&+]\s*[A-Z][a-z]+)*)\b'
    connector_matches = re.findall(brand_connector_pattern, title_clean)
    brands.update(connector_matches)
    
    return brands

def identify_abbreviations(brands_list):
    """
    Identify potential abbreviations and their full forms.
    """
    abbreviations = {}
    full_names = {}
    
    for brand in brands_list:
        if len(brand) <= 4 and brand.isupper():
            # Potential abbreviation
            abbreviations[brand] = []
        elif len(brand) > 4:
            # Potential full name
            full_names[brand] = brand
    
    # Try to match abbreviations with full names
    for abbr in abbreviations:
        for full_name in full_names:
            # Simple matching: check if abbreviation could be initials
            initials = ''.join([word[0].upper() for word in full_name.split() if word])
            if abbr == initials:
                abbreviations[abbr].append(full_name)
    
    return abbreviations

def analyze_brand_inconsistencies(brands_counter):
    """
    Analyze brand inconsistencies and variations.
    """
    inconsistencies = defaultdict(list)
    
    brands_lower = {}
    for brand, count in brands_counter.items():
        brand_lower = brand.lower()
        if brand_lower not in brands_lower:
            brands_lower[brand_lower] = []
        brands_lower[brand_lower].append((brand, count))
    
    # Find variations of the same brand
    for brand_lower, variations in brands_lower.items():
        if len(variations) > 1:
            inconsistencies[brand_lower] = variations
    
    return inconsistencies

def main():
    # Read the most recent CSV file
    csv_file = '/Users/mahnoorbhatti/Desktop/Final_Project_Aue_Natural/data/raw/all_search_results_20251105_161626.csv'
    
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} rows from {csv_file}")
        print(f"Columns: {list(df.columns)}")
        print()
        
        if 'title' not in df.columns:
            print("Error: 'title' column not found in the CSV file")
            return
        
        # Extract all potential brands
        all_brands = []
        titles_with_brands = []
        
        for idx, title in enumerate(df['title'].dropna()):
            brands = extract_potential_brands(title)
            all_brands.extend(brands)
            titles_with_brands.append({
                'row': idx,
                'title': title,
                'extracted_brands': list(brands)
            })
        
        # Count brand occurrences
        brand_counter = Counter(all_brands)
        
        print("=== BRAND ANALYSIS RESULTS ===\n")
        
        # 1. Most common brands
        print("1. TOP 20 MOST COMMON BRANDS:")
        print("-" * 40)
        for brand, count in brand_counter.most_common(20):
            print(f"{brand:<25} : {count:>3} occurrences")
        print()
        
        # 2. Potential abbreviations
        print("2. POTENTIAL ABBREVIATIONS:")
        print("-" * 40)
        abbreviations = identify_abbreviations(list(brand_counter.keys()))
        for abbr, full_forms in abbreviations.items():
            count = brand_counter[abbr]
            if full_forms:
                print(f"{abbr:<10} ({count:>2}x) -> Possible full forms: {', '.join(full_forms)}")
            else:
                print(f"{abbr:<10} ({count:>2}x) -> No matching full form found")
        print()
        
        # 3. Brand inconsistencies
        print("3. BRAND INCONSISTENCIES (same brand, different formatting):")
        print("-" * 60)
        inconsistencies = analyze_brand_inconsistencies(brand_counter)
        for brand_lower, variations in inconsistencies.items():
            print(f"Brand variations for '{brand_lower}':")
            for variation, count in sorted(variations, key=lambda x: x[1], reverse=True):
                print(f"  - {variation:<20} : {count:>3} occurrences")
            print()
        
        # 4. Single occurrence brands (potential typos or unique products)
        print("4. BRANDS WITH SINGLE OCCURRENCES (potential typos or unique items):")
        print("-" * 70)
        single_occurrence = [brand for brand, count in brand_counter.items() if count == 1]
        if single_occurrence:
            print(f"Found {len(single_occurrence)} brands with only 1 occurrence:")
            for i, brand in enumerate(sorted(single_occurrence), 1):
                print(f"{i:>3}. {brand}")
                if i >= 30:  # Limit output
                    print(f"... and {len(single_occurrence) - 30} more")
                    break
        else:
            print("No brands with single occurrences found")
        print()
        
        # 5. Brands with special characters or patterns
        print("5. BRANDS WITH SPECIAL CHARACTERS OR PATTERNS:")
        print("-" * 50)
        special_brands = []
        for brand in brand_counter.keys():
            if any(char in brand for char in ['&', '+', '.', '-', "'"]):
                special_brands.append((brand, brand_counter[brand]))
        
        if special_brands:
            for brand, count in sorted(special_brands, key=lambda x: x[1], reverse=True):
                print(f"{brand:<25} : {count:>3} occurrences")
        else:
            print("No brands with special characters found")
        print()
        
        # 6. Sample titles for manual verification
        print("6. SAMPLE TITLES FOR MANUAL VERIFICATION:")
        print("-" * 45)
        print("First 10 titles with extracted brands:")
        for i, item in enumerate(titles_with_brands[:10]):
            print(f"{i+1:>2}. Title: {item['title']}")
            print(f"    Brands: {', '.join(item['extracted_brands']) if item['extracted_brands'] else 'None detected'}")
            print()
        
        # 7. Summary statistics
        print("7. SUMMARY STATISTICS:")
        print("-" * 25)
        print(f"Total unique brands found: {len(brand_counter)}")
        print(f"Total brand mentions: {sum(brand_counter.values())}")
        print(f"Average brands per title: {sum(brand_counter.values()) / len(df):.2f}")
        print(f"Titles with no detected brands: {len([t for t in titles_with_brands if not t['extracted_brands']])}")
        print(f"Brands appearing only once: {len(single_occurrence)}")
        print(f"Brand variations detected: {len(inconsistencies)}")
        
    except FileNotFoundError:
        print(f"Error: File {csv_file} not found")
    except Exception as e:
        print(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()
