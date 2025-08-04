# Urban Dictionary Only - SlangBridge Data Collector
# Simplified version focusing only on Urban Dictionary API

import requests
import json
import time
import pandas as pd
import sqlite3
from datetime import datetime
import re
from typing import List, Dict, Tuple

# =============================================================================
# 1. URBAN DICTIONARY API COLLECTOR
# =============================================================================

class UrbanDictionaryCollector:
    def __init__(self):
        self.base_url = "https://api.urbandictionary.com/v0"
        self.session = requests.Session()
    
    def get_definition(self, term: str) -> List[Dict]:
        """Get definitions for a specific slang term"""
        url = f"{self.base_url}/define"
        params = {'term': term}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('list', [])
        except Exception as e:
            print(f"Error fetching {term}: {e}")
            return []
    
    def get_random_words(self, count: int = 100) -> List[Dict]:
        """Get random slang terms"""
        all_definitions = []
        for i in range(count):
            try:
                response = self.session.get(f"{self.base_url}/random")
                response.raise_for_status()
                data = response.json()
                all_definitions.extend(data.get('list', []))
                time.sleep(0.1)  # Rate limiting
                if i % 10 == 0:
                    print(f"Random collection progress: {i}/{count}")
            except Exception as e:
                print(f"Error fetching random words: {e}")
                continue
        return all_definitions
    
    def collect_popular_slang(self, terms_list: List[str]) -> List[Dict]:
        """Collect definitions for a list of popular slang terms"""
        all_data = []
        
        for i, term in enumerate(terms_list):
            definitions = self.get_definition(term)
            # Filter for quality (minimum upvotes)
            quality_defs = [d for d in definitions if d.get('thumbs_up', 0) >= 10]
            all_data.extend(quality_defs)
            
            if i % 10 == 0:
                print(f"Collection progress: {i}/{len(terms_list)} terms processed")
                
            time.sleep(0.2)  # Be respectful with API calls
            
        return all_data
    
    def extract_slang_standard_pairs(self, definitions: List[Dict]) -> List[Tuple[str, str]]:
        """Extract slang-standard translation pairs from Urban Dictionary data"""
        pairs = []
        
        for definition in definitions:
            word = definition.get('word', '').strip()
            definition_text = definition.get('definition', '').strip()
            example = definition.get('example', '').strip()
            
            if not word or not definition_text:
                continue
                
            # Clean up the definition text
            clean_definition = self.clean_definition(definition_text)
            
            # Create slang-to-standard pair
            if clean_definition:
                pairs.append((word, clean_definition))
                
            # Extract from examples if available
            if example:
                example_pairs = self.extract_from_example(word, example)
                pairs.extend(example_pairs)
                
        return pairs
    
    def clean_definition(self, definition: str) -> str:
        """Clean Urban Dictionary definition text"""
        # Remove markup and clean text
        definition = re.sub(r'\[.*?\]', '', definition)  # Remove [bracketed] text
        definition = re.sub(r'\s+', ' ', definition).strip()
        
        # Extract the main definition (usually first sentence)
        sentences = definition.split('.')
        if sentences:
            return sentences[0].strip()
        return definition
    
    def extract_from_example(self, word: str, example: str) -> List[Tuple[str, str]]:
        """Extract slang usage from examples"""
        pairs = []
        # Look for the word in context and try to infer meaning
        if word.lower() in example.lower():
            # Simple heuristic: if example contains both slang and explanation
            if 'means' in example.lower() or 'is' in example.lower():
                pairs.append((word, example))
        return pairs

# =============================================================================
# 2. DATA STORAGE AND MANAGEMENT
# =============================================================================

