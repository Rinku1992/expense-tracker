import pandas as pd
from datetime import datetime

CATEGORY_KEYWORDS = {
    'credit': {
        'Owner/Promoter Funds': [
            'neeru', 'ravikant', 'kusum', 'suryakan', 'nrtokas',
            'ravidhanke', 'ankit suhag', 'ankita suhag', 'the forno',
        ],
        'Cheque Deposit': [
            'credit-chq', 'chq', 'cheque',
        ],
        'Association/CMAI': [
            'cmai', 'garment f', 'association', 'federation',
        ],
        'Interest & Dividend': [
            'interest', 'dividend', 'bonus', 'int.on',
        ],
        'Refund': [
            'refund', 'cashback', 'reversal', 'reimburse',
        ],
        # Customer Payment must be LAST - it's the catch-all for UPI/IMPS/NEFT credits
        'Customer Payment': [
            'upi/cr', 'imps', 'neft', 'rtgs', 'transfer',
        ],
    },
    'debit': {
        'Supplier & Vendor': [
            'textile', 'agency', 'fabrics', 'fabric', 'trader', 'enterprise', 'industries',
            'dori', 'pate', 'shiv textile', 'supplier', 'vendor', 'wholesale', 'merchant',
            'manufacturing', 'mills', 'exports', 'imports', 'garment', 'cloth',
            'embroid', 'stitch', 'thread', 'lace', 'button', 'zip',
        ],
        'Logistics & Transport': [
            'uber', 'ola', 'cab', 'taxi', 'petr', 'petrol', 'diesel', 'fuel',
            'transport', 'courier', 'freight', 'shipping', 'delivery', 'delhivery',
            'bluedart', 'dtdc', 'fedex', 'cargo', 'logistics', 'travel',
            'flight', 'train', 'irctc', 'hotel', 'booking',
        ],
        'Business Payment': [
            'vyapar', 'payment', 'business',
        ],
        'Membership & Fees': [
            'cmai', 'association', 'membership', 'federation', 'chamber', 'guild',
        ],
        'Salary & Staff': [
            'salary', 'wages', 'staff', 'employee', 'pf', 'esic', 'gratuity',
        ],
        'Rent & Property': [
            'rent', 'lease', 'property', 'housing', 'maintenance',
        ],
        'Utilities': [
            'electricity', 'water', 'gas', 'bill', 'broadband', 'internet',
            'phone', 'mobile', 'recharge', 'airtel', 'jio', 'bsnl',
        ],
        'Tax & Compliance': [
            'gst', 'tax', 'tds', 'compliance', 'govt', 'government', 'income tax',
            'customs', 'duty', 'cess',
        ],
        'Bank Charges': [
            'charges', 'fee', 'commission', 'penalty', 'bank charge', 'service charge',
            'sms alert', 'debit card', 'annual fee',
        ],
        'EMI & Loans': [
            'emi', 'loan', 'mortgage', 'installment',
        ],
        'Insurance': [
            'insurance', 'lic', 'policy', 'premium',
        ],
        'Food & Dining': [
            'swiggy', 'zomato', 'restaurant', 'food', 'dining', 'cafe', 'coffee',
        ],
        'Shopping': [
            'amazon', 'flipkart', 'myntra', 'shopping', 'store', 'mall',
        ],
        'ATM Withdrawal': [
            'atm', 'withdrawal', 'cash',
        ],
    },
}


OWNER_PROMOTER_KEYWORDS = [
    'neeru', 'ravikant', 'kusum', 'suryakan', 'nrtokas',
    'ravidhanke', 'ankit suhag', 'ankita suhag', 'the forno',
]


