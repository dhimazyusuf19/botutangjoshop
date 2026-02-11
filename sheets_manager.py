import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List, Dict
import logging
from datetime import datetime

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
            # Create Tingkat 1-4 sheets
            tingkat_headers = ['Tanggal', 'Nama', 'Barang', 'Jumlah', 'Harga Satuan', 'Total']
            
            for tingkat_num in range(1, 5):
                sheet_name = f'Tingkat {tingkat_num}'
                try:
                    tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
                except gspread.WorksheetNotFound:
                    tingkat_sheet = self.spreadsheet.add_worksheet(
                        title=sheet_name, rows=1000, cols=6
                    )
                
                # Check if headers exist
                if not tingkat_sheet.row_values(1):
                    tingkat_sheet.append_row(tingkat_headers)
                    # Format header with blue background
                    tingkat_sheet.format('A1:F1', {
                        'textFormat': {'bold': True},
                        'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.8}
                    })
                    logger.info(f"Created sheet: {sheet_name}")
            
            # Create History sheet
            history_headers = ['Tanggal Lunas', 'Tingkat', 'Tanggal Transaksi', 'Nama', 'Total']
            try:
                history_sheet = self.spreadsheet.worksheet('History')
            except gspread.WorksheetNotFound:
                history_sheet = self.spreadsheet.add_worksheet(
                    title='History', rows=1000, cols=5
                )
            
            # Check if headers exist
            if not history_sheet.row_values(1):
                history_sheet.append_row(history_headers)
                # Format header with gray background
                history_sheet.format('A1:E1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}
                })
                logger.info("Created History sheet")
            
            logger.info("Sheets initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing sheets: {e}")
            raise
    
    def add_transaction(self, data: Dict):
        """Add transaction to spreadsheet with auto-merge logic"""
        try:
            tingkat = data['tingkat']
            nama = data['nama']
            sheet_name = f'Tingkat {tingkat}'
            tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
            
            # Get all records to check for existing customer
            records = tingkat_sheet.get_all_records()
            
            # Check if customer already exists (case-insensitive)
            existing_row_idx = None
            existing_record = None
            for idx, record in enumerate(records, start=2):  # Start from row 2 (after header)
                if record['Nama'].lower() == nama.lower():
                    existing_row_idx = idx
                    existing_record = record
                    break
            
            if existing_row_idx:
                # Customer exists - MERGE transaction
                existing_total = int(existing_record['Total'])
                new_total = existing_total + data['total']
                
                # Update existing row
                tingkat_sheet.update_cell(existing_row_idx, 1, data['tanggal'])  # Tanggal
                tingkat_sheet.update_cell(existing_row_idx, 3, 'Multiple')       # Barang
                tingkat_sheet.update_cell(existing_row_idx, 4, '-')              # Jumlah
                tingkat_sheet.update_cell(existing_row_idx, 5, '-')              # Harga Satuan
                tingkat_sheet.update_cell(existing_row_idx, 6, new_total)        # Total
                
                logger.info(f"Transaction MERGED for {nama} in {sheet_name}: {existing_total} + {data['total']} = {new_total}")
            else:
                # New customer - ADD new row
                row = [
                    data['tanggal'],
                    nama,
                    data['barang'],
                    data['jumlah'],
                    data['harga_satuan'],
                    data['total']
                ]
                
                tingkat_sheet.append_row(row)
                logger.info(f"New transaction added for {nama} in {sheet_name}")
            
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            raise
    
    def get_total_debt(self, nama: str, tingkat: int = None) -> int:
        """Get total debt for a customer, optionally filtered by tingkat"""
        try:
            total = 0
            
            if tingkat:
                # Get debt from specific tingkat only
                sheet_name = f'Tingkat {tingkat}'
                tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
                records = tingkat_sheet.get_all_records()
                
                for record in records:
                    if record['Nama'].lower() == nama.lower():
                        total += int(record['Total'])
            else:
                # Get debt from all tingkat sheets
                for tingkat_num in range(1, 5):
                    sheet_name = f'Tingkat {tingkat_num}'
                    try:
                        tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
                        records = tingkat_sheet.get_all_records()
                        
                        for record in records:
                            if record['Nama'].lower() == nama.lower():
                                total += int(record['Total'])
                    except gspread.WorksheetNotFound:
                        continue
            
            return total
            
        except Exception as e:
            logger.error(f"Error getting total debt: {e}")
            raise
    
    def get_unpaid_customers(self, tingkat: int = None) -> List[Dict]:
        """Get list of customers with unpaid debt, optionally filtered by tingkat"""
        try:
            customers_debt = {}
            
            # Determine which tingkat sheets to check
            tingkat_range = [tingkat] if tingkat else range(1, 5)
            
            for tingkat_num in tingkat_range:
                sheet_name = f'Tingkat {tingkat_num}'
                try:
                    tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
                    records = tingkat_sheet.get_all_records()
                    
                    for record in records:
                        nama = record['Nama']
                        total = int(record['Total'])
                        
                        # Create unique key with tingkat
                        key = f"{nama}_{tingkat_num}"
                        if key not in customers_debt:
                            customers_debt[key] = {
                                'nama': nama,
                                'tingkat': tingkat_num,
                                'total': total
                            }
                except gspread.WorksheetNotFound:
                    continue
            
            # Convert to list and sort
            result = list(customers_debt.values())
            return sorted(result, key=lambda x: (x['tingkat'], x['nama']))
            
        except Exception as e:
            logger.error(f"Error getting unpaid customers: {e}")
            raise
    
    def mark_as_paid(self, nama: str, tingkat: int):
        """Delete row from tingkat sheet and backup to History"""
        try:
            sheet_name = f'Tingkat {tingkat}'
            tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
            records = tingkat_sheet.get_all_records()
            
            # Find the customer row
            for idx, record in enumerate(records, start=2):  # Start from row 2 (after header)
                if record['Nama'].lower() == nama.lower():
                    # Get transaction data
                    tanggal_transaksi = record['Tanggal']
                    total = record['Total']
                    
                    # Backup to History sheet
                    tanggal_lunas = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    history_sheet = self.spreadsheet.worksheet('History')
                    history_row = [
                        tanggal_lunas,
                        tingkat,
                        tanggal_transaksi,
                        nama,
                        total
                    ]
                    history_sheet.append_row(history_row)
                    
                    # Delete row from tingkat sheet
                    tingkat_sheet.delete_rows(idx)
                    
                    logger.info(f"Payment processed for {nama} in {sheet_name}: Rp {total:,} - Row deleted and backed up to History")
                    return
            
            logger.warning(f"Customer {nama} not found in {sheet_name}")
            
        except Exception as e:
            logger.error(f"Error marking as paid: {e}")
            raise
    
    def get_stats(self) -> Dict:
        """Get statistics for all tingkat sheets"""
        try:
            stats = {
                'tingkat': {},
                'grand_total': 0,
                'total_customers': 0,
                'total_transactions': 0
            }
            
            for tingkat_num in range(1, 5):
                sheet_name = f'Tingkat {tingkat_num}'
                try:
                    tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
                    records = tingkat_sheet.get_all_records()
                    
                    # Calculate stats for this tingkat
                    total_debt = sum(int(record['Total']) for record in records)
                    num_customers = len(records)
                    num_transactions = num_customers  # 1 customer = 1 row
                    
                    stats['tingkat'][tingkat_num] = {
                        'total_debt': total_debt,
                        'num_customers': num_customers,
                        'num_transactions': num_transactions
                    }
                    
                    stats['grand_total'] += total_debt
                    stats['total_customers'] += num_customers
                    stats['total_transactions'] += num_transactions
                    
                except gspread.WorksheetNotFound:
                    stats['tingkat'][tingkat_num] = {
                        'total_debt': 0,
                        'num_customers': 0,
                        'num_transactions': 0
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise
    
    def import_data(self, tingkat: int, csv_content: str) -> Dict:
        """Import CSV data with auto-merge logic"""
        try:
            import csv
            from io import StringIO
            
            sheet_name = f'Tingkat {tingkat}'
            tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
            
            # Parse CSV
            csv_reader = csv.DictReader(StringIO(csv_content))
            
            imported_count = 0
            merged_count = 0
            skipped_count = 0
            
            for row in csv_reader:
                try:
                    # Handle both lowercase and titlecase headers
                    nama = row.get('Nama') or row.get('nama', '').strip()
                    barang = row.get('Barang') or row.get('barang', '').strip()
                    tanggal = row.get('Tanggal') or row.get('tanggal', '').strip()
                    jumlah = row.get('Jumlah') or row.get('jumlah', '').strip()
                    harga_satuan = row.get('Harga Satuan') or row.get('harga satuan', '').strip()
                    total = row.get('Total') or row.get('total', '').strip()
                    
                    if not nama or not total:
                        skipped_count += 1
                        logger.warning(f"Skipping invalid row: {row}")
                        continue
                    
                    # Convert numeric values
                    try:
                        total = int(total)
                        if jumlah and jumlah != '-':
                            jumlah = int(jumlah)
                        if harga_satuan and harga_satuan != '-':
                            harga_satuan = int(harga_satuan)
                    except ValueError:
                        skipped_count += 1
                        logger.warning(f"Invalid numeric values in row: {row}")
                        continue
                    
                    # Check if customer exists (for auto-merge)
                    records = tingkat_sheet.get_all_records()
                    existing_row_idx = None
                    existing_record = None
                    
                    for idx, record in enumerate(records, start=2):
                        if record['Nama'].lower() == nama.lower():
                            existing_row_idx = idx
                            existing_record = record
                            break
                    
                    if existing_row_idx:
                        # Merge with existing
                        existing_total = int(existing_record['Total'])
                        new_total = existing_total + total
                        
                        tingkat_sheet.update_cell(existing_row_idx, 1, tanggal)
                        tingkat_sheet.update_cell(existing_row_idx, 3, 'Multiple')
                        tingkat_sheet.update_cell(existing_row_idx, 4, '-')
                        tingkat_sheet.update_cell(existing_row_idx, 5, '-')
                        tingkat_sheet.update_cell(existing_row_idx, 6, new_total)
                        
                        merged_count += 1
                        logger.info(f"Merged import for {nama}: {existing_total} + {total} = {new_total}")
                    else:
                        # Add new row
                        new_row = [tanggal, nama, barang, jumlah, harga_satuan, total]
                        tingkat_sheet.append_row(new_row)
                        imported_count += 1
                        logger.info(f"Imported new customer: {nama}")
                    
                except Exception as e:
                    skipped_count += 1
                    logger.warning(f"Error processing row: {row}, Error: {e}")
                    continue
            
            return {
                'imported': imported_count,
                'merged': merged_count,
                'skipped': skipped_count,
                'total': imported_count + merged_count
            }
            
        except Exception as e:
            logger.error(f"Error importing data: {e}")
            raise
    
    def export_data(self, tingkat: int) -> str:
        """Export tingkat sheet data to CSV format"""
        try:
            sheet_name = f'Tingkat {tingkat}'
            tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
            
            # Get all values including headers
            all_values = tingkat_sheet.get_all_values()
            
            if not all_values:
                return ""
            
            # Convert to CSV format
            import csv
            from io import StringIO
            
            output = StringIO()
            csv_writer = csv.writer(output)
            
            for row in all_values:
                csv_writer.writerow(row)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            raise