class DataManager:
    def __init__(self, db_path: str = 'slangbridge.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS slang_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slang_term TEXT NOT NULL,
                standard_translation TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.0,
                upvotes INTEGER DEFAULT 0,
                context_category TEXT,
                region TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                raw_content TEXT NOT NULL,
                metadata TEXT,
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_slang_pairs(self, pairs: List[Tuple[str, str]], source: str):
        """Store slang-standard translation pairs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for slang, standard in pairs:
            cursor.execute('''
                INSERT INTO slang_terms (slang_term, standard_translation, source)
                VALUES (?, ?, ?)
            ''', (slang, standard, source))
        
        conn.commit()
        conn.close()
        print(f"Stored {len(pairs)} pairs from {source}")
    
    def get_dataset_stats(self) -> Dict:
        """Get statistics about the collected dataset"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM slang_terms')
        total_pairs = cursor.fetchone()[0]
        
        cursor.execute('SELECT source, COUNT(*) FROM slang_terms GROUP BY source')
        source_counts = dict(cursor.fetchall())
        
        cursor.execute('SELECT AVG(LENGTH(slang_term)), AVG(LENGTH(standard_translation)) FROM slang_terms')
        avg_lengths = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_pairs': total_pairs,
            'source_distribution': source_counts,
            'avg_slang_length': avg_lengths[0] if avg_lengths[0] else 0,
            'avg_standard_length': avg_lengths[1] if avg_lengths[1] else 0
        }

# =============================================================================
# 3. CSV EXPORT FUNCTIONALITY
# =============================================================================

class CSVExporter:
    def __init__(self, db_path: str = 'slangbridge.db'):
        self.db_path = db_path
    
    def export_all_data(self, output_file: str = 'slangbridge_complete_dataset.csv'):
        """Export all collected data to CSV"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT 
            slang_term,
            standard_translation,
            source,
            confidence_score,
            upvotes,
            context_category,
            region,
            created_at,
            LENGTH(slang_term) as slang_length,
            LENGTH(standard_translation) as standard_length
        FROM slang_terms
        ORDER BY source, upvotes DESC
        """
        
        df = pd.read_sql_query(query, conn)
        df.to_csv(output_file, index=False, encoding='utf-8')
        conn.close()
        
        print(f"Exported {len(df)} records to {output_file}")
        return df
    
    def export_training_format(self, output_file: str = 'slangbridge_training_data.csv'):
        """Export data in format suitable for ML training"""
        conn = sqlite3.connect(self.db_path)
        
        # Create training format with both directions
        query = """
        SELECT 
            slang_term as input_text,
            standard_translation as target_text,
            'slang_to_standard' as direction,
            source,
            confidence_score
        FROM slang_terms
        WHERE LENGTH(slang_term) > 2 AND LENGTH(standard_translation) > 5
        
        UNION ALL
        
        SELECT 
            standard_translation as input_text,
            slang_term as target_text,
            'standard_to_slang' as direction,
            source,
            confidence_score
        FROM slang_terms
        WHERE LENGTH(slang_term) > 2 AND LENGTH(standard_translation) > 5
        """
        
        df = pd.read_sql_query(query, conn)
        
        # Add additional features for training
        df['input_length'] = df['input_text'].str.len()
        df['target_length'] = df['target_text'].str.len()
        df['word_count_input'] = df['input_text'].str.split().str.len()
        df['word_count_target'] = df['target_text'].str.split().str.len()
        
        df.to_csv(output_file, index=False, encoding='utf-8')
        conn.close()
        
        print(f"Exported {len(df)} training examples to {output_file}")
        return df

