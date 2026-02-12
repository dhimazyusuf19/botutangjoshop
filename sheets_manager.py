import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SheetsManager:
    """Manager for Google Sheets operations"""
    
    # Column indices for tingkat sheets (1-based for gspread)
    TOTAL_COLUMN_INDEX = 6
    
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
    
    def initialize_keuangan_sheet(self):
        """Initialize Keuangan sheet for financial transactions"""
        try:
            keuangan_headers = ['Tanggal', 'Tipe', 'Keterangan', 'Debit', 'Kredit', 'Saldo']
            
            try:
                keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            except gspread.WorksheetNotFound:
                keuangan_sheet = self.spreadsheet.add_worksheet(
                    title='Keuangan', rows=1000, cols=6
                )
            
            # Check if headers exist
            if not keuangan_sheet.row_values(1):
                keuangan_sheet.append_row(keuangan_headers)
                # Format header with green background
                keuangan_sheet.format('A1:F1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.2, 'green': 0.8, 'blue': 0.4}
                })
                logger.info("Created Keuangan sheet")
            
        except Exception as e:
            logger.error(f"Error initializing Keuangan sheet: {e}")
            raise
    
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
            
            # Create Keuangan sheet
            self.initialize_keuangan_sheet()
            
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
    
    def mark_as_paid(self, nama: str, tingkat: int) -> int:
        """Delete row from tingkat sheet, backup to History, and update Keuangan"""
        try:
            sheet_name = f'Tingkat {tingkat}'
            tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
            records = tingkat_sheet.get_all_records()
            
            # Find the customer row
            for idx, record in enumerate(records, start=2):  # Start from row 2 (after header)
                if record['Nama'].lower() == nama.lower():
                    # Get transaction data
                    tanggal_transaksi = record['Tanggal']
                    total = int(record['Total'])
                    
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
                    
                    # Add to Keuangan sheet
                    self.add_pelunasan_to_keuangan(nama, tingkat, total)
                    
                    logger.info(f"Payment processed for {nama} in {sheet_name}: Rp {total:,} - Row deleted, backed up to History, and added to Keuangan")
                    return total
            
            logger.warning(f"Customer {nama} not found in {sheet_name}")
            return 0
            
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
    
    def set_modal_awal(self, jumlah: int) -> bool:
        """Set initial capital (can only be set once)"""
        try:
            keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            records = keuangan_sheet.get_all_records()
            
            # Check if modal already set
            for record in records:
                if record.get('Tipe') == 'Modal Awal':
                    return False
            
            # Add modal awal transaction
            tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row = [tanggal, 'Modal Awal', 'Modal awal usaha', jumlah, 0, jumlah]
            keuangan_sheet.append_row(row)
            
            logger.info(f"Modal awal set to: Rp {jumlah:,}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting modal awal: {e}")
            raise
    
    def get_modal_awal(self) -> int:
        """Get initial capital from first Modal Awal transaction"""
        try:
            keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            records = keuangan_sheet.get_all_records()
            
            for record in records:
                if record.get('Tipe') == 'Modal Awal':
                    return int(record.get('Debit', 0))
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting modal awal: {e}")
            raise
    
    def get_current_saldo(self) -> int:
        """Get current balance from last row in Keuangan sheet"""
        try:
            keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            records = keuangan_sheet.get_all_records()
            
            if not records:
                return 0
            
            # Get saldo from last transaction
            last_record = records[-1]
            return int(last_record.get('Saldo', 0))
            
        except Exception as e:
            logger.error(f"Error getting current saldo: {e}")
            raise
    
    def add_topup(self, jumlah: int):
        """Add top-up transaction"""
        try:
            keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            current_saldo = self.get_current_saldo()
            new_saldo = current_saldo + jumlah
            
            tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row = [tanggal, 'Top-up', 'Tambah modal', jumlah, 0, new_saldo]
            keuangan_sheet.append_row(row)
            
            logger.info(f"Top-up added: Rp {jumlah:,}, New saldo: Rp {new_saldo:,}")
            
        except Exception as e:
            logger.error(f"Error adding topup: {e}")
            raise
    
    def add_penarikan(self, jumlah: int) -> bool:
        """Add withdrawal transaction"""
        try:
            current_saldo = self.get_current_saldo()
            
            # Check if sufficient balance
            if current_saldo < jumlah:
                return False
            
            keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            new_saldo = current_saldo - jumlah
            
            tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row = [tanggal, 'Penarikan', 'Ambil saldo', 0, jumlah, new_saldo]
            keuangan_sheet.append_row(row)
            
            logger.info(f"Penarikan added: Rp {jumlah:,}, New saldo: Rp {new_saldo:,}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding penarikan: {e}")
            raise
    
    def add_pemasukan(self, jumlah: int, keterangan: str = 'Pemasukan cash'):
        """Add cash income transaction"""
        try:
            keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            current_saldo = self.get_current_saldo()
            new_saldo = current_saldo + jumlah
            
            tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row = [tanggal, 'Pemasukan', keterangan, jumlah, 0, new_saldo]
            keuangan_sheet.append_row(row)
            
            logger.info(f"Pemasukan added: Rp {jumlah:,}, Keterangan: {keterangan}, New saldo: Rp {new_saldo:,}")
            
        except Exception as e:
            logger.error(f"Error adding pemasukan: {e}")
            raise
    
    def add_pengeluaran(self, jumlah: int, keterangan: str = 'Pengeluaran operasional') -> bool:
        """Add expense transaction"""
        try:
            current_saldo = self.get_current_saldo()
            
            # Check if sufficient balance
            if current_saldo < jumlah:
                return False
            
            keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            new_saldo = current_saldo - jumlah
            
            tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row = [tanggal, 'Pengeluaran', keterangan, 0, jumlah, new_saldo]
            keuangan_sheet.append_row(row)
            
            logger.info(f"Pengeluaran added: Rp {jumlah:,}, Keterangan: {keterangan}, New saldo: Rp {new_saldo:,}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding pengeluaran: {e}")
            raise
    
    def add_pelunasan_to_keuangan(self, nama: str, tingkat: int, jumlah: int):
        """Add pelunasan transaction to Keuangan"""
        try:
            keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            current_saldo = self.get_current_saldo()
            new_saldo = current_saldo + jumlah
            
            tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            keterangan = f'{nama} - Tingkat {tingkat}'
            row = [tanggal, 'Pelunasan', keterangan, jumlah, 0, new_saldo]
            keuangan_sheet.append_row(row)
            
            logger.info(f"Pelunasan added to Keuangan: {nama}, Tingkat {tingkat}, Rp {jumlah:,}, New saldo: Rp {new_saldo:,}")
            
        except Exception as e:
            logger.error(f"Error adding pelunasan to keuangan: {e}")
            raise
    
    def process_payment(self, nama: str, tingkat: int, jumlah: int) -> Dict:
        """Process payment (partial or full) for a customer"""
        try:
            sheet_name = f'Tingkat {tingkat}'
            tingkat_sheet = self.spreadsheet.worksheet(sheet_name)
            records = tingkat_sheet.get_all_records()
            
            # Find the customer row
            customer_found = False
            for idx, record in enumerate(records, start=2):  # Start from row 2 (after header)
                if record['Nama'].lower() == nama.lower():
                    customer_found = True
                    current_debt = int(record['Total'])
                    
                    # Validate payment amount
                    if jumlah > current_debt:
                        return {
                            'success': False,
                            'error': 'exceeds_debt',
                            'current_debt': current_debt,
                            'payment': jumlah
                        }
                    
                    # Calculate remaining debt
                    sisa_utang = current_debt - jumlah
                    saldo_sebelum = self.get_current_saldo()
                    
                    if sisa_utang == 0:
                        # Full payment - DELETE row and backup to History
                        tanggal_transaksi = record['Tanggal']
                        tanggal_lunas = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Backup to History
                        history_sheet = self.spreadsheet.worksheet('History')
                        history_row = [tanggal_lunas, tingkat, tanggal_transaksi, nama, current_debt]
                        history_sheet.append_row(history_row)
                        
                        # Delete row from tingkat sheet
                        tingkat_sheet.delete_rows(idx)
                        
                        # Add to Keuangan as Pelunasan
                        keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
                        new_saldo = saldo_sebelum + jumlah
                        keterangan = f'{nama} - Tingkat {tingkat}'
                        keuangan_row = [tanggal_lunas, 'Pelunasan', keterangan, jumlah, 0, new_saldo]
                        keuangan_sheet.append_row(keuangan_row)
                        
                        logger.info(f"Full payment processed: {nama}, Tingkat {tingkat}, Rp {jumlah:,}")
                        
                        return {
                            'success': True,
                            'is_full_payment': True,
                            'nama': nama,
                            'tingkat': tingkat,
                            'payment': jumlah,
                            'previous_debt': current_debt,
                            'remaining_debt': 0,
                            'saldo_sebelum': saldo_sebelum,
                            'saldo_sekarang': new_saldo
                        }
                    else:
                        # Partial payment - UPDATE Total column
                        tingkat_sheet.update_cell(idx, self.TOTAL_COLUMN_INDEX, sisa_utang)
                        
                        # Add to Keuangan as Pembayaran Cicilan
                        keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
                        new_saldo = saldo_sebelum + jumlah
                        tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        keterangan = f'{nama} - Tingkat {tingkat} (Rp {jumlah:,} dari Rp {current_debt:,})'
                        keuangan_row = [tanggal, 'Pembayaran Cicilan', keterangan, jumlah, 0, new_saldo]
                        keuangan_sheet.append_row(keuangan_row)
                        
                        logger.info(f"Partial payment processed: {nama}, Tingkat {tingkat}, Rp {jumlah:,}, Remaining: Rp {sisa_utang:,}")
                        
                        return {
                            'success': True,
                            'is_full_payment': False,
                            'nama': nama,
                            'tingkat': tingkat,
                            'payment': jumlah,
                            'previous_debt': current_debt,
                            'remaining_debt': sisa_utang,
                            'saldo_sebelum': saldo_sebelum,
                            'saldo_sekarang': new_saldo
                        }
            
            # Customer not found
            if not customer_found:
                return {
                    'success': False,
                    'error': 'not_found',
                    'nama': nama,
                    'tingkat': tingkat
                }
            
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            raise
    
    def get_keuangan_summary(self) -> Dict:
        """Return summary for financial dashboard"""
        try:
            keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            records = keuangan_sheet.get_all_records()
            
            current_saldo = self.get_current_saldo()
            modal_awal = self.get_modal_awal()
            profit = current_saldo - modal_awal
            
            # Calculate totals by type
            total_pelunasan = 0
            total_cicilan = 0
            total_pemasukan = 0
            total_pengeluaran_ops = 0
            total_penarikan = 0
            
            for record in records:
                tipe = record.get('Tipe', '')
                debit = int(record.get('Debit', 0))
                kredit = int(record.get('Kredit', 0))
                
                if tipe == 'Pelunasan':
                    total_pelunasan += debit
                elif tipe == 'Pembayaran Cicilan':
                    total_cicilan += debit
                elif tipe == 'Pemasukan':
                    total_pemasukan += debit
                elif tipe == 'Pengeluaran':
                    total_pengeluaran_ops += kredit
                elif tipe == 'Penarikan':
                    total_penarikan += kredit
            
            total_pendapatan = total_pelunasan + total_cicilan + total_pemasukan
            total_pengeluaran = total_pengeluaran_ops + total_penarikan
            
            return {
                'saldo': current_saldo,
                'modal_awal': modal_awal,
                'profit': profit,
                'total_pelunasan': total_pelunasan,
                'total_cicilan': total_cicilan,
                'total_pemasukan': total_pemasukan,
                'total_pendapatan': total_pendapatan,
                'total_pengeluaran_ops': total_pengeluaran_ops,
                'total_penarikan': total_penarikan,
                'total_pengeluaran': total_pengeluaran
            }
            
        except Exception as e:
            logger.error(f"Error getting keuangan summary: {e}")
            raise
    
    def get_keuangan_history(self, limit: int = 10) -> List[Dict]:
        """Get last N transactions from Keuangan sheet"""
        try:
            keuangan_sheet = self.spreadsheet.worksheet('Keuangan')
            records = keuangan_sheet.get_all_records()
            
            # Get last N records (newest first)
            last_records = list(reversed(records[-limit:]))
            
            # Format records
            history = []
            for record in last_records:
                history.append({
                    'tanggal': record.get('Tanggal', ''),
                    'tipe': record.get('Tipe', ''),
                    'keterangan': record.get('Keterangan', ''),
                    'debit': int(record.get('Debit', 0)),
                    'kredit': int(record.get('Kredit', 0)),
                    'saldo': int(record.get('Saldo', 0))
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting keuangan history: {e}")
            raise
    
    def add_debt_quick(self, tingkat: int, nama: str, jumlah: int):
        """Quick add debt without going through full flow"""
        try:
            # Use existing add_transaction with auto-merge
            transaction_data = {
                'tanggal': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'tingkat': str(tingkat),
                'nama': nama,
                'barang': 'Quick Entry',
                'jumlah': '-',
                'harga_satuan': '-',
                'total': jumlah
            }
            
            self.add_transaction(transaction_data)
            logger.info(f"Quick debt added: {nama}, Tingkat {tingkat}, Rp {jumlah:,}")
            
        except Exception as e:
            logger.error(f"Error adding quick debt: {e}")
            raise
