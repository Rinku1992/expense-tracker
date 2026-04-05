import os
import tempfile
import pandas as pd
import pytest
from utils import parse_excel, detect_category


class TestDetectCategory:
    def test_salary_credit(self):
        assert detect_category('Monthly Salary Credit', 'credit') == 'Salary'

    def test_swiggy_debit(self):
        assert detect_category('Swiggy order payment', 'debit') == 'Food & Dining'

    def test_amazon_debit(self):
        assert detect_category('Amazon purchase', 'debit') == 'Shopping'

    def test_uber_debit(self):
        assert detect_category('Uber trip', 'debit') == 'Travel'

    def test_unknown_returns_other(self):
        assert detect_category('Random transaction xyz', 'debit') == 'Other'


class TestParseExcel:
    def _create_csv(self, data):
        df = pd.DataFrame(data)
        fd, path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        df.to_csv(path, index=False)
        return path

    def test_parse_csv_with_amount_column(self):
        path = self._create_csv({
            'Date': ['2025-01-15', '2025-01-20'],
            'Description': ['Salary Credit', 'Swiggy order'],
            'Amount': [50000, -500],
        })
        try:
            transactions = parse_excel(path)
            assert len(transactions) == 2
            assert transactions[0]['txn_type'] == 'credit'
            assert transactions[0]['amount'] == 50000
            assert transactions[1]['txn_type'] == 'debit'
            assert transactions[1]['amount'] == 500
        finally:
            os.unlink(path)

    def test_parse_csv_with_separate_credit_debit_columns(self):
        path = self._create_csv({
            'Date': ['2025-01-15', '2025-01-20'],
            'Description': ['Salary', 'Shopping at Amazon'],
            'Credit': [50000, 0],
            'Debit': [0, 2000],
        })
        try:
            transactions = parse_excel(path)
            assert len(transactions) == 2
            assert transactions[0]['txn_type'] == 'credit'
            assert transactions[1]['txn_type'] == 'debit'
            assert transactions[1]['category'] == 'Shopping'
        finally:
            os.unlink(path)

    def test_parse_empty_file(self):
        path = self._create_csv({
            'Date': [],
            'Description': [],
            'Amount': [],
        })
        try:
            transactions = parse_excel(path)
            assert len(transactions) == 0
        finally:
            os.unlink(path)
