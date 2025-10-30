# app.py
import os
from flask import Flask
from models.country import db
from models import Country, WmiRegionCode, WmiCountryCode, WmiFactoryCode
from seeders import (
    seed_countries, 
    seed_wmi_region_codes, 
    seed_wmi_country_codes, 
    fill_missing_wmi_ranges,
    seed_wmi_factory_codes
)
from utils import validate_wmi_country_codes

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db with app
db.init_app(app)


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
        print("  - wmi_region_codes")
        print("  - wmi_country_codes")
        print("  - wmi_factory_codes")
        
        # Run seeders
        seed_countries()
        seed_wmi_region_codes()
        seed_wmi_country_codes()
        
        # Fill any missing ranges with "Unknown" country
        fill_missing_wmi_ranges()
        
        # Validate WMI country codes after filling gaps
        validate_wmi_country_codes()
        
        # Continue with factory codes
        seed_wmi_factory_codes()
        
        print("\n🎉 All done! Database is ready to use.")