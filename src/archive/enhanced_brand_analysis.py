#!/usr/bin/env python3
"""
Enhanced Brand Analysis Script for Identifying True Brand Names and Abbreviations

This script filters out generic product terms to focus on actual brand names
and identifies key abbreviation patterns that need normalization.
"""

import pandas as pd
import re
from collections import Counter, defaultdict

# Generic product terms that should not be considered brands
GENERIC_TERMS = {
    'bar', 'shampoo', 'conditioner', 'serum', 'butter', 'body', 'hair', 'face', 
    'soap', 'skin', 'oil', 'natural', 'organic', 'hydrating', 'solid', 'anti',
    'coconut', 'shea', 'whipped', 'for', 'and', 'the', 'with', 'free', 'dry',
    'care', 'treatment', 'cream', 'lotion', 'formula', 'extract', 'essence',
    'mask', 'cleansing', 'moisturizing', 'nourishing', 'strengthening',
    'softening', 'volumizing', 'clarifying', 'repairing', 'brightening',
    'firming', 'lifting', 'tightening', 'smoothing', 'calming', 'soothing',
    'protecting', 'restoring', 'revitalizing', 'regenerating', 'renewing',
    'refreshing', 'balancing', 'purifying', 'detoxifying', 'exfoliating',
    'normal', 'oily', 'combination', 'sensitive', 'mature', 'fine', 'thick',
    'curly', 'straight', 'wavy', 'frizzy', 'damaged', 'colored', 'treated',
    'day', 'night', 'morning', 'evening', 'daily', 'weekly', 'intensive',
    'gentle', 'mild', 'strong', 'light', 'rich', 'ultra', 'super', 'extra',
    'best', 'new', 'fresh', 'pure', 'clean', 'clear', 'soft', 'smooth',
    'shine', 'glow', 'radiance', 'youth', 'age', 'aging', 'wrinkle', 'line',
    'spot', 'blemish', 'acne', 'blackhead', 'pore', 'tone', 'texture',
    'moisture', 'hydration', 'nutrition', 'vitamin', 'mineral', 'protein',
    'keratin', 'collagen', 'elastin', 'peptide', 'acid', 'complex',
    'lavender', 'rose', 'vanilla', 'mint', 'lemon', 'orange', 'grapefruit',
    'tea', 'green', 'white', 'black', 'red', 'blue', 'pink', 'purple',
    'ml', 'oz', 'g', 'kg', 'mg', 'pack', 'set', 'kit', 'collection',
    'size', 'mini', 'travel', 'full', 'large', 'small', 'xl', 'xxl',
    'men', 'women', 'unisex', 'baby', 'kids', 'children', 'adult',
    'vegan', 'cruelty', 'sulfate', 'paraben', 'silicone', 'alcohol',
    'plastic', 'eco', 'bio', 'dermatologically', 'clinically', 'tested',
    'approved', 'certified', 'professional', 'salon', 'spa', 'luxury',
    'premium', 'essential', 'active', 'potent', 'concentrated', 'intense',
    'maximum', 'minimum', 'optimal', 'perfect', 'complete', 'total',
    'advanced', 'innovative', 'breakthrough', 'revolutionary', 'unique',
    'exclusive', 'special', 'limited', 'edition', 'collection', 'range',
    'line', 'series', 'system', 'routine', 'regime', 'program', 'solution',
    'repair', 'restore', 'renew', 'refresh', 'revive', 'rejuvenate',
    'protect', 'defend', 'shield', 'guard', 'boost', 'enhance', 'improve',
    'control', 'balance', 'regulate', 'stabilize', 'normalize', 'correct',
    'prevent', 'reduce', 'minimize', 'eliminate', 'remove', 'cleanse',
    'wash', 'rinse', 'foam', 'lather', 'bubble', 'gel', 'liquid', 'powder',
    'spray', 'mist', 'drops', 'pearls', 'capsules', 'tablets', 'pills'
}

# Known brand abbreviations that should be normalized
KNOWN_ABBREVIATIONS = {
    'L\'OREAL': ['L\'Oreal', 'OREAL', 'Oreal'],
    'P&G': ['Proctor & Gamble', 'Procter & Gamble'],
    'J&J': ['Johnson & Johnson'],
    'OGX': ['Ogx'],
    'CEO': ['Cosmetic Executive Officer'],
    'NYX': ['Nyx'],
    'MAC': ['M.A.C'],
    'DKNY': ['Donna Karan New York'],
    'YSL': ['Yves Saint Laurent'],
    'TBS': ['The Body Shop'],
    'B&BW': ['Bath & Body Works'],
    'S&G': ['Soap & Glory'],
}

