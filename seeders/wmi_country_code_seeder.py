import json
from models.country import WmiCountryCode, db
from utils import find_country_by_name

# Valid VIN characters in order (excluding I, O, Q)
VIN_CHARACTERS = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 
    'N', 'P', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
]


def expand_range(range_str):
    """
    Expand a range string into individual 2-character codes.
    Examples:
        'AA-AH' -> ['AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH']
        'H' -> ['HA', 'HB', ..., 'HZ', 'H0', 'H1', ..., 'H9']
        'PV' -> ['PV']
        '1, 4, 5' -> ['1A', '1B', ..., '1Z', '10', ..., '4A', ..., '5A', ...]
    """
    range_str = range_str.strip()
    codes = []
    
    # Handle comma-separated values (e.g., "1, 4, 5")
    if ',' in range_str:
        parts = [p.strip() for p in range_str.split(',')]
        for part in parts:
            codes.extend(expand_range(part))
        return codes
    
    # Handle range (e.g., "AA-AH")
    if '-' in range_str:
        start, end = range_str.split('-')
        start = start.strip()
        end = end.strip()
        
        # Both should be 2 characters
        if len(start) == 2 and len(end) == 2:
            first_char = start[0]
            start_second = start[1]
            end_second = end[1]
            
            # Find indices in VIN_CHARACTERS
            try:
                start_idx = VIN_CHARACTERS.index(start_second)
                end_idx = VIN_CHARACTERS.index(end_second)
                
                # Generate all codes in range
                for i in range(start_idx, end_idx + 1):
                    codes.append(first_char + VIN_CHARACTERS[i])
            except ValueError as e:
                print(f"⚠ Invalid character in range '{range_str}': {e}")
        else:
            print(f"⚠ Invalid range format '{range_str}': expected 2-char codes")
    
    # Single character - expand to all combinations (e.g., "H" -> "HA" to "H9")
    elif len(range_str) == 1:
        first_char = range_str
        for second_char in VIN_CHARACTERS:
            codes.append(first_char + second_char)
    
    # Exact 2-character code (e.g., "PV")
    elif len(range_str) == 2:
        codes.append(range_str)
    
    else:
        print(f"⚠ Unknown range format: '{range_str}'")
    
    return codes


def seed_wmi_country_codes():
    """Seed WMI country codes from JSON file"""
    
    print("\n📥 Loading WMI country codes from ./json/wmi_country_codes.json...")
    
    try:
        with open("./json/wmi_country_codes.json", "r", encoding="utf-8") as f:
            wmi_data = json.load(f)
        
        print("✓ Loaded WMI country codes data")
        print("💾 Processing and inserting into database...")
        
        inserted_count = 0
        skipped_count = 0
        errors = []
        
        for entry in wmi_data:
            range_str = entry.get('range', '')
            country_name = entry.get('country', '')
            
            # Find the country in the database
            country = find_country_by_name(country_name)
            
            if not country:
                error_msg = f"⚠ Country not found: {country_name} (range: {range_str})"
                print(error_msg)
                errors.append(error_msg)
                continue
            
            # Expand the range into individual codes
            codes = expand_range(range_str)
            
            if not codes:
                error_msg = f"⚠ No codes generated for range: {range_str}"
                print(error_msg)
                errors.append(error_msg)
                continue
            
            print(f"\n🌍 {country.common_name}: {range_str} ({len(codes)} codes)")
            
            # Insert each code
            for code in codes:
                # Check if this code already exists for this country
                existing = WmiCountryCode.query.filter_by(
                    code=code,
                    country_id=country.id
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Create new WMI country code
                wmi_code = WmiCountryCode(
                    code=code,
                    country_id=country.id
                )
                
                db.session.add(wmi_code)
                inserted_count += 1
            
            print(f"  ✓ Inserted {len(codes)} codes for {country.common_name}")
        
        # Commit all changes
        db.session.commit()
        
        print("="*60)
        print(f"✅ Successfully seeded {inserted_count} WMI country codes!")
        print(f"⊘ Skipped {skipped_count} entries")
        
        if errors:
            print(f"\n⚠ {len(errors)} errors encountered:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
        
        print("="*60)
        
    except FileNotFoundError:
        print("❌ Error: ./json/wmi_country_codes.json not found")
        print("Please make sure the file exists in the json directory")
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
    except Exception as e:
        print(f"❌ Error processing data: {e}")
        db.session.rollback()
        raise