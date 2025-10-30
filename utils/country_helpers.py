from models.country import Country, db


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
    'Unknown': ['Unknown'],  # Special catch-all
}


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