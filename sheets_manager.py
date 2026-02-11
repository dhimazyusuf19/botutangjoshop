import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class SheetsManager:
    """Manager for Google Sheets operations"""
    
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.spreadsheet = None
        self._connect()
    
    def _connect(self):
        """Connect to Google Sheets"""
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self.credentials_path, scope
        )
        self.client = gspread.authorize(credentials)
        self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
    
    def initialize_sheets(self):
        """Initialize sheets with headers if not exist"""
        try:
            # Sheet 1: Transaksi
            try:
                transaksi_sheet = self.spreadsheet.worksheet('Transaksi')
            except gspread.WorksheetNotFound:
                transaksi_sheet = self.spreadsheet.add_worksheet(
                    title='Transaksi', rows=1000, cols=8
                )
            
            # Check if headers exist
            if not transaksi_sheet.row_values(1):
                headers = [
                    'Tanggal', 'Tingkat', 'Nama', 'Barang', 
                    'Jumlah', 'Harga Satuan', 'Total', 'Status'
                ]
                transaksi_sheet.append_row(headers)
                # Format header
                transaksi_sheet.format('A1:H1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}
                })
            
            logger.info("Sheets initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing sheets: {e}")
            raise
    
    def add_transaction(self, data: Dict):
        """Add transaction to spreadsheet"""
        try:
            transaksi_sheet = self.spreadsheet.worksheet('Transaksi')
            
            row = [
                data['tanggal'],
                data['tingkat'],
                data['nama'],
                data['barang'],
                data['jumlah'],
                data['harga_satuan'],
                data['total'],
                data['status']
            ]
            
            transaksi_sheet.append_row(row)
            logger.info(f"Transaction added for {data['nama']}")
            
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            raise
    
    def get_total_debt(self, nama: str) -> int:
        """Get total debt for a customer"""
        try:
            transaksi_sheet = self.spreadsheet.worksheet('Transaksi')
            records = transaksi_sheet.get_all_records()
            
            total = 0
            for record in records:
                if record['Nama'].lower() == nama.lower() and record['Status'] == 'Belum Lunas':
                    total += int(record['Total'])
            
            return total
            
        except Exception as e:
            logger.error(f"Error getting total debt: {e}")
            raise
    
    def get_unpaid_customers(self) -> List[Dict]:
        """Get list of customers with unpaid debt"""
        try:
            transaksi_sheet = self.spreadsheet.worksheet('Transaksi')
            records = transaksi_sheet.get_all_records()
            
            # Group by nama
            customers_debt = {}
            for record in records:
                if record['Status'] == 'Belum Lunas':
                    nama = record['Nama']
                    if nama not in customers_debt:
                        customers_debt[nama] = 0
                    customers_debt[nama] += int(record['Total'])
            
            # Convert to list
            result = [
                {'nama': nama, 'total': total}
                for nama, total in customers_debt.items()
            ]
            
            return sorted(result, key=lambda x: x['nama'])
            
        except Exception as e:
            logger.error(f"Error getting unpaid customers: {e}")
            raise
    
    def mark_as_paid(self, nama: str):
        """Mark all transactions for a customer as paid"""
        try:
            transaksi_sheet = self.spreadsheet.worksheet('Transaksi')
            records = transaksi_sheet.get_all_records()
            
            # Find and update rows
            for idx, record in enumerate(records, start=2):  # Start from row 2 (after header)
                if record['Nama'].lower() == nama.lower() and record['Status'] == 'Belum Lunas':
                    transaksi_sheet.update_cell(idx, 8, 'Lunas')  # Column 8 is Status
            
            logger.info(f"Marked transactions as paid for {nama}")
            
        except Exception as e:
            logger.error(f"Error marking as paid: {e}")
            raise
