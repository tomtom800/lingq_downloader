#!/usr/bin/env python3
"""
LingQ Vocabulary Downloader
Downloads all your saved vocabulary (LingQs) from LingQ using their API
"""

import requests
import json
import csv
import os
import time
from datetime import datetime
from typing import List, Dict, Optional
import argparse

class LingQDownloader:
    def __init__(self, api_key: str, base_url: str = "https://www.lingq.com/api/v2"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_key}',
            'Content-Type': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """Test if the API connection is working"""
        try:
            response = self.session.get(f"{self.base_url}/languages/")
            return response.status_code == 200
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def get_languages(self) -> List[Dict]:
        """Get list of all languages"""
        try:
            response = self.session.get(f"{self.base_url}/languages/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting languages: {e}")
            return []
    
    def get_user_contexts(self) -> List[Dict]:
        """Get user's language learning contexts"""
        try:
            response = self.session.get(f"{self.base_url}/contexts/")
            response.raise_for_status()
            return response.json().get('results', [])
        except Exception as e:
            print(f"Error getting contexts: {e}")
            return []
    
    def get_lingqs_for_language(self, language_code: str, page_size: int = 50) -> List[Dict]:
        """Download all LingQs for a specific language with rate limiting"""
        all_lingqs = []
        page = 1
        consecutive_errors = 0
        
        print(f"Downloading LingQs for {language_code}...")
        
        while True:
            try:
                url = f"{self.base_url}/{language_code}/cards/"
                params = {
                    'page_size': page_size,
                    'page': page
                }
                
                response = self.session.get(url, params=params)
                
                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = 60 + (consecutive_errors * 30)  # Exponential backoff
                    print(f"  Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    consecutive_errors += 1
                    if consecutive_errors > 5:
                        print(f"  Too many rate limit errors. Stopping at page {page}")
                        break
                    continue
                
                response.raise_for_status()
                data = response.json()
                consecutive_errors = 0  # Reset error counter on success
                
                results = data.get('results', [])
                if not results:
                    break
                
                all_lingqs.extend(results)
                print(f"  Downloaded page {page}, total LingQs: {len(all_lingqs)}")
                
                # Check if there are more pages
                if not data.get('next'):
                    break
                
                page += 1
                
                # Progressive delay - slower as we get more data
                if page < 10:
                    time.sleep(1)
                elif page < 50:
                    time.sleep(2)
                else:
                    time.sleep(3)
                
            except requests.exceptions.RequestException as e:
                if "429" in str(e):
                    wait_time = 60 + (consecutive_errors * 30)
                    print(f"  Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    consecutive_errors += 1
                    if consecutive_errors > 5:
                        print(f"  Too many rate limit errors. Stopping at page {page}")
                        break
                else:
                    print(f"Error downloading page {page}: {e}")
                    break
            except Exception as e:
                print(f"Unexpected error downloading page {page}: {e}")
                break
        
        print(f"Downloaded {len(all_lingqs)} LingQs for {language_code}")
        return all_lingqs
    
    def flatten_lingq(self, lingq: Dict) -> Dict:
        """Flatten a LingQ object for easier export"""
        # Get the first/best translation
        best_hint = ""
        hint_locale = ""
        if lingq.get('hints'):
            # Sort by popularity (highest first)
            sorted_hints = sorted(lingq['hints'], key=lambda x: x.get('popularity', 0), reverse=True)
            best_hint = sorted_hints[0].get('text', '')
            hint_locale = sorted_hints[0].get('locale', '')
        
        # Get all translations
        all_translations = []
        for hint in lingq.get('hints', []):
            all_translations.append(f"{hint.get('text', '')} ({hint.get('locale', '')})")
        
        return {
            'id': lingq.get('pk'),
            'term': lingq.get('term', ''),
            'fragment': lingq.get('fragment', ''),
            'best_translation': best_hint,
            'translation_locale': hint_locale,
            'all_translations': ' | '.join(all_translations),
            'importance': lingq.get('importance', 0),
            'status': lingq.get('status', 0),
            'notes': lingq.get('notes', ''),
            'tags': ', '.join(lingq.get('tags', [])),
            'srs_due_date': lingq.get('srs_due_date', ''),
            'last_reviewed_correct': lingq.get('last_reviewed_correct', ''),
            'words': ', '.join(lingq.get('words', [])),
            'audio': lingq.get('audio', ''),
            'url': lingq.get('url', '')
        }
    
    def save_to_json(self, data: Dict, filename: str) -> None:
        """Save data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved to {filename}")
    
    def save_to_csv(self, lingqs: List[Dict], filename: str) -> None:
        """Save LingQs to CSV file"""
        if not lingqs:
            print("No LingQs to save")
            return
        
        fieldnames = [
            'id', 'term', 'fragment', 'best_translation', 'translation_locale',
            'all_translations', 'importance', 'status', 'notes', 'tags',
            'srs_due_date', 'last_reviewed_correct', 'words', 'audio', 'url'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for lingq in lingqs:
                flattened = self.flatten_lingq(lingq)
                writer.writerow(flattened)
        
        print(f"Saved {len(lingqs)} LingQs to {filename}")
    
    def download_all_lingqs(self, languages: Optional[List[str]] = None,
                          export_format: str = 'both') -> Dict:
        """Download all LingQs for specified languages or all user languages"""
        
        if not self.test_connection():
            print("❌ Connection test failed. Please check your API key.")
            return {}
        
        print("✅ Connection successful!")
        
        # Get user's languages if not specified
        if not languages:
            contexts = self.get_user_contexts()
            if not contexts:
                print("No language contexts found. Let's try common languages...")
                # Fallback: try common language codes
                common_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh']
                languages = []
                for lang in common_languages:
                    # Test if user has LingQs in this language
                    try:
                        test_response = self.session.get(f"{self.base_url}/{lang}/cards/?page_size=1")
                        if test_response.status_code == 200:
                            data = test_response.json()
                            if data.get('count', 0) > 0:
                                languages.append(lang)
                                print(f"Found LingQs in {lang}")
                    except:
                        continue
                
                if not languages:
                    print("No LingQs found in common languages. Please specify language codes manually.")
                    return {}
            else:
                # Extract language codes from contexts
                all_languages = self.get_languages()
                lang_lookup = {lang['url']: lang['code'] for lang in all_languages}
                
                # Debug: print the structure to understand what we're working with
                print("Debug - First context:", contexts[0] if contexts else "No contexts")
                
                languages = []
                for context in contexts:
                    lang_url = context.get('language')
                    if isinstance(lang_url, str):
                        lang_code = lang_lookup.get(lang_url)
                        if lang_code:
                            languages.append(lang_code)
                    elif isinstance(lang_url, dict):
                        # If language is already a dict with code
                        lang_code = lang_url.get('code')
                        if lang_code:
                            languages.append(lang_code)
                
                languages = list(set(languages))  # Remove duplicates
        
        print(f"Will download LingQs for languages: {', '.join(languages)}")
        
        all_data = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for lang_code in languages:
            print(f"\n--- Processing {lang_code} ---")
            lingqs = self.get_lingqs_for_language(lang_code)
            
            if lingqs:
                all_data[lang_code] = lingqs
                
                # Save individual language files
                if export_format in ['json', 'both']:
                    json_filename = f"lingqs_{lang_code}_{timestamp}.json"
                    self.save_to_json(lingqs, json_filename)
                
                if export_format in ['csv', 'both']:
                    csv_filename = f"lingqs_{lang_code}_{timestamp}.csv"
                    self.save_to_csv(lingqs, csv_filename)
        
        # Save combined file
        if all_data:
            if export_format in ['json', 'both']:
                combined_json = f"lingqs_all_{timestamp}.json"
                self.save_to_json(all_data, combined_json)
            
            if export_format in ['csv', 'both']:
                # Combine all LingQs into one CSV with language column
                all_lingqs_flat = []
                for lang_code, lingqs in all_data.items():
                    for lingq in lingqs:
                        flattened = self.flatten_lingq(lingq)
                        flattened['language'] = lang_code
                        all_lingqs_flat.append(flattened)
                
                if all_lingqs_flat:
                    combined_csv = f"lingqs_all_{timestamp}.csv"
                    fieldnames = ['language'] + [
                        'id', 'term', 'fragment', 'best_translation', 'translation_locale',
                        'all_translations', 'importance', 'status', 'notes', 'tags',
                        'srs_due_date', 'last_reviewed_correct', 'words', 'audio', 'url'
                    ]
                    
                    with open(combined_csv, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(all_lingqs_flat)
                    
                    print(f"Saved combined {len(all_lingqs_flat)} LingQs to {combined_csv}")
        
        return all_data


def main():
    parser = argparse.ArgumentParser(description='Download LingQs from LingQ API')
    parser.add_argument('--api-key', required=True, help='Your LingQ API key')
    parser.add_argument('--languages', nargs='+', help='Language codes to download (e.g., en es fr)')
    parser.add_argument('--format', choices=['json', 'csv', 'both'], default='csv',
                       help='Export format (default: csv)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume download for remaining languages')
    
    args = parser.parse_args()
    
    downloader = LingQDownloader(args.api_key)
    
    print("🚀 Starting LingQ download...")
    print("=" * 50)
    print("⚠️  Note: This will be slow to respect API rate limits")
    print("   Large collections may take hours to download completely")
    print("=" * 50)
    
    result = downloader.download_all_lingqs(
        languages=args.languages,
        export_format=args.format
    )
    
    if result:
        total_lingqs = sum(len(lingqs) for lingqs in result.values())
        print(f"\n✅ Download complete! Total LingQs: {total_lingqs}")
        print(f"Languages: {', '.join(result.keys())}")
        
        # Show incomplete languages
        if args.languages:
            incomplete = set(args.languages) - set(result.keys())
            if incomplete:
                print(f"⚠️  Incomplete downloads for: {', '.join(incomplete)}")
                print("   You can retry with: --languages " + " ".join(incomplete))
    else:
        print("\n❌ No LingQs downloaded.")


if __name__ == "__main__":
    main()