def _extract_payee_info(description):
    """Extract payee name and keywords from bank description formats."""
    desc = description.strip()
    parts_combined = desc.lower()

    # UPI format: TO TRANSFER-UPI/DR/{txn_id}/{PAYEE}/{BANK}/{upi_handle}/{keyword}--
    if 'upi/' in parts_combined:
        segments = desc.split('/')
        payee = ''
        keyword = ''
        if len(segments) >= 4:
            payee = segments[3].strip()
        if len(segments) >= 6:
            keyword = segments[5].strip().split('--')[0].strip()
        return f"{payee} {keyword}".strip()

    # Cheque clearing: TO CLEARING-Chq {no} Sess {n} {PAYEE_NAME} {account}--{chq}
    if 'clearing' in parts_combined and 'chq' in parts_combined:
        import re
        match = re.search(r'sess\s+\d+\s+(.+?)(?:\s{2,}|\s+\d{5,}|--)', desc, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # NEFT/RTGS/IMPS: extract payee name after common patterns
    if any(kw in parts_combined for kw in ['neft', 'rtgs', 'imps']):
        segments = desc.split('/')
        if len(segments) >= 3:
            return segments[2].strip().split('--')[0].strip()

    return desc


def _is_owner_promoter(description):
    """Check if a credit transaction is from an owner/promoter.
    For UPI: check the 4th segment (payee name).
    For IMPS: check the 3rd segment.
    For others: check full description.
    """
    desc = description.strip()
    desc_lower = desc.lower()

    segment_to_check = ''

    # UPI: BY TRANSFER-UPI/CR/{txn_id}/{PAYEE}/{BANK}/{upi_handle}/{keyword}--
    # Segments: [0]BY TRANSFER-UPI [1]CR [2]txn_id [3]PAYEE [4]BANK [5]upi_handle ...
    if 'upi/' in desc_lower:
        segments = desc.split('/')
        if len(segments) >= 4:
            segment_to_check = segments[3].strip().lower()  # 4th segment = payee

    # IMPS: BY TRANSFER-IMPS/{txn_id}/{name-info}/IMPS--
    # Segments: [0]BY TRANSFER-IMPS [1]txn_id [2]name-info ...
    elif 'imps' in desc_lower:
        segments = desc.split('/')
        if len(segments) >= 3:
            segment_to_check = segments[2].strip().lower()  # 3rd segment = name

    # NEFT or others: check full description
    else:
        segment_to_check = desc_lower

    if segment_to_check:
        return any(kw in segment_to_check for kw in OWNER_PROMOTER_KEYWORDS)
    return False


def detect_category(description, txn_type):
    desc_lower = description.lower()

    # For credits: first check if it's an owner/promoter using segment-based logic
    if txn_type == 'credit':
        if _is_owner_promoter(description):
            return 'Owner/Promoter Funds'

    # Extract payee info for general keyword matching
    payee_info = _extract_payee_info(description).lower()
    search_text = f"{payee_info} {desc_lower}"

    categories = CATEGORY_KEYWORDS.get(txn_type, {})
    for category, keywords in categories.items():
        # Skip Owner/Promoter Funds in keyword matching - handled above
        if category == 'Owner/Promoter Funds':
            continue
        if any(kw in search_text for kw in keywords):
            return category
    return 'General Payment' if txn_type == 'debit' else 'Other Income'


def parse_excel(file_path):
    ext = file_path.rsplit('.', 1)[-1].lower()

    if ext == 'csv':
        # Try comma-separated first, then tab-separated, then auto-detect
        for sep in [',', '\t', None]:
            try:
                if sep is None:
                    df = pd.read_csv(file_path, sep=sep, engine='python')
                else:
                    df = pd.read_csv(file_path, sep=sep)
                # Check if we got more than 1 column (valid parse)
                if len(df.columns) > 1:
                    break
            except Exception:
                continue
        else:
            df = pd.read_csv(file_path)
    elif ext == 'xlsx':
        df = pd.read_excel(file_path, engine='openpyxl')
    elif ext == 'xls':
        df = pd.read_excel(file_path, engine='xlrd')
    else:
        df = pd.read_excel(file_path, engine='openpyxl')

    # Clean column names: strip whitespace, drop unnamed/empty columns
    df.columns = [str(col).strip().lower() for col in df.columns]
    df = df.loc[:, ~df.columns.str.startswith('unnamed')]
    df = df.loc[:, df.columns != '']

    # Drop completely empty rows
    df = df.dropna(how='all')

    col_map = _detect_columns(df)
    if not col_map:
        raise ValueError(
            f"Could not detect required columns. "
            f"Found columns: {list(df.columns)}. "
            f"Please ensure your file has columns for: date, description, and credit/debit amounts."
        )

    transactions = []
    for _, row in df.iterrows():
        date_val = _parse_date(row[col_map['date']])
        if date_val is None:
            continue

        description = str(row[col_map['description']]).strip()
        if not description or description == 'nan':
            continue

        if 'credit_amount' in col_map and 'debit_amount' in col_map:
            credit = _to_float(row.get(col_map['credit_amount'], 0))
            debit = _to_float(row.get(col_map['debit_amount'], 0))
            if credit > 0:
                txn_type = 'credit'
                amount = credit
            elif debit > 0:
                txn_type = 'debit'
                amount = debit
            else:
                continue
        elif 'amount' in col_map:
            amount = _to_float(row[col_map['amount']])
            if amount == 0:
                continue
            if 'type' in col_map:
                type_val = str(row[col_map['type']]).strip().lower()
                txn_type = 'credit' if type_val in ('credit', 'cr', 'c') else 'debit'
                amount = abs(amount)
            else:
                txn_type = 'credit' if amount > 0 else 'debit'
                amount = abs(amount)
        else:
            continue

        category = detect_category(description, txn_type)
        transactions.append({
            'date': date_val,
            'description': description,
            'amount': round(amount, 2),
            'txn_type': txn_type,
            'category': category,
        })

    return transactions


def _detect_columns(df):
    col_map = {}
    columns = list(df.columns)

    date_keywords = ['txn date', 'transaction date', 'value date', 'posting date', 'date']
    desc_keywords = ['description', 'narration', 'particulars', 'details', 'remarks', 'transaction details']
    amount_keywords = ['amount', 'txn amount', 'transaction amount']
    credit_keywords = ['credit', 'credit amount', 'deposit']
    debit_keywords = ['debit', 'debit amount', 'withdrawal']
    type_keywords = ['type', 'txn type', 'transaction type', 'cr/dr']

    for col in columns:
        col_lower = col.strip().lower()
        if not col_map.get('date') and any(kw in col_lower for kw in date_keywords):
            col_map['date'] = col
        if not col_map.get('description') and any(kw in col_lower for kw in desc_keywords):
            col_map['description'] = col
        if not col_map.get('amount') and col_lower in amount_keywords:
            col_map['amount'] = col
        if not col_map.get('credit_amount') and col_lower in credit_keywords:
            col_map['credit_amount'] = col
        if not col_map.get('debit_amount') and col_lower in debit_keywords:
            col_map['debit_amount'] = col
        if not col_map.get('type') and any(kw in col_lower for kw in type_keywords):
            col_map['type'] = col

    if 'date' not in col_map or 'description' not in col_map:
        return None
    if 'amount' not in col_map and ('credit_amount' not in col_map or 'debit_amount' not in col_map):
        return None

    return col_map


def _parse_date(val):
    if pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, pd.Timestamp):
        return val.date()
    val_str = str(val).strip()
    # Try multiple date formats including 2-digit year
    for fmt in ('%d-%b-%y', '%d-%b-%Y', '%d/%m/%y', '%d/%m/%Y',
                '%Y-%m-%d', '%d-%m-%Y', '%d-%m-%y', '%m/%d/%Y',
                '%d %b %Y', '%d %b %y', '%d-%B-%Y', '%d-%B-%y'):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(val):
    if pd.isna(val):
        return 0.0
    try:
        return float(str(val).replace(',', '').replace(' ', ''))
    except (ValueError, TypeError):
        return 0.0