def export_for_checkpoint_report():
    """Export data specifically formatted for checkpoint report"""
    exporter = CSVExporter()
    
    # Create comprehensive dataset for report
    conn = sqlite3.connect(exporter.db_path)
    
    # Main dataset with all features
    main_query = """
    SELECT 
        slang_term,
        standard_translation,
        source,
        LENGTH(slang_term) as slang_word_count,
        LENGTH(standard_translation) as standard_word_count,
        upvotes,
        context_category,
        region,
        created_at,
        CASE 
            WHEN LENGTH(slang_term) <= 5 THEN 'short'
            WHEN LENGTH(slang_term) <= 15 THEN 'medium'
            ELSE 'long'
        END as slang_length_category,
        CASE 
            WHEN LENGTH(standard_translation) <= 10 THEN 'short'
            WHEN LENGTH(standard_translation) <= 30 THEN 'medium'
            ELSE 'long'
        END as standard_length_category
    FROM slang_terms
    ORDER BY source, upvotes DESC
    """
    
    df = pd.read_sql_query(main_query, conn)
    df.to_csv('checkpoint2_dataset.csv', index=False, encoding='utf-8')
    
    # Create summary statistics
    summary_stats = {
        'total_pairs': len(df),
        'unique_slang_terms': df['slang_term'].nunique(),
        'sources': df['source'].value_counts().to_dict(),
        'avg_slang_length': df['slang_word_count'].mean(),
        'avg_standard_length': df['standard_word_count'].mean(),
        'length_distribution': df['slang_length_category'].value_counts().to_dict()
    }
    
    # Save summary as JSON and CSV
    import json
    with open('checkpoint2_summary.json', 'w') as f:
        json.dump(summary_stats, f, indent=2, default=str)
    
    # Create summary DataFrame
    summary_df = pd.DataFrame([summary_stats])
    summary_df.to_csv('checkpoint2_summary.csv', index=False)
    
    conn.close()
    
    print(f"Exported checkpoint dataset: {len(df)} records")
    print("Files created:")
    print("- checkpoint2_dataset.csv (main dataset)")
    print("- checkpoint2_summary.csv (statistics)")
    print("- checkpoint2_summary.json (detailed stats)")
    
    return df, summary_stats

# =============================================================================
# 4. MEGA SLANG TERMS LIST
# =============================================================================

def get_mega_slang_list():
    """200+ comprehensive slang terms covering all categories"""
    return [
        # Core Gen Z expressions
        'salty', 'ghosting', 'stan', 'lowkey', 'highkey', 'periodt', 'no cap',
        'bet', 'vibes', 'mood', 'pressed', 'based', 'cringe', 'bussin',
        'slaps', 'fire', 'drip', 'flex', 'sus', 'cap', 'facts', 'deadass',
        'say less', 'hits different', 'straight up', 'fr fr', 'that slaps',
        
        # Social media & internet slang
        'main character', 'side quest', 'understood the assignment', 'sending me',
        'living for this', 'big mood', 'this aint it chief', 'ok boomer',
        'karen', 'simp', 'simping', 'iconic', 'legend', 'queen', 'king',
        'bestie', 'chile', 'the audacity', 'not me', 'im deceased', 'im weak',
        'im crying', 'go off', 'pop off', 'slayed', 'ate and left no crumbs',
        
        # Emotional expressions
        'and i oop', 'sksksk', 'vsco girl', 'basic', 'extra', 'snatched',
        'tea', 'spill the tea', 'thats the tea', 'wig', 'wig snatched',
        'shook', 'woke', 'stay woke', 'cancelled', 'its giving', 'material girl',
        'gaslight', 'gatekeep', 'girlboss', 'pick me', 'not like other girls',
        
        # Gaming & tech slang
        'noob', 'pwned', 'respawn', 'lag', 'glitch', 'npc', 'main character energy',
        'side character', 'touch grass', 'go outside', 'chronically online',
        'very demure', 'very mindful', 'very cutesy', 'core', 'aesthetic',
        'coded', 'energy', 'moment', 'era', 'phase', 'vibe check',
        
        # 2024 trending terms
        'ohio', 'ohio rizz', 'sigma', 'alpha', 'beta', 'ligma', 'sugma',
        'among us', 'sus af', 'impostor', 'vent', 'emergency meeting',
        'skibidi', 'gyat', 'fanum tax', 'brain rot', 'gen alpha',
        'rizz', 'no rizz', 'rizz god', 'unspoken rizz', 'w rizz', 'l rizz',
        
        # Relationship & dating
        'sliding into dms', 'shoot your shot', 'red flag', 'green flag',
        'toxic', 'situationship', 'soft launch', 'hard launch', 'breadcrumbing',
        'love bombing', 'orbiting', 'cushioning', 'benching', 'haunting',
        'submarining', 'zombieing', 'cuffing season', 'hot girl summer',
        
        # Fashion & appearance
        'outfit ate', 'served looks', 'lewk', 'fit check', 'dripped out',
        'dripping', 'clean fit', 'coordinated', 'matchy matchy', 'clashing',
        'put together', 'disheveled', 'mess', 'hot mess', 'disaster',
        'glowed up', 'glow up', 'leveled up', 'upgrade', 'downgrade',
        
        # Food & lifestyle
        'chefs kiss', 'hits the spot', 'slaps different', 'bussin bussin',
        'no seasoning', 'bland', 'spicy', 'too spicy', 'mild', 'boujee',
        'bougie', 'fancy', 'expensive taste', 'cheap', 'budget', 'broke',
        'rich', 'wealthy', 'loaded', 'stacked', 'coins', 'bag', 'secure the bag',
        
        # Music & entertainment
        'bop', 'goes hard', 'fire track', 'skip', 'next', 'on repeat',
        'stuck in my head', 'earworm', 'playlist worthy', 'concert worthy',
        'road trip music', 'study music', 'gym music', 'pump up song',
        'sad girl hours', 'crying playlist', 'shower thoughts', 'vibe',
        
        # Work & school
        'homework', 'procrastinating', 'cramming', 'all nighter', 'burnt out',
        'motivated', 'productive', 'lazy day', 'grind', 'hustle', 'side hustle',
        'main character moment', 'villain era', 'character development',
        'plot twist', 'character arc', 'redemption arc', 'origin story',
        
        # Classic internet acronyms
        'lol', 'lmao', 'lmfao', 'rofl', 'omg', 'wtf', 'smh', 'fml',
        'tbh', 'ngl', 'imo', 'imho', 'afaik', 'tl dr', 'ftw', 'ftl',
        'brb', 'ttyl', 'gtg', 'irl', 'dm', 'pm', 'rt', 'mt', 'hmu',
        
        # Reaction expressions
        'yikes', 'oof', 'rip', 'f in chat', 'press f', 'big oof',
        'major yikes', 'awkward', 'cringe worthy', 'second hand embarrassment',
        'uncomfortable', 'weird flex', 'weird flex but ok', 'ok and',
        'so what', 'who asked', 'nobody asked', 'ratio', 'this you'
    ]

