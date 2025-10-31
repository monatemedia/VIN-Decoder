import sqlite3
import os
from PIL import Image
from pathlib import Path
import re
import shutil

DB_PATH = "./instance/vin.db"
LOGOS_DIR = "./logos/brands"
OUTPUT_DIR = "./img/logos"
THUMBNAIL_HEIGHT = 100  # Height in pixels, width will be calculated to maintain aspect ratio

def setup_database():
    """Drop and recreate the factory_logos table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing table
    cursor.execute("DROP TABLE IF EXISTS factory_logos")
    
    # Create factory_logos table fresh
    cursor.execute("""
        CREATE TABLE factory_logos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factory_id INTEGER NOT NULL,
            logo_filename VARCHAR(255) NOT NULL,
            FOREIGN KEY(factory_id) REFERENCES wmi_factory_codes(id) ON DELETE CASCADE,
            UNIQUE(factory_id, logo_filename)
        )
    """)
    
    conn.commit()
    return conn

def normalize_name(name):
    """Normalize a name for comparison - remove special chars, lowercase, etc."""
    # Remove parentheses and their contents
    name = re.sub(r'\([^)]*\)', '', name)
    # Remove common suffixes and punctuation
    name = re.sub(r'\b(ltd|limited|inc|incorporated|corp|corporation|gmbh|ag|sa|pty|llc|co)\b', '', name, flags=re.IGNORECASE)
    # Remove special characters and extra spaces
    name = re.sub(r'[^a-z0-9\s]', '', name.lower())
    name = ' '.join(name.split())  # Normalize whitespace
    return name

def get_logo_files():
    """Get all logo files from the logos directory"""
    if not os.path.exists(LOGOS_DIR):
        print(f"Error: Logos directory not found at {LOGOS_DIR}")
        return []
    
    logo_files = []
    for file in os.listdir(LOGOS_DIR):
        if file.endswith('.png'):
            # Extract brand name from filename (remove .png extension and replace underscores)
            brand_name = file[:-4].replace('_', ' ')
            logo_files.append({
                'filename': file,
                'brand_name': brand_name,
                'normalized': normalize_name(brand_name)
            })
    
    return logo_files

def get_all_factories(cursor):
    """Get all factories from the database"""
    cursor.execute("SELECT id, manufacturer FROM wmi_factory_codes")
    factories = []
    for row in cursor.fetchall():
        factory_id, manufacturer = row
        factories.append({
            'id': factory_id,
            'name': manufacturer,
            'normalized': normalize_name(manufacturer)
        })
    return factories

def find_matches(logos, factories):
    """Find matches between logos and factories"""
    matches = []
    
    for logo in logos:
        logo_matches = []
        logo_normalized = logo['normalized']
        
        # Skip very short brand names (2 chars or less) to avoid false positives
        if len(logo_normalized) <= 2:
            continue
        
        for factory in factories:
            factory_normalized = factory['normalized']
            
            # Check if logo brand name appears as a whole word in factory name
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(logo_normalized) + r'\b'
            if re.search(pattern, factory_normalized):
                logo_matches.append(factory['id'])
        
        if logo_matches:
            matches.append({
                'logo': logo,
                'factory_ids': logo_matches,
                'match_count': len(logo_matches)
            })
    
    return matches

def resolve_conflicts(matches):
    """Resolve conflicts where multiple logos match the same factory"""
    # Create a mapping of factory_id -> list of logos that match it
    factory_to_logos = {}
    
    for match in matches:
        for factory_id in match['factory_ids']:
            if factory_id not in factory_to_logos:
                factory_to_logos[factory_id] = []
            factory_to_logos[factory_id].append(match)
    
    # For each factory with multiple logo matches, pick the logo with most total matches
    final_mappings = {}
    
    for factory_id, competing_logos in factory_to_logos.items():
        if len(competing_logos) == 1:
            # No conflict
            final_mappings[factory_id] = competing_logos[0]['logo']
        else:
            # Pick the logo with the most matches overall
            winner = max(competing_logos, key=lambda x: x['match_count'])
            final_mappings[factory_id] = winner['logo']
            
            # Log the conflict resolution
            print(f"Conflict for factory {factory_id}: {len(competing_logos)} logos matched")
            print(f"  Winner: {winner['logo']['brand_name']} ({winner['match_count']} total matches)")
    
    return final_mappings

def create_thumbnail(source_path, dest_path):
    """Create a thumbnail of the logo, keeping PNG format for transparency"""
    try:
        with Image.open(source_path) as img:
            # Calculate new width maintaining aspect ratio
            aspect_ratio = img.width / img.height
            new_height = THUMBNAIL_HEIGHT
            new_width = int(new_height * aspect_ratio)
            
            # Resize image
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save as PNG to preserve transparency
            img.save(dest_path, 'PNG', optimize=True)
        
        return True
    except Exception as e:
        print(f"Error creating thumbnail for {source_path}: {e}")
        return False

def main():
    print("=" * 80)
    print("LOGO MATCHER AND THUMBNAIL GENERATOR")
    print("=" * 80)
    print()
    
    # Delete and recreate output directory
    print("Cleaning output directory...")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
        print(f"Deleted {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Created {OUTPUT_DIR}")
    print()
    
    # Setup database
    print("Setting up database...")
    conn = setup_database()
    cursor = conn.cursor()
    print("Dropped and recreated 'factory_logos' table")
    print()
    
    # Get logos and factories
    print("Loading logos...")
    logos = get_logo_files()
    print(f"Found {len(logos)} logos")
    print()
    
    print("Loading factories...")
    factories = get_all_factories(cursor)
    print(f"Found {len(factories)} factories")
    print()
    
    # Find matches
    print("Finding matches...")
    matches = find_matches(logos, factories)
    print(f"Found {len(matches)} logos with matches")
    
    # Show first few matches for debugging
    if matches:
        print("\nFirst 5 logo matches (for debugging):")
        print("-" * 80)
        for match in matches[:5]:
            print(f"  {match['logo']['brand_name']:30} -> {match['match_count']:3} factories")
    print()
    
    # Resolve conflicts
    print("Resolving conflicts...")
    final_mappings = resolve_conflicts(matches)
    print(f"Final mappings: {len(final_mappings)} factories will have logos")
    print()
    
    # Create thumbnails and save to database
    print("Creating thumbnails and saving to database...")
    print("-" * 80)
    
    thumbnail_count = 0
    processed_logos = set()
    
    for factory_id, logo in final_mappings.items():
        logo_filename = logo['filename']
        
        # Create thumbnail (only once per logo)
        if logo_filename not in processed_logos:
            source_path = os.path.join(LOGOS_DIR, logo_filename)
            # Keep as PNG
            thumb_filename = logo_filename
            dest_path = os.path.join(OUTPUT_DIR, thumb_filename)
            
            if create_thumbnail(source_path, dest_path):
                thumbnail_count += 1
                processed_logos.add(logo_filename)
                print(f"Created thumbnail: {thumb_filename}")
            
            db_filename = thumb_filename
        else:
            db_filename = logo_filename
        
        # Insert into database
        try:
            cursor.execute(
                "INSERT INTO factory_logos (factory_id, logo_filename) VALUES (?, ?)",
                (factory_id, db_filename)
            )
        except sqlite3.IntegrityError:
            # Already exists, skip
            pass
    
    conn.commit()
    print()
    
    # Summary statistics
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total logos processed: {len(logos)}")
    print(f"Logos with matches: {len(matches)}")
    print(f"Unique thumbnails created: {thumbnail_count}")
    print(f"Factory-logo mappings created: {len(final_mappings)}")
    print(f"Factories with logos: {len(final_mappings)} / {len(factories)} ({len(final_mappings)/len(factories)*100:.1f}%)")
    print()
    
    # Show some examples
    print("Sample mappings (first 20):")
    print("-" * 80)
    cursor.execute("""
        SELECT wfc.manufacturer, fl.logo_filename
        FROM factory_logos fl
        JOIN wmi_factory_codes wfc ON fl.factory_id = wfc.id
        LIMIT 20
    """)
    for row in cursor.fetchall():
        manufacturer, logo = row
        print(f"{manufacturer[:60]:60} -> {logo}")
    
    print()
    
    # Show logos with most matches
    print("Top 10 logos by number of factory matches:")
    print("-" * 80)
    cursor.execute("""
        SELECT fl.logo_filename, COUNT(*) as match_count
        FROM factory_logos fl
        GROUP BY fl.logo_filename
        ORDER BY match_count DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        logo, count = row
        print(f"{logo:30} -> {count:4} factories")
    
    print()
    print("=" * 80)
    print(f"Thumbnails saved to: {OUTPUT_DIR}")
    print("Database table 'factory_logos' created and populated")
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    main()