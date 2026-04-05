from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class MonthlyReport(db.Model):
    __tablename__ = 'monthly_reports'

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='draft')  # 'draft' or 'finalized'
    finalized_at = db.Column(db.DateTime)

    __table_args__ = (db.UniqueConstraint('year', 'month', name='uq_year_month'),)

    def to_dict(self):
        return {
            'id': self.id,
            'year': self.year,
            'month': self.month,
            'status': self.status,
            'finalized_at': self.finalized_at.isoformat() if self.finalized_at else None,
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    txn_type = db.Column(db.String(10), nullable=False)  # 'credit' or 'debit'
    category = db.Column(db.String(100), default='Other')
    upload_batch = db.Column(db.String(100))

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'description': self.description,
            'amount': self.amount,
            'txn_type': self.txn_type,
            'category': self.category,
            'upload_batch': self.upload_batch,
        }