# =============================================================================
# 5. MAIN EXECUTION
# =============================================================================

def quick_test():
    """Quick test with a few terms"""
    print(" Quick Urban Dictionary Test...")
    
    data_manager = DataManager()
    ud_collector = UrbanDictionaryCollector()
    
    test_terms = ['salty', 'ghosting', 'stan', 'lowkey', 'periodt']
    
    definitions = ud_collector.collect_popular_slang(test_terms)
    pairs = ud_collector.extract_slang_standard_pairs(definitions)
    data_manager.store_slang_pairs(pairs, 'test_run')
    
    stats = data_manager.get_dataset_stats()
    print(f" Test complete! {len(pairs)} pairs collected")
    print(f"Total in database: {stats['total_pairs']}")
    
    return pairs

def standard_collection():
    """Standard Urban Dictionary collection with 50+ terms"""
    print("📚 Standard Urban Dictionary Collection...")
    
    data_manager = DataManager()
    ud_collector = UrbanDictionaryCollector()
    
    # Core slang terms
    core_terms = [
        'salty', 'ghosting', 'stan', 'lowkey', 'highkey', 'periodt', 'no cap',
        'bet', 'vibes', 'mood', 'pressed', 'based', 'cringe', 'bussin',
        'slaps', 'fire', 'drip', 'flex', 'sus', 'cap', 'facts', 'deadass',
        'main character', 'side quest', 'understood the assignment', 'rizz',
        'red flag', 'green flag', 'toxic', 'situationship', 'touch grass',
        'ohio', 'sigma', 'alpha', 'skibidi', 'gyat', 'fanum tax', 'brain rot'
    ]
    
    # Collect from core terms
    definitions = ud_collector.collect_popular_slang(core_terms)
    
    # Add some random terms
    print("Adding random terms...")
    random_definitions = ud_collector.get_random_words(50)
    definitions.extend(random_definitions)
    
    # Process all
    pairs = ud_collector.extract_slang_standard_pairs(definitions)
    data_manager.store_slang_pairs(pairs, 'urban_dictionary_standard')
    
    stats = data_manager.get_dataset_stats()
    print(f" Standard collection complete! {len(pairs)} pairs collected")
    print(f"Total in database: {stats['total_pairs']}")
    
    return pairs

