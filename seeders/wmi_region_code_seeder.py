import json
from models.country import WmiRegionCode, db
from utils import find_country_by_name


def seed_wmi_region_codes():
    """Seed WMI region codes from JSON file"""
    
    print("\n📥 Loading WMI region codes from ./json/wmi_region_codes.json...")
    
    try:
        with open("./json/wmi_region_codes.json", "r", encoding="utf-8") as f:
            wmi_data = json.load(f)
        
        print("✓ Loaded WMI region codes data")
        print("💾 Processing and inserting into database...")
        
        inserted_count = 0
        skipped_count = 0
        errors = []
        
        for region, codes in wmi_data.items():
            print(f"\n🌍 Processing region: {region}")
            
            for code, countries in codes.items():
                for country_name in countries:
                    # Find the country in the database
                    country = find_country_by_name(country_name)
                    
                    if not country:
                        error_msg = f"⚠ Country not found: {country_name} (code: {code})"
                        print(error_msg)
                        errors.append(error_msg)
                        skipped_count += 1
                        continue
                    
                    # Check if this WMI code already exists for this country
                    existing = WmiRegionCode.query.filter_by(
                        code=code,
                        country_id=country.id
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Create new WMI region code
                    wmi_code = WmiRegionCode(
                        code=code,
                        country_id=country.id
                    )
                    
                    db.session.add(wmi_code)
                    print(f"  ✓ {code} -> {country.common_name}")
                    inserted_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print("="*60)
        print(f"✅ Successfully seeded {inserted_count} WMI region codes!")
        print(f"⊘ Skipped {skipped_count} entries")
        
        if errors:
            print(f"\n⚠ {len(errors)} errors encountered:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
        
        print("="*60)
        
    except FileNotFoundError:
        print("❌ Error: ./json/wmi_region_codes.json not found")
        print("Please make sure the file exists in the json directory")
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
    except Exception as e:
        print(f"❌ Error processing data: {e}")
        db.session.rollback()
        raise