def is_likely_brand(word):
    """
    Determine if a word is likely to be a brand name rather than a generic term.
    """
    if not word or len(word) < 2:
        return False
    
    word_lower = word.lower()
    
    # Skip generic terms
    if word_lower in GENERIC_TERMS:
        return False
    
    # Skip numbers and measurements
    if re.match(r'^\d+[a-z]*$', word_lower):
        return False
    
    # Skip very common words
    common_words = {'of', 'in', 'on', 'at', 'by', 'to', 'from', 'up', 'out', 'all'}
    if word_lower in common_words:
        return False
    
    # Brand indicators:
    # 1. Starts with capital letter
    # 2. Contains special characters (likely brand formatting)
    # 3. All caps (potential abbreviation)
    # 4. Mixed case with no spaces (brand names)
    
    if word[0].isupper():
        return True
    
    if any(char in word for char in ['&', '+', '.', '-', "'"]):
        return True
    
    return False

def extract_real_brands(title):
    """
    Extract actual brand names from product titles, filtering out generic terms.
    """
    brands = set()
    
    # Clean the title
    title_clean = title.strip()
    words = title_clean.split()
    
    # Look for brand patterns at the beginning of the title
    brand_sequence = []
    for i, word in enumerate(words):
        if is_likely_brand(word):
            brand_sequence.append(word)
        else:
            break
        
        # Don't take too many words as a single brand
        if len(brand_sequence) >= 4:
            break
    
    # Add individual brand words and the sequence
    for word in brand_sequence:
        brands.add(word)
    
    if len(brand_sequence) > 1:
        brands.add(' '.join(brand_sequence))
    
    # Look for quoted brand names
    quoted_pattern = r'["\']([^"\']+)["\']'
    quoted_matches = re.findall(quoted_pattern, title_clean)
    for match in quoted_matches:
        if is_likely_brand(match):
            brands.add(match)
    
    # Look for brand patterns with special characters
    special_patterns = [
        r'\b([A-Z][a-z]+(?:[&+\-\'.][A-Z][a-z]+)+)\b',  # Multi-word brands with connectors
        r'\b([A-Z]{2,})\b',  # All caps (abbreviations)
        r'\b([A-Z][a-z]*[A-Z][a-z]*)\b',  # CamelCase
    ]
    
    for pattern in special_patterns:
        matches = re.findall(pattern, title_clean)
        for match in matches:
            if is_likely_brand(match):
                brands.add(match)
    
    return brands

def identify_brand_normalizations():
    """
    Return known brand normalizations that should be applied.
    """
    normalizations = {}
    
    # Add known abbreviations
    for standard, variations in KNOWN_ABBREVIATIONS.items():
        for variation in variations:
            normalizations[variation] = standard
    
    # Common brand variations
    brand_variations = {
        'Loreal': 'L\'Oreal',
        'LOREAL': 'L\'Oreal',
        'Cerave': 'CeraVe',
        'CERAVE': 'CeraVe',
        'Nivea': 'NIVEA',
        'Ethique': 'ETHIQUE',
        'Foamie': 'FOAMIE',
        'HiBAR': 'HIBAR',
        'Kinkind': 'KinKind',
        'Anihana': 'ANIHANA',
        'Akoma': 'AKOMA',
    }
    
    normalizations.update(brand_variations)
    
    return normalizations

