import requests
import pandas as pd
from datetime import datetime
import time
import json

# Your credentials
USERNAME = 'mahnoorbhatti_6JRvx'
PASSWORD = 'Auenatural=2025'

# Your search queries
queries = [
    'shampoo bar',
    'conditioner bar',
    'face serum',
    'body butter'
]

all_results = []

# Scrape each query with pagination
for query_idx, query in enumerate(queries, 1):
    print(f"\n{'='*70}")
    print(f"[{query_idx}/{len(queries)}] Searching for: {query}")
    print('='*70)

    successful_pages = 0
    failed_pages = 0

    # Request multiple pages (1-10 = 100 results)
    for page in range(1, 11):  # Pages 1 to 10
        print(f"  Page {page}/10...", end=' ')

        payload = {
            'source': 'google_shopping_search',
            'query': query,
            'geo_location': 'United Kingdom',
            'parse': True,
            'start_page': page,
            'pages': 1
        }

        try:
            response = requests.post(
                'https://realtime.oxylabs.io/v1/queries',
                auth=(USERNAME, PASSWORD),
                json=payload,
                timeout=60  # Increased timeout
            )

            # Check HTTP status
            response.raise_for_status()

            # Check if response has content
            if not response.text or not response.text.strip():
                print(f"✗ Empty response")
                failed_pages += 1
                time.sleep(3)  # Wait before next request
                continue

            # Try to parse JSON
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"✗ Invalid JSON: {str(e)[:50]}")
                failed_pages += 1
                time.sleep(3)
                continue

            # Check if results exist in expected structure
            if 'results' not in data:
                print(f"✗ No 'results' key in response")
                failed_pages += 1
                time.sleep(3)
                continue

            if not data['results'] or len(data['results']) == 0:
                print(f"✗ Empty results array")
                failed_pages += 1
                time.sleep(3)
                continue

            # Check for content
            result = data['results'][0]
            if 'content' not in result:
                print(f"✗ No 'content' in result")
                failed_pages += 1
                time.sleep(3)
                continue

            # Check for organic results
            if 'results' not in result['content']:
                print(f"✗ No 'results' in content")
                failed_pages += 1
                time.sleep(3)
                continue

            if 'organic' not in result['content']['results']:
                print(f"✗ No 'organic' results")
                failed_pages += 1
                time.sleep(3)
                continue

            # Extract organic results
            organic = result['content']['results']['organic']

            if not organic or len(organic) == 0:
                print(f"✗ Empty organic results")
                failed_pages += 1
                time.sleep(3)
                continue

            # Add metadata to each result
            for item in organic:
                item['search_query'] = query
                item['page_number'] = page
                item['timestamp'] = datetime.now().strftime("%Y%m%d_%H%M%S")

            all_results.extend(organic)
            successful_pages += 1
            print(f"✓ Got {len(organic)} results")

        except requests.exceptions.Timeout:
            print(f"✗ Request timeout")
            failed_pages += 1

        except requests.exceptions.ConnectionError:
            print(f"✗ Connection error")
            failed_pages += 1

        except requests.exceptions.HTTPError as e:
            print(f"✗ HTTP error: {e.response.status_code}")
            failed_pages += 1

        except KeyError as e:
            print(f"✗ Missing key in response: {e}")
            failed_pages += 1

        except Exception as e:
            print(f"✗ Unexpected error: {str(e)[:50]}")
            failed_pages += 1

        # Increased delay between requests
        time.sleep(3)  # 3 seconds between pages

    # Summary for this query
    print(f"\n  Summary: {successful_pages} successful, {failed_pages} failed")

    # Longer delay between queries
    if query_idx < len(queries):
        print(f"  Waiting 5 seconds before next query...")
        time.sleep(5)

# Convert to DataFrame and save
print(f"\n{'='*70}")
print("FINAL RESULTS")
print('='*70)

if all_results:
    df = pd.DataFrame(all_results)

    # Create filename with timestamp
    filename = f'all_search_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    df.to_csv(filename, index=False)

    print(f"\n✓ Total results collected: {len(df)}")
    print(f"✓ Saved to: {filename}")

    # Show breakdown by query
    print("\n📊 Breakdown by search query:")
    summary = df.groupby('search_query').size()
    for query, count in summary.items():
        print(f"  {query}: {count} results")

    # Show sample
    print(f"\n📋 Sample of first 5 results:")
    print(df[['search_query', 'page_number', 'title', 'url']].head())

else:
    print("\n✗ No results collected!")
    print("  Check your Oxylabs credentials and account credits.")

print(f"\n{'='*70}")