from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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


class WmiRegionCode(db.Model):
    __tablename__ = 'wmi_region_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1), nullable=False, index=True)
    country_id = db.Column(db.Integer, db.ForeignKey('countries.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    country = db.relationship('Country', backref=db.backref('wmi_region_codes', lazy=True))
    
    # Unique constraint: each code can only belong to a country once
    __table_args__ = (
        db.UniqueConstraint('code', 'country_id', name='unique_code_country'),
    )
    
    def __repr__(self):
        return f"<WmiRegionCode {self.code} -> {self.country.common_name}>"


class WmiCountryCode(db.Model):
    __tablename__ = 'wmi_country_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(2), nullable=False, index=True)
    country_id = db.Column(db.Integer, db.ForeignKey('countries.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    country = db.relationship('Country', backref=db.backref('wmi_country_codes', lazy=True))
    
    # Unique constraint: each code can only belong to a country once
    __table_args__ = (
        db.UniqueConstraint('code', 'country_id', name='unique_country_code'),
    )
    
    def __repr__(self):
        return f"<WmiCountryCode {self.code} -> {self.country.common_name}>"


class WmiFactoryCode(db.Model):
    __tablename__ = 'wmi_factory_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    wmi = db.Column(db.String(3), nullable=False, unique=True, index=True)
    manufacturer = db.Column(db.Text, nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey('countries.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    country = db.relationship('Country', backref=db.backref('wmi_factory_codes', lazy=True))
    
    def __repr__(self):
        return f"<WmiFactoryCode {self.wmi} -> {self.manufacturer[:30]}...>"