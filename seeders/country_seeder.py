import requests
from models.country import Country, db
from utils import get_first_value, get_calling_code, map_region


def seed_countries():
    """Download and seed countries data from mledoze/countries repository"""
    
    url = 'https://raw.githubusercontent.com/mledoze/countries/master/countries.json'
    
    print("\n📥 Downloading countries data from mledoze/countries...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        countries = response.json()
        
        print(f"✓ Downloaded {len(countries)} countries")
        print("💾 Processing and inserting into database...")
        
        inserted_count = 0
        skipped_count = 0
        
        for country_data in countries:
            # Check if country already exists
            iso_alpha2 = country_data.get('cca2')
            
            if not iso_alpha2:
                print(f"⚠ Skipping country without ISO Alpha-2 code")
                skipped_count += 1
                continue
            
            existing = Country.query.filter_by(iso_alpha2=iso_alpha2).first()
            
            if existing:
                skipped_count += 1
                continue
            
            # Create new country record
            country = Country(
                iso_alpha2=iso_alpha2,
                iso_alpha3=country_data.get('cca3'),
                iso_numeric=country_data.get('ccn3'),
                name=country_data.get('name', {}).get('official', country_data['name']['common']),
                common_name=country_data.get('name', {}).get('common'),
                region=map_region(country_data.get('region'), country_data.get('subregion')),
                subregion=country_data.get('subregion'),
                currency_code=get_first_value(country_data.get('currencies')),
                calling_code=get_calling_code(country_data.get('idd', {})),
                tld=country_data.get('tld', [None])[0],
                flag_emoji=country_data.get('flag'),
                is_active=True
            )
            
            db.session.add(country)
            print(f"✓ {country.common_name}")
            inserted_count += 1
        
        # Add special "Unknown" country for unassigned/invalid VIN ranges
        unknown_country = Country.query.filter_by(iso_alpha2='XX').first()
        if not unknown_country:
            unknown_country = Country(
                iso_alpha2='XX',
                iso_alpha3='XXX',
                iso_numeric='999',
                name='Unknown',
                common_name='Unknown',
                region='Unknown',
                subregion='Unknown',
                currency_code=None,
                calling_code=None,
                tld=None,
                flag_emoji='🏳',
                is_active=True
            )
            db.session.add(unknown_country)
            print(f"✓ Unknown (special catch-all country)")
            inserted_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print("="*50)
        print(f"✅ Successfully seeded {inserted_count} countries!")
        print(f"⊘ Skipped {skipped_count} countries")
        print("="*50)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading data: {e}")
        db.session.rollback()
    except Exception as e:
        print(f"❌ Error processing data: {e}")
        db.session.rollback()
        raise