def mega_collection():
    """MEGA Urban Dictionary collection with 200+ terms"""
    print("🚀 MEGA Urban Dictionary Collection!")
    print("This will take 10-15 minutes...")
    
    data_manager = DataManager()
    ud_collector = UrbanDictionaryCollector()
    
    # Get the mega slang list
    mega_terms = get_mega_slang_list()
    print(f"Collecting from {len(mega_terms)} curated slang terms...")
    
    # Collect from mega list
    definitions = ud_collector.collect_popular_slang(mega_terms)
    
    # Add multiple rounds of random terms
    print("Adding random terms (round 1/3)...")
    random_1 = ud_collector.get_random_words(100)
    definitions.extend(random_1)
    
    print("Adding random terms (round 2/3)...")
    time.sleep(2)
    random_2 = ud_collector.get_random_words(100)
    definitions.extend(random_2)
    
    print("Adding random terms (round 3/3)...")
    time.sleep(2)
    random_3 = ud_collector.get_random_words(100)
    definitions.extend(random_3)
    
    # Process all definitions
    print("Processing all definitions...")
    pairs = ud_collector.extract_slang_standard_pairs(definitions)
    data_manager.store_slang_pairs(pairs, 'urban_dictionary_mega')
    
    stats = data_manager.get_dataset_stats()
    print(f" MEGA collection complete! {len(pairs)} pairs collected")
    print(f"Total in database: {stats['total_pairs']}")
    print("Source breakdown:")
    for source, count in stats['source_distribution'].items():
        print(f"  📁 {source}: {count}")
    
    return pairs

def export_all_data():
    """Export all data to CSV files"""
    print(" Exporting all data to CSV files...")
    
    exporter = CSVExporter()
    
    # Export complete dataset
    complete_df = exporter.export_all_data()
    
    # Export training format
    training_df = exporter.export_training_format()
    
    # Export checkpoint files
    checkpoint_df, stats = export_for_checkpoint_report()
    
    print(" All exports complete!")
    print(f"Files created:")
    print(f"- slangbridge_complete_dataset.csv ({len(complete_df)} records)")
    print(f"- slangbridge_training_data.csv ({len(training_df)} records)")
    print(f"- checkpoint2_dataset.csv ({len(checkpoint_df)} records)")
    print(f"- checkpoint2_summary.csv (statistics)")
    print(f"- checkpoint2_summary.json (detailed stats)")
    
    return complete_df, training_df, checkpoint_df

if __name__ == "__main__":
    print("Urban Dictionary SlangBridge Collector")
    print("=" * 50)
    
    print("\nChoose collection type:")
    print("1. Quick test (5 terms)")
    print("2. Standard collection (50+ terms + random)")
    print("3. MEGA collection (200+ terms + 300 random)")
    print("4. Export existing data to CSV")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        pairs = quick_test()
        export_choice = input("\nExport to CSV? (y/n): ").strip().lower()
        if export_choice == 'y':
            export_all_data()
    
    elif choice == "2":
        pairs = standard_collection()
        export_choice = input("\nExport to CSV? (y/n): ").strip().lower()
        if export_choice == 'y':
            export_all_data()
    
    elif choice == "3":
        pairs = mega_collection()
        export_choice = input("\nExport to CSV? (y/n): ").strip().lower()
        if export_choice == 'y':
            export_all_data()
    
    elif choice == "4":
        export_all_data()
    
    else:
        print("Invalid choice. Please run again.")
    
    print("\n Done! Check your directory for CSV files.")
    print("Main files for your checkpoint report:")
    print("- checkpoint2_dataset.csv")
    print("- checkpoint2_summary.csv")
    print("- checkpoint2_summary.json")
