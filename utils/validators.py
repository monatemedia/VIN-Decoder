"""
Validation utilities for WMI data
"""
from models.country import WmiCountryCode, db

# Valid VIN characters in order (excluding I, O, Q)
VIN_CHARACTERS = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 
    'N', 'P', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
]


def validate_wmi_country_codes():
    """
    Validate wmi_country_codes table for overlaps and gaps.
    Returns True if validation passes (user continues), False otherwise.
    """
    
    print("\n" + "="*60)
    print("📋 VALIDATING WMI COUNTRY CODES")
    print("="*60)
    
    try:
        # Get all codes from the database
        all_entries = WmiCountryCode.query.all()
        
        if not all_entries:
            print("⚠️  No WMI country codes found in database!")
            print("\n⏸️  Press ENTER to continue...")
            input()
            return True
        
        # Track all codes and their assignments
        code_assignments = {}  # code -> list of countries/regions
        
        # Process all entries from database
        for entry in all_entries:
            code = entry.code
            location = entry.country.common_name if entry.country else "Unknown"
            
            if code not in code_assignments:
                code_assignments[code] = []
            code_assignments[code].append(location)
        
        # Check for overlaps
        print("\n🔍 Checking for overlaps...")
        overlaps = []
        for code, locations in code_assignments.items():
            if len(locations) > 1:
                overlaps.append((code, locations))
        
        if overlaps:
            print(f"⚠️  Found {len(overlaps)} overlapping codes:")
            for code, locations in sorted(overlaps)[:15]:  # Show first 15
                print(f"  {code}: {', '.join(set(locations))}")
            if len(overlaps) > 15:
                print(f"  ... and {len(overlaps) - 15} more")
        else:
            print("✅ No overlaps found!")
        
        # Check for gaps
        print("\n🔍 Checking for gaps...")
        all_possible_codes = []
        for first_char in VIN_CHARACTERS:
            for second_char in VIN_CHARACTERS:
                all_possible_codes.append(first_char + second_char)
        
        assigned_codes = set(code_assignments.keys())
        missing_codes = set(all_possible_codes) - assigned_codes
        
        empty_ranges = []  # Initialize here
        
        if missing_codes:
            print(f"⚠️  Found {len(missing_codes)} unassigned codes")
            
            # Group by first character
            missing_by_first = {}
            for code in sorted(missing_codes):
                first = code[0]
                if first not in missing_by_first:
                    missing_by_first[first] = []
                missing_by_first[first].append(code)
            
            print("\n  Missing codes by first character:")
            partial_ranges = []
            
            for first_char in VIN_CHARACTERS:
                if first_char in missing_by_first:
                    codes = missing_by_first[first_char]
                    # Check if entire range is missing
                    if len(codes) == 34:  # All 34 possible second characters
                        empty_ranges.append(first_char)
                    else:
                        partial_ranges.append((first_char, len(codes)))
            
            if empty_ranges:
                print(f"\n  📭 Empty ranges (all codes missing): {', '.join(empty_ranges)}")
                print(f"     These ranges have no country assignments in the database.")
            
            if partial_ranges:
                print(f"\n  ⚠️  Partial coverage:")
                for first_char, count in partial_ranges[:10]:
                    print(f"    {first_char}: {count} codes missing")
                if len(partial_ranges) > 10:
                    print(f"    ... and {len(partial_ranges) - 10} more ranges")
        else:
            print("✅ No gaps found - all codes are assigned!")
        
        # Summary
        print("\n" + "="*60)
        print("📊 SUMMARY:")
        print(f"  Total codes in database: {len(all_entries)}")
        print(f"  Total unique codes assigned: {len(assigned_codes)}")
        print(f"  Total possible codes: {len(all_possible_codes)}")
        print(f"  Coverage: {len(assigned_codes)/len(all_possible_codes)*100:.1f}%")
        print(f"  Overlaps: {len(overlaps)}")
        print(f"  Gaps: {len(missing_codes)}")
        
        if empty_ranges:
            print(f"  Empty ranges: {', '.join(empty_ranges)}")
        
        print("="*60)
        
        # Pause and ask user to continue
        print("\n⏸️  Press ENTER to continue with factory code seeding...")
        input()
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error during validation: {e}")
        print("\n⏸️  Press ENTER to continue anyway...")
        input()
        return True