def main():
    # Read the most recent CSV file
    csv_file = '/Users/mahnoorbhatti/Desktop/Final_Project_Aue_Natural/data/raw/all_search_results_20251105_161626.csv'
    
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} rows from {csv_file}")
        print()
        
        # Extract real brands (filter out generic terms)
        real_brands = []
        titles_with_brands = []
        
        for idx, title in enumerate(df['title'].dropna()):
            brands = extract_real_brands(title)
            real_brands.extend(brands)
            if brands:  # Only store titles that have detected brands
                titles_with_brands.append({
                    'row': idx,
                    'title': title,
                    'extracted_brands': list(brands)
                })
        
        # Count brand occurrences
        brand_counter = Counter(real_brands)
        
        print("=== ACTUAL BRAND ANALYSIS (Generic terms filtered out) ===\n")
        
        # 1. Top actual brands
        print("1. TOP 30 ACTUAL BRANDS:")
        print("-" * 40)
        for brand, count in brand_counter.most_common(30):
            print(f"{brand:<30} : {count:>3} occurrences")
        print()
        
        # 2. Potential abbreviations (2-5 character all-caps words)
        print("2. POTENTIAL BRAND ABBREVIATIONS:")
        print("-" * 40)
        abbreviations = {}
        for brand, count in brand_counter.items():
            if 2 <= len(brand) <= 5 and brand.isupper() and brand.isalpha():
                abbreviations[brand] = count
        
        for abbr, count in sorted(abbreviations.items(), key=lambda x: x[1], reverse=True):
            print(f"{abbr:<10} : {count:>3} occurrences")
        print()
        
        # 3. Brand variations that need normalization
        print("3. BRAND VARIATIONS NEEDING NORMALIZATION:")
        print("-" * 50)
        normalizations = identify_brand_normalizations()
        
        variations_found = {}
        for brand in brand_counter:
            brand_lower = brand.lower()
            # Group similar brands
            found_group = False
            for group_key, group_brands in variations_found.items():
                if any(b.lower() == brand_lower for b in group_brands):
                    group_brands.append(brand)
                    found_group = True
                    break
            
            if not found_group:
                # Check for similar brands (case differences, etc.)
                similar_brands = [brand]
                for other_brand in brand_counter:
                    if (other_brand != brand and 
                        other_brand.lower() == brand_lower and 
                        other_brand not in similar_brands):
                        similar_brands.append(other_brand)
                
                if len(similar_brands) > 1:
                    variations_found[brand_lower] = similar_brands
        
        for brand_group, variations in variations_found.items():
            if len(variations) > 1:
                print(f"Brand group '{brand_group}':")
                total_count = 0
                for variation in sorted(variations, key=lambda x: brand_counter[x], reverse=True):
                    count = brand_counter[variation]
                    total_count += count
                    recommended = " ← RECOMMEND" if variation == variations[0] else ""
                    print(f"  {variation:<25} : {count:>3} occurrences{recommended}")
                print(f"  Total: {total_count} occurrences")
                print()
        
        # 4. Brands with special characters (likely need attention)
        print("4. BRANDS WITH SPECIAL CHARACTERS:")
        print("-" * 40)
        special_brands = []
        for brand, count in brand_counter.items():
            if any(char in brand for char in ['&', '+', '.', '-', "'"]) and count > 1:
                special_brands.append((brand, count))
        
        for brand, count in sorted(special_brands, key=lambda x: x[1], reverse=True):
            print(f"{brand:<30} : {count:>3} occurrences")
        print()
        
        # 5. Suggested normalization rules
        print("5. SUGGESTED NORMALIZATION RULES FOR CLEAN_DATA SCRIPT:")
        print("-" * 60)
        print("# Brand name normalizations to add to clean_data script:")
        print()
        
        # Generate normalization rules based on findings
        suggested_rules = {}
        
        # Case normalization
        for brand_group, variations in variations_found.items():
            if len(variations) > 1:
                # Use the most common variation as the standard
                standard = max(variations, key=lambda x: brand_counter[x])
                for variation in variations:
                    if variation != standard:
                        suggested_rules[variation] = standard
        
        # Add known normalizations
        suggested_rules.update(normalizations)
        
        for incorrect, correct in sorted(suggested_rules.items()):
            print(f"    '{incorrect}': '{correct}',")
        
        print()
        print("# Example usage in clean_data_script.py:")
        print("def normalize_brand_name(brand_name):")
        print("    brand_normalizations = {")
        for incorrect, correct in list(sorted(suggested_rules.items()))[:10]:
            print(f"        '{incorrect}': '{correct}',")
        print("        # ... add more normalizations")
        print("    }")
        print("    return brand_normalizations.get(brand_name, brand_name)")
        
        print()
        print("6. SUMMARY:")
        print("-" * 15)
        print(f"Total unique actual brands: {len(brand_counter)}")
        print(f"Potential abbreviations found: {len(abbreviations)}")
        print(f"Brand groups needing normalization: {len([g for g in variations_found.values() if len(g) > 1])}")
        print(f"Brands with special characters: {len(special_brands)}")
        print(f"Suggested normalization rules: {len(suggested_rules)}")
        
    except FileNotFoundError:
        print(f"Error: File {csv_file} not found")
    except Exception as e:
        print(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()
