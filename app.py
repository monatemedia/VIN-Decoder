# app.py
import os
from flask import Flask
from models.country import db
from models import Country, WmiRegionCode
from seeders import seed_countries, seed_wmi_region_codes

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
        
        # Run seeders
        seed_countries()
        seed_wmi_region_codes()
        
        print("\n🎉 All done! Database is ready to use.")