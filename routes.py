import os
import uuid
from io import BytesIO
from datetime import datetime
from collections import defaultdict

import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from sqlalchemy import extract, func

from models import db, Transaction, MonthlyReport
from utils import parse_excel, CATEGORY_KEYWORDS

bp = Blueprint('main', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('main.index'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('main.index'))

    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload .xlsx, .xls, or .csv files.', 'error')
        return redirect(url_for('main.index'))

    filename = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        transactions = parse_excel(filepath)
        if not transactions:
            flash('No transactions found in the file. Please check the format.', 'error')
            return redirect(url_for('main.index'))

        # Group transactions by year-month to detect which months are in the file
        months_in_file = set()
        for txn in transactions:
            months_in_file.add((txn['date'].year, txn['date'].month))

        # Check for finalized months
        finalized_months = []
        for year, month in months_in_file:
            report = MonthlyReport.query.filter_by(year=year, month=month, status='finalized').first()
            if report:
                finalized_months.append(f"{_month_name(month)} {year}")

        if finalized_months:
            flash(f'Cannot upload: {", ".join(finalized_months)} already finalized. Unfinalize first to re-upload.', 'error')
            return redirect(url_for('main.index'))

        # Delete existing transactions for these months (prevents duplicates)
        replaced_count = 0
        for year, month in months_in_file:
            existing = Transaction.query.filter(
                extract('year', Transaction.date) == year,
                extract('month', Transaction.date) == month,
            ).all()
            replaced_count += len(existing)
            for e in existing:
                db.session.delete(e)

        # Insert new transactions
        batch_id = uuid.uuid4().hex[:12]
        for txn in transactions:
            record = Transaction(
                date=txn['date'],
                description=txn['description'],
                amount=txn['amount'],
                txn_type=txn['txn_type'],
                category=txn['category'],
                upload_batch=batch_id,
            )
            db.session.add(record)

        # Create/update monthly reports as draft
        for year, month in months_in_file:
            report = MonthlyReport.query.filter_by(year=year, month=month).first()
            if not report:
                report = MonthlyReport(year=year, month=month, status='draft')
                db.session.add(report)
            else:
                report.status = 'draft'
                report.finalized_at = None

        db.session.commit()

        msg = f'Successfully uploaded {len(transactions)} transactions.'
        if replaced_count > 0:
            msg += f' Replaced {replaced_count} existing transactions.'
        flash(msg, 'success')

    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('main.index'))
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    return redirect(url_for('main.dashboard'))


@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@bp.route('/api/monthly-summary')
def monthly_summary():
    # Optional filters
    filter_year = request.args.get('year', type=int)
    filter_month = request.args.get('month', type=int)

    query = db.session.query(
        extract('year', Transaction.date).label('year'),
        extract('month', Transaction.date).label('month'),
        Transaction.txn_type,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count'),
    )

    if filter_year:
        query = query.filter(extract('year', Transaction.date) == filter_year)
    if filter_month:
        query = query.filter(extract('month', Transaction.date) == filter_month)

    results = (
        query
        .group_by('year', 'month', Transaction.txn_type)
        .order_by('year', 'month')
        .all()
    )

    # Get report statuses
    report_statuses = {}
    reports = MonthlyReport.query.all()
    for r in reports:
        report_statuses[(r.year, r.month)] = r.status

    summary = {}
    for row in results:
        key = f"{int(row.year)}-{int(row.month):02d}"
        if key not in summary:
            summary[key] = {
                'year': int(row.year),
                'month': int(row.month),
                'credit': 0, 'debit': 0,
                'credit_count': 0, 'debit_count': 0,
                'status': report_statuses.get((int(row.year), int(row.month)), 'draft'),
            }
        summary[key][row.txn_type] = round(row.total, 2)
        summary[key][f'{row.txn_type}_count'] = row.count

    data = sorted(summary.values(), key=lambda x: (x['year'], x['month']))
    return jsonify(data)


