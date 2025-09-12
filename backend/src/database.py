import os
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from models import db, User, BankStatement, Transaction, ProcessingLog, Bank, TransactionCategory
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration class"""

    @staticmethod
    def get_database_uri():
        """Get database URI from environment"""
        db_uri = os.getenv('DATABASE_URL')
        if not db_uri:
            raise RuntimeError('DATABASE_URL environment variable is not set')
        return db_uri
    
    @staticmethod
    def init_app(app):
        """Initialize database with Flask app"""
        app.config['SQLALCHEMY_DATABASE_URI'] = DatabaseConfig.get_database_uri()
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 10,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
        }
        
        db.init_app(app)
        migrate = Migrate(app, db)
        
        return db, migrate

def create_database():
    """Create database if it doesn't exist"""
    db_uri = DatabaseConfig.get_database_uri()
    
    # Parse database name from URI
    db_name = db_uri.split('/')[-1].split('?')[0]
    
    # Create connection to postgres default database
    postgres_uri = db_uri.rsplit('/', 1)[0] + '/postgres'
    
    engine = create_engine(postgres_uri)
    conn = engine.connect()
    
    try:
        # Check if database exists
        conn.execute(text("COMMIT"))
        exists = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        ).fetchone()
        
        if not exists:
            # Create database
            conn.execute(text("COMMIT"))
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            logger.info(f"Database '{db_name}' created successfully")
        else:
            logger.info(f"Database '{db_name}' already exists")
            
    except Exception as e:
        logger.error(f"Error creating database: {e}")
    finally:
        conn.close()
        engine.dispose()

