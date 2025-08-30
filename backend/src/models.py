from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    statements = db.relationship('BankStatement', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'statement_count': self.statements.count()
        }

class BankStatement(db.Model):
    __tablename__ = 'bank_statements'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    
    # File information
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(50))
    
    # Account information
    account_number = db.Column(db.String(50))
    account_holder_name = db.Column(db.String(255))
    bank_name = db.Column(db.String(255))
    statement_period_start = db.Column(db.Date)
    statement_period_end = db.Column(db.Date)
    
    # Balance information
    opening_balance = db.Column(db.Numeric(12, 2))
    closing_balance = db.Column(db.Numeric(12, 2))
    total_credits = db.Column(db.Numeric(12, 2))
    total_debits = db.Column(db.Numeric(12, 2))
    
    # Metadata
    raw_text = db.Column(db.Text)
    account_info_json = db.Column(JSONB)  # Store additional account info as JSON
    processing_status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    processing_error = db.Column(db.Text)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='statement', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'account_number': self.account_number,
            'account_holder_name': self.account_holder_name,
            'bank_name': self.bank_name,
            'statement_period': {
                'start': self.statement_period_start.isoformat() if self.statement_period_start else None,
                'end': self.statement_period_end.isoformat() if self.statement_period_end else None
            },
            'balances': {
                'opening': float(self.opening_balance) if self.opening_balance else None,
                'closing': float(self.closing_balance) if self.closing_balance else None,
                'total_credits': float(self.total_credits) if self.total_credits else None,
                'total_debits': float(self.total_debits) if self.total_debits else None
            },
            'account_info': self.account_info_json,
            'processing_status': self.processing_status,
            'transaction_count': self.transactions.count(),
            'uploaded_at': self.uploaded_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id = db.Column(UUID(as_uuid=True), db.ForeignKey('bank_statements.id'), nullable=False)
    
    # Transaction details
    transaction_date = db.Column(db.Date)
    posting_date = db.Column(db.Date)
    description = db.Column(db.Text)
    reference_number = db.Column(db.String(100))
    
    # Amount information
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    transaction_type = db.Column(db.String(20))  # credit, debit
    balance = db.Column(db.Numeric(12, 2))
    
    # Categorization
    category = db.Column(db.String(100))
    subcategory = db.Column(db.String(100))
    merchant_name = db.Column(db.String(255))
    
    # Additional metadata
    raw_text = db.Column(db.Text)  # Original OCR text for this transaction
    metadata_json = db.Column(JSONB)  # Store additional transaction metadata
    confidence_score = db.Column(db.Float)  # OCR confidence score
    
    # Flags
    is_pending = db.Column(db.Boolean, default=False)
    is_flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_transaction_date', 'transaction_date'),
        db.Index('idx_amount', 'amount'),
        db.Index('idx_category', 'category'),
        db.Index('idx_statement_date', 'statement_id', 'transaction_date'),
    )
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'statement_id': str(self.statement_id),
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'posting_date': self.posting_date.isoformat() if self.posting_date else None,
            'description': self.description,
            'reference_number': self.reference_number,
            'amount': float(self.amount) if self.amount else None,
            'transaction_type': self.transaction_type,
            'balance': float(self.balance) if self.balance else None,
            'category': self.category,
            'subcategory': self.subcategory,
            'merchant_name': self.merchant_name,
            'metadata': self.metadata_json,
            'confidence_score': self.confidence_score,
            'is_pending': self.is_pending,
            'is_flagged': self.is_flagged,
            'flag_reason': self.flag_reason,
            'created_at': self.created_at.isoformat()
        }

class ProcessingLog(db.Model):
    __tablename__ = 'processing_logs'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id = db.Column(UUID(as_uuid=True), db.ForeignKey('bank_statements.id'))
    
    # Log details
    action = db.Column(db.String(100))  # upload, ocr_start, ocr_complete, parse_start, parse_complete, error
    status = db.Column(db.String(50))  # success, failed, warning
    message = db.Column(db.Text)
    details_json = db.Column(JSONB)
    
    # Performance metrics
    processing_time_ms = db.Column(db.Integer)
    pages_processed = db.Column(db.Integer)
    transactions_found = db.Column(db.Integer)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'statement_id': str(self.statement_id) if self.statement_id else None,
            'action': self.action,
            'status': self.status,
            'message': self.message,
            'details': self.details_json,
            'processing_time_ms': self.processing_time_ms,
            'created_at': self.created_at.isoformat()
        }

class Bank(db.Model):
    __tablename__ = 'banks'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), unique=True, nullable=False)
    code = db.Column(db.String(50), unique=True)
    
    # Bank patterns for better OCR recognition
    date_format = db.Column(db.String(50))  # e.g., 'MM/DD/YYYY', 'DD-MM-YYYY'
    statement_patterns = db.Column(JSONB)  # Regex patterns for parsing
    
    # Bank specific configurations
    config_json = db.Column(JSONB)
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'code': self.code,
            'date_format': self.date_format,
            'patterns': self.statement_patterns,
            'config': self.config_json,
            'is_active': self.is_active
        }

class TransactionCategory(db.Model):
    __tablename__ = 'transaction_categories'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), unique=True, nullable=False)
    parent_id = db.Column(UUID(as_uuid=True), db.ForeignKey('transaction_categories.id'))
    
    # Category rules for auto-categorization
    keywords = db.Column(JSONB)  # List of keywords to match
    rules_json = db.Column(JSONB)  # Complex rules for categorization
    
    # UI customization
    color = db.Column(db.String(7))  # Hex color code
    icon = db.Column(db.String(50))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Self-referential relationship for subcategories
    subcategories = db.relationship('TransactionCategory', backref=db.backref('parent', remote_side=[id]))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'parent_id': str(self.parent_id) if self.parent_id else None,
            'keywords': self.keywords,
            'rules': self.rules_json,
            'color': self.color,
            'icon': self.icon,
            'subcategories': [sub.to_dict() for sub in self.subcategories]
        }