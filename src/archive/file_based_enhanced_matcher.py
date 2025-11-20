#!/usr/bin/env python3
"""
Simple File-Based Enhanced Matching Engine Runner

This script runs the enhanced matching engine on CSV files without requiring database setup.
It's designed to work with the automated pipeline.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import json
import argparse
import re
from pathlib import Path

# Import the matching functions (we'll create a simplified version)
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("file_based_matcher")

class FileBasedMatcher:
    def __init__(self, output_dir="data/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Matching parameters
        self.MIN_SIMILARITY = 65
        self.LEXICAL_WEIGHT = 0.6
        self.SEMANTIC_WEIGHT = 0.4
        
        # Initialize sentence transformer
        self.model = None
        self.embeddings_cache = {}
        
    def load_sentence_transformer(self):
        """Load the sentence transformer model."""
        if self.model is None:
            log.info("Loading Sentence-BERT model...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
    def get_embedding(self, text):
        """Get embedding for text with caching."""
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
            
        if self.model is None:
            self.load_sentence_transformer()
            
        embedding = self.model.encode([text])[0]
        self.embeddings_cache[text] = embedding
        return embedding
        
    def normalize_text(self, text):
        """Basic text normalization."""
        if pd.isna(text):
            return ""
        text = str(text).lower().strip()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text
        
    def calculate_lexical_similarity(self, text1, text2):
        """Calculate lexical similarity using RapidFuzz and Jaccard."""
        fuzz_score = fuzz.token_set_ratio(text1, text2)
        
        # Jaccard similarity
        tokens1 = set(text1.split())
        tokens2 = set(text2.split())
        
        if not tokens1 or not tokens2:
            jaccard_score = 0
        else:
            intersection = len(tokens1 & tokens2)
            union = len(tokens1 | tokens2)
            jaccard_score = (intersection / union) * 100
            
        return (fuzz_score + jaccard_score) / 2
        
    def calculate_semantic_similarity(self, text1, text2):
        """Calculate semantic similarity using embeddings."""
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)
        
        similarity = cosine_similarity([emb1], [emb2])[0][0]
        return similarity * 100  # Convert to percentage
        
    def calculate_hybrid_similarity(self, text1, text2):
        """Calculate hybrid similarity combining lexical and semantic."""
        lexical_sim = self.calculate_lexical_similarity(text1, text2)
        semantic_sim = self.calculate_semantic_similarity(text1, text2)
        
        hybrid_sim = (self.LEXICAL_WEIGHT * lexical_sim + 
                      self.SEMANTIC_WEIGHT * semantic_sim)
        
        return {
            'hybrid_similarity': hybrid_sim,
            'lexical_similarity': lexical_sim,
            'semantic_similarity': semantic_sim
        }
        
    def extract_brand_from_name(self, product_name):
        """Extract brand from product name (simple heuristic)."""
        if pd.isna(product_name):
            return ""
        
        # Take the first few words as potential brand
        words = str(product_name).split()
        if len(words) >= 2:
            return ' '.join(words[:2])
        elif len(words) == 1:
            return words[0]
        return ""
        
    def _parse_retailer_name(self, merchant_data):
        """Parse retailer name from merchant data (which might be JSON)."""
        if pd.isna(merchant_data):
            return "Unknown"
            
        merchant_str = str(merchant_data)
        
        # Try to parse as JSON
        try:
            if merchant_str.startswith('{') and merchant_str.endswith('}'):
                import json
                merchant_obj = eval(merchant_str)  # Safe here as we control the data
                return merchant_obj.get('name', 'Unknown')
        except:
            pass
            
        # Return as-is if not JSON
        return merchant_str
        
    def process_input_file(self, input_file):
        """Process the input CSV file and generate matches."""
        log.info(f"Processing input file: {input_file}")
        
        # Load the data
        df = pd.read_csv(input_file)
        log.info(f"Loaded {len(df)} products")
        
        # Handle different column name conventions
        product_col = 'product_name' if 'product_name' in df.columns else 'title'
        brand_col = 'brand_name' if 'brand_name' in df.columns else None
        category_col = 'category_name' if 'category_name' in df.columns else 'search_query'
        retailer_col = 'retailer_name' if 'retailer_name' in df.columns else 'merchant'
        
        # Standardize column names for easier processing
        df['product_name'] = df[product_col]
        df['brand_name'] = df[brand_col] if brand_col and brand_col in df.columns else ''
        df['category_name'] = df.get(category_col, 'Unknown')
        df['retailer_name'] = df[retailer_col] if retailer_col in df.columns else 'Unknown'
        
        # Basic data cleaning
        df['product_clean'] = df['product_name'].apply(self.normalize_text)
        
        if brand_col and brand_col in df.columns:
            df['brand_clean'] = df['brand_name'].apply(self.normalize_text)
        else:
            df['brand_clean'] = df['product_name'].apply(self.extract_brand_from_name).apply(self.normalize_text)
            
        df['category_clean'] = df['category_name'].apply(self.normalize_text)
        
        # Handle merchant column (which might be JSON)
        if retailer_col in df.columns:
            if df[retailer_col].dtype == 'object':
                # Try to parse JSON if it's a string
                df['retailer_clean'] = df[retailer_col].apply(self._parse_retailer_name).apply(self.normalize_text)
            else:
                df['retailer_clean'] = df[retailer_col].apply(self.normalize_text)
        else:
            df['retailer_clean'] = 'Unknown'
        
        # Generate unique product IDs if not present
        if 'product_id' not in df.columns:
            df['product_id'] = 'PRD' + df.index.astype(str).str.zfill(8)
            
        matches = []
        unmatched_products = []
        
        # Group by category for efficiency
        for category, group in df.groupby('category_clean'):
            group = group.reset_index(drop=True)
            log.info(f"Processing category '{category}': {len(group)} products")
            
            category_matches = []
            matched_in_category = set()
            
            # Compare all pairs within category
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    prod1 = group.iloc[i]
                    prod2 = group.iloc[j]
                    
                    # Skip if same retailer (likely same product)
                    if prod1['retailer_clean'] == prod2['retailer_clean']:
                        continue
                        
                    # Calculate similarity
                    sim_scores = self.calculate_hybrid_similarity(
                        prod1['product_clean'], 
                        prod2['product_clean']
                    )
                    
                    # Brand matching bonus/penalty
                    brand_bonus = 0
                    if prod1['brand_clean'] == prod2['brand_clean'] and prod1['brand_clean']:
                        brand_bonus = 15  # Brand match bonus
                    elif prod1['brand_clean'] != prod2['brand_clean'] and prod1['brand_clean'] and prod2['brand_clean']:
                        brand_bonus = -10  # Brand mismatch penalty
                        
                    final_similarity = sim_scores['hybrid_similarity'] + brand_bonus
                    final_similarity = max(0, min(100, final_similarity))  # Clamp to 0-100
                    
                    if final_similarity >= self.MIN_SIMILARITY:
                        match = {
                            'product_1_id': prod1['product_id'],
                            'product_2_id': prod2['product_id'],
                            'product_1_name': prod1['product_name'],
                            'product_2_name': prod2['product_name'],
                            'brand_1': prod1.get('brand_name', ''),
                            'brand_2': prod2.get('brand_name', ''),
                            'category': category,
                            'size_value_1': prod1.get('size_value', ''),
                            'size_unit_1': prod1.get('size_unit', ''),
                            'size_value_2': prod2.get('size_value', ''),
                            'size_unit_2': prod2.get('size_unit', ''),
                            'price_1': prod1.get('price', ''),
                            'price_2': prod2.get('price', ''),
                            'currency_1': prod1.get('currency', 'GBP'),
                            'currency_2': prod2.get('currency', 'GBP'),
                            'retailer_1': prod1['retailer_clean'],
                            'retailer_2': prod2['retailer_clean'],
                            'similarity': final_similarity,
                            'hybrid_name_similarity': sim_scores['hybrid_similarity'],
                            'lexical_similarity': sim_scores['lexical_similarity'],
                            'semantic_similarity': sim_scores['semantic_similarity'],
                            'brand_similarity': brand_bonus,
                            'size_similarity': 50.0,  # Default
                            'match_source': 'main_engine',
                            'processing_date': datetime.now().strftime('%Y-%m-%d'),
                            'engine_version': 'enhanced_with_embeddings_v1',
                            'confidence_tier': self._get_confidence_tier(final_similarity),
                            'match_rank': 1  # Will be updated later
                        }
                        
                        category_matches.append(match)
                        matched_in_category.add(i)
                        matched_in_category.add(j)
                        
            matches.extend(category_matches)
            
            # Add unmatched products from this category
            for i, prod in group.iterrows():
                if i not in matched_in_category:
                    unmatched = prod.to_dict()
                    unmatched['reason_unmatched'] = f"No match >= {self.MIN_SIMILARITY} (enhanced)"
                    unmatched_products.append(unmatched)
                    
        log.info(f"Found {len(matches)} matches and {len(unmatched_products)} unmatched products")
        
        return matches, unmatched_products, df
        
    def _get_confidence_tier(self, similarity):
        """Determine confidence tier based on similarity."""
        if similarity >= 90:
            return "HIGH"
        elif similarity >= 75:
            return "MEDIUM"
        elif similarity >= 65:
            return "LOW"
        else:
            return "VERY_LOW"
            
    def save_results(self, matches, unmatched_products, original_df, input_file=None):
        """Save the matching results to CSV files."""
        
        # Save matches
        matches_df = pd.DataFrame(matches)
        matches_file = self.output_dir / f"processed_matches_{self.timestamp}.csv"
        matches_df.to_csv(matches_file, index=False)
        log.info(f"Saved {len(matches)} matches to {matches_file}")
        
        # Save unmatched products
        unmatched_df = pd.DataFrame(unmatched_products)
        unmatched_file = self.output_dir / f"unmatched_products_{self.timestamp}.csv"
        unmatched_df.to_csv(unmatched_file, index=False)
        log.info(f"Saved {len(unmatched_products)} unmatched products to {unmatched_file}")
        
        # Generate summary
        total_products = len(original_df)
        matched_products = total_products - len(unmatched_products)
        coverage = (matched_products / total_products) * 100
        
        summary = {
            "processing_metadata": {
                "timestamp": datetime.now().isoformat(),
                "engine_version": "enhanced_with_embeddings_v1",
                "input_file": str(input_file) if input_file else "N/A"
            },
            "dataset_overview": {
                "total_products": total_products,
                "matched_products": matched_products,
                "unmatched_products": len(unmatched_products),
                "coverage_percentage": round(coverage, 1)
            },
            "matching_results": {
                "total_match_pairs": len(matches),
                "main_engine_pairs": len(matches),
                "post_processing_pairs": 0
            },
            "quality_metrics": {
                "avg_similarity": np.mean([m['similarity'] for m in matches]) if matches else 0,
                "median_similarity": np.median([m['similarity'] for m in matches]) if matches else 0,
                "perfect_matches": len([m for m in matches if m['similarity'] >= 95]),
                "high_quality_matches": len([m for m in matches if m['similarity'] >= 85])
            }
        }
        
        summary_file = self.output_dir / f"processing_summary_{self.timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        log.info(f"Saved processing summary to {summary_file}")
        
        return {
            'matches_file': matches_file,
            'unmatched_file': unmatched_file,
            'summary_file': summary_file
        }
        
    def run(self, input_file):
        """Run the complete matching process."""
        log.info("Starting enhanced matching engine...")
        
        matches, unmatched_products, original_df = self.process_input_file(input_file)
        results = self.save_results(matches, unmatched_products, original_df, input_file)
        
        log.info("Enhanced matching engine completed successfully!")
        return results

def main():
    parser = argparse.ArgumentParser(description='File-Based Enhanced Product Matching Engine')
    parser.add_argument('--input', type=str, required=True, help='Input CSV file path')
    parser.add_argument('--output-dir', type=str, default='data/processed', help='Output directory')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
        
    matcher = FileBasedMatcher(args.output_dir)
    results = matcher.run(args.input)
    
    print(f"Results saved:")
    print(f"  Matches: {results['matches_file']}")
    print(f"  Unmatched: {results['unmatched_file']}")
    print(f"  Summary: {results['summary_file']}")

if __name__ == "__main__":
    main()