def init_database(app):
    """Initialize database tables and seed data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        logger.info("Database tables created successfully")
        
        # Seed initial data
        seed_initial_data()

def seed_initial_data():
    """Seed initial data for banks and categories"""
    
    # Seed banks
    banks_data = [
        {
            'name': 'Bank of America',
            'code': 'BOA',
            'date_format': 'MM/DD/YYYY',
            'statement_patterns': {
                'account_number': r'Account Number:?\s*(\d+)',
                'balance': r'Balance:?\s*\$?([\d,]+\.?\d*)',
                'transaction': r'(\d{2}/\d{2}/\d{4})\s+(.*?)\s+\$?([\d,]+\.?\d*)'
            }
        },
        {
            'name': 'Chase Bank',
            'code': 'CHASE',
            'date_format': 'MM/DD/YYYY',
            'statement_patterns': {
                'account_number': r'Account:?\s*(\d+)',
                'balance': r'Balance:?\s*\$?([\d,]+\.?\d*)',
                'transaction': r'(\d{2}/\d{2}/\d{4})\s+(.*?)\s+\$?([\d,]+\.?\d*)'
            }
        },
        {
            'name': 'Wells Fargo',
            'code': 'WF',
            'date_format': 'MM/DD/YYYY',
            'statement_patterns': {
                'account_number': r'Account\s*#?:?\s*(\d+)',
                'balance': r'Balance:?\s*\$?([\d,]+\.?\d*)',
                'transaction': r'(\d{2}/\d{2}/\d{4})\s+(.*?)\s+\$?([\d,]+\.?\d*)'
            }
        }
    ]
    
    for bank_data in banks_data:
        bank = Bank.query.filter_by(code=bank_data['code']).first()
        if not bank:
            bank = Bank(**bank_data)
            db.session.add(bank)
    
    # Seed transaction categories
    categories_data = [
        {
            'name': 'Income',
            'color': '#28a745',
            'icon': '💰',
            'keywords': ['salary', 'payroll', 'income', 'deposit', 'transfer in'],
            'subcategories': [
                {'name': 'Salary', 'keywords': ['salary', 'payroll', 'wages']},
                {'name': 'Freelance', 'keywords': ['freelance', 'contract', 'consulting']},
                {'name': 'Investment', 'keywords': ['dividend', 'interest', 'investment']},
                {'name': 'Other Income', 'keywords': ['refund', 'reimbursement', 'cashback']}
            ]
        },
        {
            'name': 'Food & Dining',
            'color': '#ffc107',
            'icon': '🍔',
            'keywords': ['restaurant', 'food', 'dining', 'cafe', 'coffee'],
            'subcategories': [
                {'name': 'Restaurants', 'keywords': ['restaurant', 'diner', 'bistro']},
                {'name': 'Groceries', 'keywords': ['grocery', 'supermarket', 'market']},
                {'name': 'Coffee Shops', 'keywords': ['coffee', 'starbucks', 'cafe']},
                {'name': 'Fast Food', 'keywords': ['mcdonald', 'burger', 'pizza']}
            ]
        },
        {
            'name': 'Transportation',
            'color': '#17a2b8',
            'icon': '🚗',
            'keywords': ['gas', 'fuel', 'uber', 'lyft', 'parking', 'transit'],
            'subcategories': [
                {'name': 'Gas & Fuel', 'keywords': ['gas', 'fuel', 'petrol', 'shell', 'exxon']},
                {'name': 'Public Transit', 'keywords': ['metro', 'bus', 'train', 'subway']},
                {'name': 'Ride Sharing', 'keywords': ['uber', 'lyft', 'taxi', 'cab']},
                {'name': 'Parking', 'keywords': ['parking', 'meter']}
            ]
        },
        {
            'name': 'Shopping',
            'color': '#e83e8c',
            'icon': '🛍️',
            'keywords': ['amazon', 'walmart', 'target', 'store', 'shop'],
            'subcategories': [
                {'name': 'Clothing', 'keywords': ['clothing', 'apparel', 'fashion']},
                {'name': 'Electronics', 'keywords': ['electronics', 'computer', 'phone']},
                {'name': 'Online Shopping', 'keywords': ['amazon', 'ebay', 'online']},
                {'name': 'General Merchandise', 'keywords': ['walmart', 'target', 'costco']}
            ]
        },
        {
            'name': 'Bills & Utilities',
            'color': '#dc3545',
            'icon': '📱',
            'keywords': ['utility', 'electric', 'water', 'internet', 'phone'],
            'subcategories': [
                {'name': 'Electricity', 'keywords': ['electric', 'power', 'energy']},
                {'name': 'Water', 'keywords': ['water', 'sewage']},
                {'name': 'Internet', 'keywords': ['internet', 'broadband', 'wifi']},
                {'name': 'Phone', 'keywords': ['phone', 'mobile', 'cellular']}
            ]
        },
        {
            'name': 'Entertainment',
            'color': '#6f42c1',
            'icon': '🎬',
            'keywords': ['netflix', 'spotify', 'movie', 'game', 'entertainment'],
            'subcategories': [
                {'name': 'Streaming Services', 'keywords': ['netflix', 'spotify', 'hulu', 'disney']},
                {'name': 'Movies', 'keywords': ['cinema', 'movie', 'theater']},
                {'name': 'Games', 'keywords': ['game', 'gaming', 'playstation', 'xbox']},
                {'name': 'Events', 'keywords': ['ticket', 'concert', 'show']}
            ]
        },
        {
            'name': 'Healthcare',
            'color': '#20c997',
            'icon': '🏥',
            'keywords': ['pharmacy', 'doctor', 'hospital', 'medical', 'health'],
            'subcategories': [
                {'name': 'Pharmacy', 'keywords': ['pharmacy', 'drug', 'medicine']},
                {'name': 'Doctor', 'keywords': ['doctor', 'physician', 'clinic']},
                {'name': 'Hospital', 'keywords': ['hospital', 'emergency', 'medical']},
                {'name': 'Insurance', 'keywords': ['insurance', 'premium', 'coverage']}
            ]
        },
        {
            'name': 'Transfer',
            'color': '#6c757d',
            'icon': '🔄',
            'keywords': ['transfer', 'withdrawal', 'deposit', 'atm'],
            'subcategories': [
                {'name': 'ATM Withdrawal', 'keywords': ['atm', 'withdrawal', 'cash']},
                {'name': 'Bank Transfer', 'keywords': ['transfer', 'wire', 'ach']},
                {'name': 'Deposit', 'keywords': ['deposit', 'credit']}
            ]
        }
    ]
    
    for cat_data in categories_data:
        parent_cat = TransactionCategory.query.filter_by(name=cat_data['name']).first()
        if not parent_cat:
            subcategories = cat_data.pop('subcategories', [])
            parent_cat = TransactionCategory(**cat_data)
            db.session.add(parent_cat)
            db.session.flush()  # Get parent ID
            
            # Add subcategories
            for subcat_data in subcategories:
                subcat = TransactionCategory(
                    name=subcat_data['name'],
                    parent_id=parent_cat.id,
                    keywords=subcat_data['keywords'],
                    color=cat_data['color'],
                    icon=cat_data['icon']
                )
                db.session.add(subcat)
    
    try:
        db.session.commit()
        logger.info("Initial data seeded successfully")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error seeding data: {e}")

def drop_all_tables(app):
    """Drop all database tables - use with caution!"""
    with app.app_context():
        db.drop_all()
        logger.warning("All database tables dropped!")

def reset_database(app):
    """Reset database - drop and recreate all tables"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_initial_data()
        logger.info("Database reset completed")