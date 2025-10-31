"""
Flask VIN Decoder & Generator Application
Uses the VIN database for accurate decoding
"""
from flask import Flask, render_template, request, jsonify
from models.country import db, Country, WmiRegionCode, WmiCountryCode, WmiFactoryCode
import random
from datetime import datetime
import os

app = Flask(__name__)

# Define the absolute path to the database
# app.root_path is the directory where vin_app.py resides
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'vin.db')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# VIN Constants
VIN_LENGTH = 17
INVALID_CHARS = ['I', 'O', 'Q']
VIN_CHARACTERS = 'ABCDEFGHJKLMNPRSTUVWXYZ0123456789'
DIGITS = '0123456789'

TRANSLITERATION = {
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
    'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
    'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9
}

WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]

MODEL_YEARS = {
    'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014, 'F': 2015,
    'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019, 'L': 2020, 'M': 2021,
    'N': 2022, 'P': 2023, 'R': 2024, 'S': 2025, 'T': 2026, 'V': 2027,
    'W': 2028, 'X': 2029, 'Y': 2030, '1': 2031, '2': 2032, '3': 2033,
    '4': 2034, '5': 2035, '6': 2036, '7': 2037, '8': 2038, '9': 2039
}


def compute_check_digit(vin):
    """Compute VIN check digit"""
    total = sum(TRANSLITERATION.get(vin[i], 0) * WEIGHTS[i] for i in range(VIN_LENGTH))
    remainder = total % 11
    return 'X' if remainder == 10 else str(remainder)


def validate_check_digit(vin):
    """Validate VIN check digit"""
    computed = compute_check_digit(vin)
    return vin[8] == computed


def resolve_model_year(char):
    """Resolve model year with 30-year cycle"""
    base_year = MODEL_YEARS.get(char)
    if not base_year:
        return None
    
    current_year = datetime.now().year
    year = base_year
    
    if year < current_year - 30:
        year += 30
    
    return year if year <= current_year else None


def decode_vin(vin):
    """Decode VIN using database"""
    vin = vin.upper().strip()
    
    # Basic validation
    if len(vin) != VIN_LENGTH:
        return {'error': f'VIN must be exactly {VIN_LENGTH} characters'}
    
    for char in INVALID_CHARS:
        if char in vin:
            return {'error': f'Invalid character "{char}" found'}
    
    # Extract components
    wmi = vin[:3]
    country_code = vin[:2]
    region_code = vin[0]
    
    # Look up in database
    region_entry = WmiRegionCode.query.filter_by(code=region_code).first()
    country_entry = WmiCountryCode.query.filter_by(code=country_code).first()
    factory_entry = WmiFactoryCode.query.filter_by(wmi=wmi).first()
    
    # Build response
    result = {
        'vin': vin,
        'wmi': wmi,
        'vds': vin[3:9],
        'vis': vin[9:17],
        'check_digit': vin[8],
        'check_digit_valid': validate_check_digit(vin),
        'model_year_char': vin[9],
        'plant_code': vin[10],
        'serial_number': vin[11:17]
    }
    
    # Region info
    if region_entry:
        result['region'] = region_entry.country.region
        result['region_country'] = region_entry.country.common_name
        result['region_flag'] = region_entry.country.flag_emoji
    else:
        result['region'] = 'Unknown'
    
    # Country info
    if country_entry:
        result['country'] = country_entry.country.common_name
        result['country_flag'] = country_entry.country.flag_emoji
        result['country_region'] = country_entry.country.region
    else:
        result['country'] = 'Unknown'
    
    # Factory/Manufacturer info
    if factory_entry:
        result['manufacturer'] = factory_entry.manufacturer
        result['factory_country'] = factory_entry.country.common_name if factory_entry.country else factory_entry.region
        result['factory_flag'] = factory_entry.country.flag_emoji if factory_entry.country else '🏭'
    else:
        result['manufacturer'] = 'Unknown Manufacturer'
    
    # Model year
    result['model_year'] = resolve_model_year(vin[9]) or 'Unknown'
    
    return result


def generate_vin():
    """Generate a random valid VIN"""
    # Get random factory
    factories = WmiFactoryCode.query.all()
    factory = random.choice(factories) if factories else None
    
    wmi = factory.wmi if factory else ''.join(random.choices(VIN_CHARACTERS, k=3))
    
    # VDS (positions 3-7)
    vds = ''.join(random.choices(VIN_CHARACTERS, k=5))
    
    # Model year (not in future)
    current_year = datetime.now().year
    valid_years = [k for k, v in MODEL_YEARS.items() if resolve_model_year(k)]
    model_year_char = random.choice(valid_years) if valid_years else 'L'
    
    # Plant code
    plant_code = random.choice(VIN_CHARACTERS)
    
    # Serial number (6 digits)
    serial = ''.join(random.choices(DIGITS, k=6))
    
    # Build VIN with placeholder check digit
    vin_array = list(wmi + vds + '0' + model_year_char + plant_code + serial)
    
    # Compute and insert check digit
    check_digit = compute_check_digit(''.join(vin_array))
    vin_array[8] = check_digit
    
    return ''.join(vin_array)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/decode', methods=['POST'])
def api_decode():
    data = request.get_json()
    vin = data.get('vin', '')
    result = decode_vin(vin)
    return jsonify(result)


@app.route('/api/generate', methods=['POST'])
def api_generate():
    vin = generate_vin()
    decoded = decode_vin(vin)
    return jsonify(decoded)


if __name__ == '__main__':
    app.run(debug=True, port=5000)