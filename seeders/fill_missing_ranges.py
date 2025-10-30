"""
Fill missing WMI country code ranges with "Unknown" country
This handles empty ranges D, F, G, 0 and any other gaps
"""
from models.country import Country, WmiCountryCode, db

# Valid VIN characters in order (excluding I, O, Q)
VIN_CHARACTERS = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 
    'N', 'P', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
]


def fill_missing_wmi_ranges():
    """Fill all missing WMI country code ranges with Unknown country"""
    
    print("\n📥 Filling missing WMI country code ranges...")
    
    try:
        # Get the "Unknown" country
        unknown_country = Country.query.filter_by(common_name='Unknown').first()
        
        if not unknown_country:
            print("❌ Error: 'Unknown' country not found in database")
            print("   Make sure seed_countries() has run first")
            return
        
        # Generate all possible 2-character codes
        all_possible_codes = []
        for first_char in VIN_CHARACTERS:
            for second_char in VIN_CHARACTERS:
                all_possible_codes.append(first_char + second_char)
        
        # Get all existing codes
        existing_codes = set(code.code for code in WmiCountryCode.query.all())
        
        # Find missing codes
        missing_codes = set(all_possible_codes) - existing_codes
        
        if not missing_codes:
            print("✅ No missing codes found - all ranges are assigned!")
            return
        
        print(f"✓ Found {len(missing_codes)} missing codes")
        print("💾 Assigning to 'Unknown' country...")
        
        # Group by first character for display
        missing_by_first = {}
        for code in sorted(missing_codes):
            first = code[0]
            if first not in missing_by_first:
                missing_by_first[first] = []
            missing_by_first[first].append(code)
        
        inserted_count = 0
        
        for first_char, codes in sorted(missing_by_first.items()):
            print(f"\n🔧 Filling range {first_char}: {len(codes)} codes")
            
            for code in codes:
                wmi_code = WmiCountryCode(
                    code=code,
                    country_id=unknown_country.id
                )
                db.session.add(wmi_code)
                inserted_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print("\n" + "="*60)
        print(f"✅ Successfully filled {inserted_count} missing codes!")
        print(f"   All codes now assigned to 'Unknown' country")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error filling missing ranges: {e}")
        db.session.rollback()
        raise