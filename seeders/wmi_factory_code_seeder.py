import json
from models.country import WmiFactoryCode, WmiCountryCode, db


def seed_wmi_factory_codes():
    """Seed WMI factory codes from JSON file"""
    
    print("\n📥 Loading WMI factory codes from ./json/wmi_factory_codes.json...")
    
    try:
        with open("./json/wmi_factory_codes.json", "r", encoding="utf-8") as f:
            factory_data = json.load(f)
        
        print("✓ Loaded WMI factory codes data")
        print("💾 Processing and inserting into database...")
        
        inserted_count = 0
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
            
            # Handle slash-separated WMI codes (e.g., "AA9/CN1" or "BF9/")
            wmi_codes = []
            if '/' in wmi_raw:
                parts = [p.strip() for p in wmi_raw.split('/')]
                for part in parts:
                    if part and len(part) == 3:
                        wmi_codes.append(part)
                    elif part and len(part) != 3:
                        error_msg = f"⚠ Invalid WMI code part: '{part}' from '{wmi_raw}'"
                        print(error_msg)
                        errors.append(error_msg)
            else:
                wmi_codes.append(wmi_raw)
            
            # Process each WMI code
            for wmi in wmi_codes:
                if not wmi or len(wmi) != 3:
                    error_msg = f"⚠ Invalid WMI code: '{wmi}'"
                    print(error_msg)
                    errors.append(error_msg)
                    skipped_count += 1
                    continue
            
            # Extract first 2 characters to look up country
            country_code = wmi[:2]
            
            # Find the country by looking up the country code in wmi_country_codes
            country_code_entry = WmiCountryCode.query.filter_by(code=country_code).first()
            
            if not country_code_entry:
                error_msg = f"⚠ Country not found for WMI '{wmi}' (country code: {country_code})"
                print(error_msg)
                errors.append(error_msg)
                skipped_count += 1
                continue
            
            country = country_code_entry.country
            
            # Check if this WMI already exists
            existing = WmiFactoryCode.query.filter_by(wmi=wmi).first()
            
            if existing:
                print(f"  ⊘ Skipping {wmi} (already exists)")
                skipped_count += 1
                continue
            
            # Create new WMI factory code
            factory_code = WmiFactoryCode(
                wmi=wmi,
                manufacturer=manufacturer,
                country_id=country.id
            )
            
            db.session.add(factory_code)
            print(f"  ✓ {wmi} -> {manufacturer[:50]}... ({country.common_name})")
            inserted_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print("="*60)
        print(f"✅ Successfully seeded {inserted_count} WMI factory codes!")
        print(f"⊘ Skipped {skipped_count} entries")
        
        if errors:
            print(f"\n⚠ {len(errors)} errors encountered:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
        
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