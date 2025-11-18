#!/usr/bin/env python3
"""
Deduplication Manager — Auê Natural
-----------------------------------
Removes already-seen products across daily extractions using:
1) URL deduplication
2) Thumbnail-hash deduplication
3) Text-based logical dedup (brand_clean + product_clean [+ category_clean])

Also persists state in JSON, produces labeled summaries, and can rebuild state
from historical files.

Usage:
  python3 src/deduplication_manager.py <raw_or_clean_file.csv>
  python3 src/deduplication_manager.py analyze
  python3 src/deduplication_manager.py stats
  python3 src/deduplication_manager.py reset
"""

import os
import re
import glob
import json
import hashlib
import logging
from datetime import datetime

import numpy as np
import pandas as pd


class DeduplicationManager:
    # ---------------------------
    # Construction / config
    # ---------------------------
    def __init__(self, project_root: str = "."):
        self.project_root = project_root

        self.raw_dir = os.path.join(project_root, "data", "raw")
        self.processed_dir = os.path.join(project_root, "data", "processed")
        os.makedirs(self.processed_dir, exist_ok=True)

        # Persistent state files
        self.thumb_state_file = os.path.join(self.processed_dir, "seen_thumbnails.json")
        self.url_state_file = os.path.join(self.processed_dir, "seen_urls.json")
        self.product_state_file = os.path.join(self.processed_dir, "seen_product_ids.json")  # optional

        # Summary outputs
        self.summary_json = os.path.join(self.processed_dir, "deduplication_summary.json")
        self.summary_csv = os.path.join(self.processed_dir, "deduplication_summary.csv")

        # Logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)

    # ---------------------------
    # State I/O helpers
    # ---------------------------
    def _load_state_set(self, path: str, key: str) -> set:
        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    data = json.load(f)
                    return set(data.get(key, []))
                except Exception:
                    return set()
        return set()

    def _save_state_set(self, path: str, key: str, values: set):
        data = {key: sorted(list(values)), "last_updated": datetime.now().isoformat(), "total_count": len(values)}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_seen_thumbnails(self) -> set:
        return self._load_state_set(self.thumb_state_file, "seen_thumbnails")

    def save_seen_thumbnails(self, s: set):
        self._save_state_set(self.thumb_state_file, "seen_thumbnails", s)

    def load_seen_urls(self) -> set:
        return self._load_state_set(self.url_state_file, "seen_urls")

    def save_seen_urls(self, s: set):
        self._save_state_set(self.url_state_file, "seen_urls", s)

    def load_seen_products(self) -> set:
        # optional; only used if product_id present in input
        return self._load_state_set(self.product_state_file, "seen_products")

    def save_seen_products(self, s: set):
        self._save_state_set(self.product_state_file, "seen_products", s)

    # ---------------------------
    # Normalization helpers
    # ---------------------------
    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = df.columns.str.lower().str.strip().str.replace(r"[^a-z0-9_]", "", regex=True)
        return df

    @staticmethod
    def _canonicalize_url(u: str) -> str:
        if pd.isna(u) or not isinstance(u, str) or not u:
            return u
        u = u.strip().lower()
        # remove common tracking params
        u = re.sub(r"(\?|&)(utm_[^=]+=[^&]+)", "", u)
        u = u.rstrip("&").rstrip("?")
        return u

    @staticmethod
    def _md5(s: str) -> str | None:
        if pd.isna(s) or not isinstance(s, str) or not s:
            return None
        return hashlib.md5(s.encode()).hexdigest()

    # ---------------------------
    # Core deduplication
    # ---------------------------
    def deduplicate_file(self, input_path: str) -> tuple[str | None, dict]:
        """
        Deduplicate a single CSV. Works with either raw or cleaned CSVs.
        If a cleaned version exists beside the raw, it will be preferred.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(input_path)

        self.logger.info(f"Starting deduplication for: {os.path.basename(input_path)}")

        # Prefer a cleaned file if it exists (same name with *_cleaned*.csv)
        base = os.path.splitext(os.path.basename(input_path))[0]
        dir_ = os.path.dirname(input_path)
        cand = sorted(glob.glob(os.path.join(dir_, f"{base.replace('.csv','')}_cleaned*.csv")))
        file_to_use = cand[-1] if cand else input_path
        if file_to_use != input_path:
            self.logger.info(f"Using cleaned file: {os.path.basename(file_to_use)}")

        df = pd.read_csv(file_to_use)
        df = self._normalize_columns(df)

        # Normalize key columns if present
        if "url" in df.columns:
            df["url"] = df["url"].astype(str).map(self._canonicalize_url)
        if "thumbnail" in df.columns:
            df["thumbnail"] = df["thumbnail"].astype(str).str.strip()

        initial_count = len(df)
        self.logger.info(f"Initial rows: {initial_count}")

        # Load states
        seen_urls = self.load_seen_urls()
        seen_thumbs = self.load_seen_thumbnails()
        seen_products = self.load_seen_products()

        self.logger.info(f"Seen URLs: {len(seen_urls)} | Seen thumbnails: {len(seen_thumbs)} | Seen products: {len(seen_products)}")

        # Feature: thumbnail hash
        if "thumbnail" in df.columns:
            df["thumbnail_hash"] = df["thumbnail"].apply(self._md5)
        else:
            df["thumbnail_hash"] = None

        # Start with URL + thumbnail dedup
        url_dup = df["url"].isin(seen_urls) if "url" in df.columns else False
        thumb_dup = df["thumbnail_hash"].isin(seen_thumbs) if "thumbnail_hash" in df.columns else False
        is_new = ~(url_dup | thumb_dup)

        # Optional: product_id-based dedup (if present)
        if "product_id" in df.columns and len(seen_products) > 0:
            prod_dup = df["product_id"].isin(seen_products)
            is_new = is_new & ~prod_dup
        else:
            prod_dup = pd.Series([False] * len(df))

        # Logical text-based dedup (brand_clean + product_clean [+ category_clean])
        if {"brand_clean", "product_clean"}.issubset(df.columns):
            cat_part = df["category_clean"].astype(str).str.lower().str.strip() if "category_clean" in df.columns else "unknown"
            df["logical_key"] = (
                df["brand_clean"].fillna("none").astype(str).str.lower().str.strip()
                + "_"
                + df["product_clean"].fillna("none").astype(str).str.lower().str.strip()
                + "_"
                + cat_part.astype(str)
            )
            text_dup = df["logical_key"].duplicated(keep="first")
            is_new = is_new & ~text_dup
        else:
            df["logical_key"] = None
            text_dup = pd.Series([False] * len(df))

        # Reason labeling for analysis
        df["dedup_reason"] = np.select(
            condlist=[
                url_dup,
                thumb_dup,
                prod_dup if isinstance(prod_dup, pd.Series) else pd.Series([False] * len(df)),
                text_dup,
            ],
            choicelist=["duplicate_url", "duplicate_thumbnail", "duplicate_product_id", "duplicate_text"],
            default="new_entry",
        )

        # Keep new entries only
        new_df = df[is_new].copy()
        new_count = len(new_df)
        removed = initial_count - new_count

        # Update states with only the new entries
        if "url" in new_df.columns:
            seen_urls.update(set(new_df["url"].dropna()))
        seen_thumbs.update(set(new_df["thumbnail_hash"].dropna()))
        if "product_id" in new_df.columns:
            seen_products.update(set(new_df["product_id"].dropna()))

        self.save_seen_urls(seen_urls)
        self.save_seen_thumbnails(seen_thumbs)
        self.save_seen_products(seen_products)

        # Save deduplicated file to processed/
        if new_count > 0:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_name = f"all_search_results_{ts}_deduplicated.csv"
            out_path = os.path.join(self.processed_dir, out_name)
            cols_to_drop = ["thumbnail_hash"]  # keep logical_key & dedup_reason in output for audit
            keep_df = new_df.drop(columns=[c for c in cols_to_drop if c in new_df.columns])
            keep_df.to_csv(out_path, index=False)
        else:
            out_path = None

        # Save summary CSV (reason counts for this run)
        reason_counts = df["dedup_reason"].value_counts(dropna=False).to_dict()
        summary_row = {
            "timestamp": datetime.now().isoformat(),
            "input_file": os.path.basename(file_to_use),
            "initial_rows": int(initial_count),
            "new_rows": int(new_count),
            "removed": int(removed),
            "seen_url_total": len(seen_urls),
            "seen_thumbnail_total": len(seen_thumbs),
            "seen_products_total": len(seen_products),
            **{f"reason_{k}": v for k, v in reason_counts.items()},
        }

        # Append to CSV summary
        if os.path.exists(self.summary_csv):
            pd.DataFrame([summary_row]).to_csv(self.summary_csv, mode="a", header=False, index=False)
        else:
            pd.DataFrame([summary_row]).to_csv(self.summary_csv, index=False)

        # Update JSON stats snapshot
        stats_snapshot = self.get_deduplication_stats()
        with open(self.summary_json, "w") as f:
            json.dump(stats_snapshot, f, indent=2)

        self.logger.info(f"Removed: {removed} | New rows: {new_count}")
        if out_path:
            self.logger.info(f"Saved deduplicated data → {out_path}")
        else:
            self.logger.info("No new products; all were duplicates")

        return out_path, summary_row

    # ---------------------------
    # History analysis / stats
    # ---------------------------
    def analyze_historical_data(self):
        """
        Build state from all historical raw files (and any processed files with URL/thumbnail).
        """
        self.logger.info("Analyzing historical data to rebuild state...")
        url_set, thumb_set, prod_set = set(), set(), set()

        candidates = []
        candidates += sorted(glob.glob(os.path.join(self.raw_dir, "all_search_results_*.csv")))
        candidates += sorted(glob.glob(os.path.join(self.processed_dir, "*.csv")))
        candidates = [c for c in candidates if os.path.isfile(c)]

        for p in candidates:
            try:
                df = pd.read_csv(p)
                df = self._normalize_columns(df)
                if "url" in df.columns:
                    df["url"] = df["url"].astype(str).map(self._canonicalize_url)
                    url_set.update(df["url"].dropna())
                if "thumbnail" in df.columns:
                    df["thumbnail"] = df["thumbnail"].astype(str).str.strip()
                    thumb_set.update(df["thumbnail"].dropna().map(self._md5).dropna())
                if "product_id" in df.columns:
                    prod_set.update(df["product_id"].dropna())
                self.logger.info(f"Processed {os.path.basename(p)}")
            except Exception as e:
                self.logger.warning(f"Skipping {os.path.basename(p)} ({e})")

        self.save_seen_urls(url_set)
        self.save_seen_thumbnails(thumb_set)
        self.save_seen_products(prod_set)
        self.logger.info(f"State rebuilt: URLs={len(url_set)}, Thumbnails={len(thumb_set)}, Products={len(prod_set)}")

    def get_deduplication_stats(self) -> dict:
        raw_files = len(glob.glob(os.path.join(self.raw_dir, "all_search_results_*.csv")))
        proc_files = len(glob.glob(os.path.join(self.processed_dir, "*_deduplicated.csv")))
        return {
            "total_seen_urls": len(self.load_seen_urls()),
            "total_seen_thumbnails": len(self.load_seen_thumbnails()),
            "total_seen_products": len(self.load_seen_products()),
            "raw_files_in_directory": raw_files,
            "deduplicated_files_in_processed": proc_files,
            "last_updated": datetime.now().isoformat(),
        }

    def reset_deduplication_state(self):
        for f in [self.url_state_file, self.thumb_state_file, self.product_state_file]:
            if os.path.exists(f):
                os.remove(f)
                self.logger.info(f"Removed state file: {os.path.basename(f)}")


# ---------------------------
# CLI
# ---------------------------
if __name__ == "__main__":
    import sys

    mgr = DeduplicationManager()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 src/deduplication_manager.py <raw_or_clean_file.csv>")
        print("  python3 src/deduplication_manager.py analyze")
        print("  python3 src/deduplication_manager.py stats")
        print("  python3 src/deduplication_manager.py reset")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "analyze":
        mgr.analyze_historical_data()

    elif cmd == "stats":
        stats = mgr.get_deduplication_stats()
        print(json.dumps(stats, indent=2))

    elif cmd == "reset":
        mgr.reset_deduplication_state()

    else:
        input_csv = sys.argv[1]
        out_path, summary = mgr.deduplicate_file(input_csv)
        print(json.dumps({"output_file": out_path, "summary": summary}, indent=2))
