from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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