@bp.route('/api/available-periods')
def available_periods():
    """Returns all years and months that have data, for filter dropdowns."""
    results = (
        db.session.query(
            extract('year', Transaction.date).label('year'),
            extract('month', Transaction.date).label('month'),
        )
        .distinct()
        .order_by('year', 'month')
        .all()
    )

    years = sorted(set(int(r.year) for r in results))
    months = sorted(set(int(r.month) for r in results))

    return jsonify({'years': years, 'months': months})


@bp.route('/api/transactions/<int:year>/<int:month>/<txn_type>')
def get_transactions(year, month, txn_type):
    if txn_type not in ('credit', 'debit'):
        return jsonify({'error': 'Invalid transaction type'}), 400

    transactions = (
        Transaction.query
        .filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month,
            Transaction.txn_type == txn_type,
        )
        .order_by(Transaction.date)
        .all()
    )

    category_summary = {}
    for txn in transactions:
        if txn.category not in category_summary:
            category_summary[txn.category] = 0
        category_summary[txn.category] = round(category_summary[txn.category] + txn.amount, 2)

    return jsonify({
        'transactions': [t.to_dict() for t in transactions],
        'category_summary': category_summary,
        'total': round(sum(t.amount for t in transactions), 2),
    })


@bp.route('/api/categories')
def get_categories():
    credit_cats = list(CATEGORY_KEYWORDS['credit'].keys()) + ['Owner/Promoter Funds', 'Other Income']
    debit_cats = list(CATEGORY_KEYWORDS['debit'].keys()) + ['General Payment']
    credit_cats = list(dict.fromkeys(credit_cats))
    debit_cats = list(dict.fromkeys(debit_cats))
    return jsonify({'credit': credit_cats, 'debit': debit_cats})


@bp.route('/api/transactions/<int:txn_id>/category', methods=['PUT'])
def update_category(txn_id):
    txn = Transaction.query.get(txn_id)
    if not txn:
        return jsonify({'error': 'Transaction not found'}), 404

    # Check if month is finalized
    report = MonthlyReport.query.filter_by(
        year=txn.date.year, month=txn.date.month, status='finalized'
    ).first()
    if report:
        return jsonify({'error': 'This month is finalized. Unfinalize to make changes.'}), 400

    data = request.get_json()
    new_category = data.get('category', '').strip()
    if not new_category:
        return jsonify({'error': 'Category is required'}), 400

    txn.category = new_category
    db.session.commit()
    return jsonify({'success': True, 'transaction': txn.to_dict()})


@bp.route('/api/monthly-report/<int:year>/<int:month>/finalize', methods=['POST'])
def finalize_month(year, month):
    report = MonthlyReport.query.filter_by(year=year, month=month).first()
    if not report:
        report = MonthlyReport(year=year, month=month)
        db.session.add(report)

    report.status = 'finalized'
    report.finalized_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'report': report.to_dict()})


@bp.route('/api/monthly-report/<int:year>/<int:month>/unfinalize', methods=['POST'])
def unfinalize_month(year, month):
    report = MonthlyReport.query.filter_by(year=year, month=month).first()
    if not report:
        return jsonify({'error': 'Report not found'}), 404

    report.status = 'draft'
    report.finalized_at = None
    db.session.commit()

    return jsonify({'success': True, 'report': report.to_dict()})


@bp.route('/export')
def export():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    txn_type = request.args.get('type')

    query = Transaction.query
    if year:
        query = query.filter(extract('year', Transaction.date) == year)
    if month:
        query = query.filter(extract('month', Transaction.date) == month)
    if txn_type in ('credit', 'debit'):
        query = query.filter(Transaction.txn_type == txn_type)

    transactions = query.order_by(Transaction.date).all()
    if not transactions:
        flash('No transactions to export.', 'error')
        return redirect(url_for('main.dashboard'))

    data = [t.to_dict() for t in transactions]
    df = pd.DataFrame(data)
    df.columns = ['ID', 'Date', 'Description', 'Amount', 'Type', 'Category', 'Upload Batch']

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    filename = f"expenses_{year or 'all'}_{month or 'all'}_{txn_type or 'all'}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def _month_name(month):
    names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return names[month - 1]
