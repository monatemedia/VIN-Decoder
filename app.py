# app.py
import os
import json
import requests
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vin.db'  # or your PostgreSQL/MySQL URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Country(db.Model):
    __tablename__ = 'countries'
    
    id = db.Column(db.Integer, primary_key=True)
    iso_alpha2 = db.Column(db.String(2), unique=True, nullable=False, index=True)
    iso_alpha3 = db.Column(db.String(3), unique=True, nullable=False, index=True)
    iso_numeric = db.Column(db.String(3), unique=True, nullable=True)
    name = db.Column(db.String(200), nullable=False)
    common_name = db.Column(db.String(200), nullable=True)
    region = db.Column(db.String(100), nullable=True, index=True)
    subregion = db.Column(db.String(100), nullable=True)
    currency_code = db.Column(db.String(3), nullable=True)
    calling_code = db.Column(db.String(10), nullable=True)
    tld = db.Column(db.String(10), nullable=True)
    flag_emoji = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    def __repr__(self):
        return f"<Country {self.common_name or self.name}>"


class WmiCodeDigit1(db.Model):
    __tablename__ = 'wmi_codes_digit_1'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1), nullable=False, index=True)
    country_id = db.Column(db.Integer, db.ForeignKey('countries.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    country = db.relationship('Country', backref=db.backref('wmi_codes_digit_1', lazy=True))
    
    # Unique constraint: each code can only belong to a country once
    __table_args__ = (
        db.UniqueConstraint('code', 'country_id', name='unique_code_country'),
    )
    
    def __repr__(self):
        return f"<WmiCodeDigit1 {self.code} -> {self.country.common_name}>"


# ===== SEEDER FUNCTIONS =====

def get_first_value(data_dict):
    """Helper to get first value from a dictionary"""
    if not data_dict:
        return None
    return list(data_dict.keys())[0] if data_dict else None


def get_calling_code(idd_data):
    """Extract calling code from IDD data"""
    if not idd_data or 'root' not in idd_data:
        return None
    
    root = idd_data.get('root', '')
    suffixes = idd_data.get('suffixes', [])
    
    if suffixes:
        return root + suffixes[0]
    return root if root else None


def map_region(region, subregion):
    """Map mledoze regions to VIN decoder regions"""
    if region == 'Americas':
        # Use subregion to determine North vs South America
        if subregion in ['Northern America', 'Central America', 'Caribbean']:
            return 'North America'
        elif subregion in ['South America']:
            return 'South America'
        else:
            return 'North America'  # Default fallback
    return region


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


# Country name variations and mappings for better matching
COUNTRY_NAME_MAPPINGS = {
    'United States': ['United States', 'United States of America', 'USA'],
    'United Kingdom': ['United Kingdom', 'United Kingdom of Great Britain and Northern Ireland'],
    'South Korea': ['South Korea', 'Korea (Republic of)', 'Republic of Korea'],
    'Taiwan': ['Taiwan', 'Taiwan, Province of China'],
    'Russia': ['Russia', 'Russian Federation'],
    'Iran': ['Iran', 'Iran (Islamic Republic of)'],
    'Turkey': ['Turkey', 'Türkiye'],
    'Vietnam': ['Vietnam', 'Viet Nam'],
    'Ivory Coast': ['Ivory Coast', "Côte d'Ivoire"],
    'Czech Republic': ['Czech Republic', 'Czechia'],
}


def find_country_by_name(country_name):
    """Find a country by name, checking variations and mappings"""
    # Try direct match first (case-insensitive)
    country = Country.query.filter(
        db.func.lower(Country.common_name) == country_name.lower()
    ).first()
    
    if country:
        return country
    
    # Try mapped variations
    for mapped_name, variations in COUNTRY_NAME_MAPPINGS.items():
        if country_name in variations:
            for variation in variations:
                country = Country.query.filter(
                    db.func.lower(Country.common_name) == variation.lower()
                ).first()
                if country:
                    return country
    
    return None


def seed_wmi_codes():
    """Seed WMI codes from JSON file"""
    
    print("\n📥 Loading WMI codes from ./json/wmi_codes.json...")
    
    try:
        with open("./json/wmi_codes.json", "r", encoding="utf-8") as f:
            wmi_data = json.load(f)
        
        print("✓ Loaded WMI codes data")
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
                    existing = WmiCodeDigit1.query.filter_by(
                        code=code,
                        country_id=country.id
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Create new WMI code
                    wmi_code = WmiCodeDigit1(
                        code=code,
                        country_id=country.id
                    )
                    
                    db.session.add(wmi_code)
                    print(f"  ✓ {code} -> {country.common_name}")
                    inserted_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print("="*60)
        print(f"✅ Successfully seeded {inserted_count} WMI codes!")
        print(f"⊘ Skipped {skipped_count} entries")
        
        if errors:
            print(f"\n⚠ {len(errors)} errors encountered:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
        
        print("="*60)
        
    except FileNotFoundError:
        print("❌ Error: ./json/wmi_codes.json not found")
        print("Please make sure the file exists in the json directory")
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
    except Exception as e:
        print(f"❌ Error processing data: {e}")
        db.session.rollback()
        raise


if __name__ == "__main__":
    with app.app_context():
        # Remove old database
        db_path = './instance/vin.db'
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"🗑️  Removed old database: {db_path}")
        
        # Create all tables
        db.create_all()
        print("\n✅ Database and tables created successfully.")
        print("\nTables created:")
        print("  - countries")
        print("  - wmi_codes_digit_1")
        
        # Run seeders
        seed_countries()
        seed_wmi_codes()
        
        print("\n🎉 All done! Database is ready to use.")