import json
import re
from models.country import WmiFactoryCode, WmiCountryCode, db
from utils import find_country_by_name

# Valid VIN characters in order (excluding I, O, Q)
VIN_CHARACTERS = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 
    'N', 'P', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
]


def expand_wmi_range(range_str):
    """
    Expand WMI range into individual 3-character codes.
    Examples:
        'JHF-JHG' -> ['JHF', 'JHG']
        'JH1-JH5' -> ['JH1', 'JH2', 'JH3', 'JH4', 'JH5']
        'JHZ' -> ['JHZ']
    """
    range_str = range_str.strip()
    codes = []
    
    # Handle range (e.g., "JHF-JHG")
    if '-' in range_str:
        start, end = range_str.split('-')
        start = start.strip()
        end = end.strip()
        
        if len(start) == 3 and len(end) == 3:
            prefix = start[:2]
            start_third = start[2]
            end_third = end[2]
            
            try:
                start_idx = VIN_CHARACTERS.index(start_third)
                end_idx = VIN_CHARACTERS.index(end_third)
                
                for i in range(start_idx, end_idx + 1):
                    codes.append(prefix + VIN_CHARACTERS[i])
            except ValueError:
                print(f"⚠ Invalid character in range '{range_str}'")
        else:
            print(f"⚠ Invalid range format '{range_str}'")
    
    # Single 3-character code
    elif len(range_str) == 3:
        codes.append(range_str)
    
    else:
        print(f"⚠ Unknown WMI range format: '{range_str}'")
    
    return codes


def parse_complex_wmi(wmi_str):
    """
    Parse complex WMI strings with multiple ranges and codes.
    Example: 'JHF-JHG, JHL-JHN, JHZ, JH1-JH5'
    """
    all_codes = []
    
    # Split by comma
    parts = [p.strip() for p in wmi_str.split(',')]
    
    for part in parts:
        codes = expand_wmi_range(part)
        all_codes.extend(codes)
    
    return all_codes


def seed_wmi_factory_codes():
    """Seed WMI factory codes from JSON file"""
    
    print("\n📥 Loading WMI factory codes from ./json/wmi_factory_codes.json...")
    
    try:
        with open("./json/wmi_factory_codes.json", "r", encoding="utf-8") as f:
            factory_data = json.load(f)
        
        print("✓ Loaded WMI factory codes data")
        print("💾 Processing and inserting into database...")
        
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        for entry in factory_data:
            wmi_raw = entry.get('WMI', '').strip()
            manufacturer = entry.get('Manufacturer', '').strip()
            
            if not manufacturer:
                error_msg = f"⚠ No manufacturer name for WMI: {wmi_raw}"
                print(error_msg)
                errors.append(error_msg)
                skipped_count += 1
                continue
            
            # Handle complex WMI codes (ranges, commas, slashes)
            wmi_codes = []
            
            # Check if it's a complex range (contains comma or hyphen with letters)
            if ',' in wmi_raw or re.search(r'[A-Z0-9]{3}-[A-Z0-9]{3}', wmi_raw):
                wmi_codes = parse_complex_wmi(wmi_raw)
            # Handle slash-separated WMI codes
            elif '/' in wmi_raw:
                parts = [p.strip() for p in wmi_raw.split('/')]
                for part in parts:
                    if part and len(part) == 3:
                        wmi_codes.append(part)
                    elif part:
                        # Try to parse as complex range
                        wmi_codes.extend(parse_complex_wmi(part))
            # Simple single WMI code
            elif len(wmi_raw) == 3:
                wmi_codes.append(wmi_raw)
            else:
                error_msg = f"⚠ Invalid WMI format: '{wmi_raw}'"
                print(error_msg)
                errors.append(error_msg)
                continue
            
            if not wmi_codes:
                error_msg = f"⚠ No valid codes from: '{wmi_raw}'"
                print(error_msg)
                errors.append(error_msg)
                continue
            
            # Process each WMI code
            for wmi in wmi_codes:
                if len(wmi) != 3:
                    error_msg = f"⚠ Invalid WMI code length: '{wmi}'"
                    errors.append(error_msg)
                    continue
                
                # Extract first 2 characters to look up country
                country_code = wmi[:2]
                
                # Find the country by looking up the country code in wmi_country_codes
                country_code_entry = WmiCountryCode.query.filter_by(code=country_code).first()
                
                country = None
                region = None
                
                if country_code_entry:
                    # Check if it's a country or region
                    country_name = country_code_entry.country.common_name
                    
                    # List of known regions (not countries)
                    known_regions = ['Africa', 'Asia', 'Europe', 'North America', 'South America', 'Oceania']
                    
                    if country_name in known_regions:
                        region = country_name
                    else:
                        country = country_code_entry.country
                
                # Check if this WMI already exists
                existing = WmiFactoryCode.query.filter_by(wmi=wmi).first()
                
                if existing:
                    # Merge manufacturer names
                    if manufacturer not in existing.manufacturer:
                        existing.manufacturer = f"{existing.manufacturer} & {manufacturer}"
                        db.session.add(existing)
                        location = existing.country.common_name if existing.country else existing.region or "Unknown"
                        print(f"  ⟳ Updated {wmi} -> {existing.manufacturer[:50]}... ({location})")
                        updated_count += 1
                    else:
                        skipped_count += 1
                    continue
                
                # Create new WMI factory code
                factory_code = WmiFactoryCode(
                    wmi=wmi,
                    manufacturer=manufacturer,
                    country_id=country.id if country else None,
                    region=region
                )
                
                db.session.add(factory_code)
                location = country.common_name if country else region or "No Region/Country"
                print(f"  ✓ {wmi} -> {manufacturer[:50]}... ({location})")
                inserted_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print("="*60)
        print(f"✅ Successfully seeded {inserted_count} WMI factory codes!")
        print(f"⟳ Updated {updated_count} existing codes with merged manufacturers")
        print(f"⊘ Skipped {skipped_count} entries")
        
        if errors:
            print(f"\n⚠ {len(errors)} errors encountered:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more")
        
        print("="*60)
        
    except FileNotFoundError:
        print("❌ Error: ./json/wmi_factory_codes.json not found")
        print("Please make sure the file exists in the json directory")
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
    except Exception as e:
        print(f"❌ Error processing data: {e}")
        db.session.rollback()
        raise