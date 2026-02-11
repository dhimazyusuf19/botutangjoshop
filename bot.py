import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from config import Config
from sheets_manager import SheetsManager
from datetime import datetime

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
TINGKAT, NAMA, BARANG, JUMLAH = range(4)
IMPORT_TINGKAT, IMPORT_FILE = range(4, 6)

# Data barang
ITEMS = {
    'roti': {'name': 'Roti', 'price': 3000},
    'singkong': {'name': 'Singkong', 'price': 5000},
    'basreng': {'name': 'Basreng', 'price': 7500}
}

class KasirBot:
    def __init__(self):
        self.config = Config()
        self.sheets = SheetsManager(
            self.config.GOOGLE_SHEETS_CREDENTIALS,
            self.config.SPREADSHEET_ID
        )
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - mulai transaksi"""
        keyboard = [
            [InlineKeyboardButton("Tingkat 1", callback_data='tingkat_1')],
            [InlineKeyboardButton("Tingkat 2", callback_data='tingkat_2')],
            [InlineKeyboardButton("Tingkat 3", callback_data='tingkat_3')],
            [InlineKeyboardButton("Tingkat 4", callback_data='tingkat_4')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            '🏪 *Selamat datang di Jo Shop!*\n\n'
            'Pilih tingkat pembeli:',
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return TINGKAT
    
    async def tingkat_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pilihan tingkat"""
        query = update.callback_query
        await query.answer()
        
        tingkat = query.data.split('_')[1]
        context.user_data['tingkat'] = tingkat
        
        await query.edit_message_text(
            f'✅ Tingkat: *{tingkat}*\n\n'
            'Sekarang, masukkan *nama pembeli*:',
            parse_mode='Markdown'
        )
        
        return NAMA
    
    async def nama_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle input nama"""
        nama = update.message.text.strip()
        
        if not nama:
            await update.message.reply_text(
                '❌ Nama tidak boleh kosong. Silakan masukkan nama:'
            )
            return NAMA
        
        context.user_data['nama'] = nama
        
        # Cek total utang yang ada untuk tingkat ini
        try:
            tingkat = int(context.user_data['tingkat'])
            total_utang = self.sheets.get_total_debt(nama, tingkat)
            utang_info = f'\n💰 Total utang saat ini (Tingkat {tingkat}): *Rp {total_utang:,}*' if total_utang > 0 else ''
        except Exception as e:
            logger.error(f"Error getting debt: {e}")
            utang_info = ''
        
        keyboard = [
            [InlineKeyboardButton("🍞 Roti - Rp 3.000", callback_data='barang_roti')],
            [InlineKeyboardButton("🥔 Singkong - Rp 5.000", callback_data='barang_singkong')],
            [InlineKeyboardButton("🌶️ Basreng - Rp 7.500", callback_data='barang_basreng')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f'✅ Nama: *{nama}*{utang_info}\n\n'
            'Pilih barang yang dibeli:',
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return BARANG
    
    async def barang_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pilihan barang"""
        query = update.callback_query
        await query.answer()
        
        barang_key = query.data.split('_')[1]
        context.user_data['barang'] = barang_key
        
        item = ITEMS[barang_key]
        
        await query.edit_message_text(
            f'✅ Barang: *{item["name"]}* (Rp {item["price"]:,})\n\n'
            'Masukkan *jumlah* yang dibeli:',
            parse_mode='Markdown'
        )
        
        return JUMLAH
    
    async def jumlah_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle input jumlah"""
        try:
            jumlah = int(update.message.text.strip())
            
            if jumlah <= 0:
                await update.message.reply_text(
                    '❌ Jumlah harus lebih dari 0. Silakan masukkan jumlah:'
                )
                return JUMLAH
            
            # Hitung total
            barang_key = context.user_data['barang']
            item = ITEMS[barang_key]
            total = item['price'] * jumlah
            
            # Simpan ke Google Sheets
            transaction_data = {
                'tanggal': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'tingkat': context.user_data['tingkat'],
                'nama': context.user_data['nama'],
                'barang': item['name'],
                'jumlah': jumlah,
                'harga_satuan': item['price'],
                'total': total
            }
            
            self.sheets.add_transaction(transaction_data)
            
            # Get updated total debt for this tingkat
            nama = context.user_data['nama']
            tingkat = int(context.user_data['tingkat'])
            total_utang = self.sheets.get_total_debt(nama, tingkat)
            
            await update.message.reply_text(
                '✅ *Transaksi Berhasil Dicatat!*\n\n'
                f'👤 Nama: *{nama}*\n'
                f'🎓 Tingkat: *{context.user_data["tingkat"]}*\n'
                f'📦 Barang: *{item["name"]}*\n'
                f'🔢 Jumlah: *{jumlah}*\n'
                f'💵 Harga Satuan: *Rp {item["price"]:,}*\n'
                f'💰 Total Transaksi: *Rp {total:,}*\n\n'
                f'📊 *Total Utang {nama} (Tingkat {tingkat}): Rp {total_utang:,}*\n\n'
                'Ketik /start untuk transaksi baru\n'
                'Ketik /lunas untuk pelunasan\n'
                'Ketik /stats untuk statistik',
                parse_mode='Markdown'
            )
            
            # Clear user data
            context.user_data.clear()
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                '❌ Input tidak valid. Masukkan angka untuk jumlah:'
            )
            return JUMLAH
        except Exception as e:
            logger.error(f"Error saving transaction: {e}")
            await update.message.reply_text(
                '❌ Terjadi kesalahan saat menyimpan transaksi. Silakan coba lagi.'
            )
            return ConversationHandler.END
    
    async def lunas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command untuk pelunasan - show tingkat selection"""
        keyboard = [
            [InlineKeyboardButton("Tingkat 1", callback_data='lunas_tingkat_1')],
            [InlineKeyboardButton("Tingkat 2", callback_data='lunas_tingkat_2')],
            [InlineKeyboardButton("Tingkat 3", callback_data='lunas_tingkat_3')],
            [InlineKeyboardButton("Tingkat 4", callback_data='lunas_tingkat_4')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            '💳 *Pilih tingkat untuk pelunasan:*',
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def lunas_tingkat_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle tingkat selection for payment"""
        query = update.callback_query
        await query.answer()
        
        tingkat = int(query.data.split('_')[2])
        
        try:
            customers = self.sheets.get_unpaid_customers(tingkat)
            
            if not customers:
                await query.edit_message_text(
                    f'✅ Tidak ada utang di Tingkat {tingkat}!'
                )
                return
            
            keyboard = []
            for customer in customers:
                nama = customer['nama']
                total = customer['total']
                keyboard.append([
                    InlineKeyboardButton(
                        f"{nama} - Rp {total:,}",
                        callback_data=f'bayar_{tingkat}_{nama}'
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f'💳 *Pilih nama untuk pelunasan (Tingkat {tingkat}):*',
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in lunas tingkat handler: {e}")
            await query.edit_message_text(
                '❌ Terjadi kesalahan. Pastikan spreadsheet sudah dikonfigurasi dengan benar.'
            )
    
    async def lunas_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pelunasan"""
        query = update.callback_query
        await query.answer()
        
        # Parse callback data: bayar_{tingkat}_{nama}
        parts = query.data.split('_', 2)
        tingkat = int(parts[1])
        nama = parts[2]
        
        try:
            total_sebelum = self.sheets.get_total_debt(nama, tingkat)
            self.sheets.mark_as_paid(nama, tingkat)
            
            await query.edit_message_text(
                '✅ *Pelunasan Berhasil!*\n\n'
                f'👤 Nama: *{nama}*\n'
                f'🎓 Tingkat: *{tingkat}*\n'
                f'💰 Total Dilunasi: *Rp {total_sebelum:,}*\n\n'
                f'Data telah dihapus dari Tingkat {tingkat}\n'
                'Backup tersimpan di History',
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error marking as paid: {e}")
            await query.edit_message_text(
                '❌ Terjadi kesalahan saat memproses pelunasan.'
            )
    
    async def cek(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command untuk cek utang"""
        if not context.args:
            await update.message.reply_text(
                '📊 *Cara penggunaan:*\n'
                '`/cek [nama]`\n\n'
                'Contoh: `/cek Yusuf`',
                parse_mode='Markdown'
            )
            return
        
        nama = ' '.join(context.args)
        
        try:
            # Get debt breakdown per tingkat
            breakdown = []
            grand_total = 0
            
            for tingkat in range(1, 5):
                total_tingkat = self.sheets.get_total_debt(nama, tingkat)
                if total_tingkat > 0:
                    breakdown.append(f'Tingkat {tingkat}: Rp {total_tingkat:,}')
                    grand_total += total_tingkat
            
            if grand_total > 0:
                breakdown_text = '\n'.join(breakdown)
                await update.message.reply_text(
                    f'📊 *Status Utang*\n\n'
                    f'👤 Nama: *{nama}*\n\n'
                    f'{breakdown_text}\n\n'
                    f'💰 *Total Semua: Rp {grand_total:,}*',
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f'✅ *{nama}* tidak memiliki utang!',
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error checking debt: {e}")
            await update.message.reply_text(
                '❌ Terjadi kesalahan saat mengecek utang.'
            )
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command untuk menampilkan statistik"""
        try:
            stats_data = self.sheets.get_stats()
            
            message = '📊 *Statistik Per Tingkat*\n\n'
            
            for tingkat in range(1, 5):
                tingkat_stats = stats_data['tingkat'][tingkat]
                message += (
                    f'*Tingkat {tingkat}:*\n'
                    f'  💰 Total Utang: Rp {tingkat_stats["total_debt"]:,}\n'
                    f'  👥 Pelanggan: {tingkat_stats["num_customers"]}\n'
                    f'  📝 Transaksi: {tingkat_stats["num_transactions"]}\n\n'
                )
            
            message += (
                f'📈 *TOTAL KESELURUHAN:*\n'
                f'💰 Rp {stats_data["grand_total"]:,}\n'
                f'👥 {stats_data["total_customers"]} pelanggan\n'
                f'📝 {stats_data["total_transactions"]} transaksi'
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await update.message.reply_text(
                '❌ Terjadi kesalahan saat mengambil statistik.'
            )
    
    async def export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command untuk export data per tingkat"""
        if not context.args:
            await update.message.reply_text(
                '📤 *Cara penggunaan:*\n'
                '`/export [tingkat]`\n\n'
                'Contoh: `/export 2`',
                parse_mode='Markdown'
            )
            return
        
        try:
            tingkat = int(context.args[0])
            
            if tingkat not in [1, 2, 3, 4]:
                await update.message.reply_text(
                    '❌ Tingkat harus 1, 2, 3, atau 4'
                )
                return
            
            # Get CSV data
            csv_data = self.sheets.export_data(tingkat)
            
            if not csv_data:
                await update.message.reply_text(
                    f'❌ Tidak ada data di Tingkat {tingkat}'
                )
                return
            
            # Generate filename
            from datetime import datetime
            filename = f'tingkat_{tingkat}_{datetime.now().strftime("%Y%m%d")}.csv'
            
            # Send as document
            from io import BytesIO
            csv_bytes = BytesIO(csv_data.encode('utf-8'))
            csv_bytes.name = filename
            
            await update.message.reply_document(
                document=csv_bytes,
                filename=filename,
                caption=f'✅ Export data Tingkat {tingkat}'
            )
            
        except ValueError:
            await update.message.reply_text(
                '❌ Format tidak valid. Gunakan `/export [tingkat]`',
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            await update.message.reply_text(
                '❌ Terjadi kesalahan saat export data.'
            )
    
    async def import_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start import conversation"""
        keyboard = [
            [InlineKeyboardButton("Tingkat 1", callback_data='import_tingkat_1')],
            [InlineKeyboardButton("Tingkat 2", callback_data='import_tingkat_2')],
            [InlineKeyboardButton("Tingkat 3", callback_data='import_tingkat_3')],
            [InlineKeyboardButton("Tingkat 4", callback_data='import_tingkat_4')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            '📥 *Import CSV Database*\n\n'
            'Pilih tingkat untuk import:',
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return IMPORT_TINGKAT
    
    async def import_tingkat_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle tingkat selection for import"""
        query = update.callback_query
        await query.answer()
        
        tingkat = int(query.data.split('_')[2])
        context.user_data['import_tingkat'] = tingkat
        
        await query.edit_message_text(
            f'✅ Tingkat: *{tingkat}*\n\n'
            '📤 Upload file CSV dengan format:\n'
            '`Tanggal,Nama,Barang,Jumlah,Harga Satuan,Total`\n\n'
            'Contoh:\n'
            '`2026-02-11,Yusuf,Roti,5,3000,15000`',
            parse_mode='Markdown'
        )
        
        return IMPORT_FILE
    
    async def import_file_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle CSV file upload"""
        try:
            document = update.message.document
            
            if not document.file_name.endswith('.csv'):
                await update.message.reply_text(
                    '❌ File harus berformat CSV (.csv)'
                )
                return IMPORT_FILE
            
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()
            csv_content = file_bytes.decode('utf-8')
            
            # Import data
            tingkat = context.user_data['import_tingkat']
            result = self.sheets.import_data(tingkat, csv_content)
            
            # Get total debt after import
            stats_data = self.sheets.get_stats()
            tingkat_total = stats_data['tingkat'][tingkat]['total_debt']
            
            await update.message.reply_text(
                '✅ *Import Berhasil!*\n\n'
                f'📊 Hasil Import Tingkat {tingkat}:\n'
                f'  ✅ {result["imported"]} baris baru\n'
                f'  🔄 {result["merged"]} baris di-merge\n'
                f'  ⚠️ {result["skipped"]} baris dilewati\n\n'
                f'💰 Total Utang Tingkat {tingkat}: Rp {tingkat_total:,}',
                parse_mode='Markdown'
            )
            
            # Clear user data
            context.user_data.clear()
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error importing file: {e}")
            await update.message.reply_text(
                '❌ Terjadi kesalahan saat import file. Pastikan format CSV sudah benar.'
            )
            return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel conversation"""
        await update.message.reply_text(
            '❌ Transaksi dibatalkan.\n\n'
            'Ketik /start untuk memulai transaksi baru.'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    def run(self):
        """Run the bot"""
        # Initialize sheets
        try:
            self.sheets.initialize_sheets()
            logger.info("Google Sheets initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing sheets: {e}")
            return
        
        # Create application
        application = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
        
        # Conversation handler untuk transaksi
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                TINGKAT: [CallbackQueryHandler(self.tingkat_handler, pattern='^tingkat_')],
                NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.nama_handler)],
                BARANG: [CallbackQueryHandler(self.barang_handler, pattern='^barang_')],
                JUMLAH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.jumlah_handler)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
        
        # Conversation handler untuk import
        import_handler = ConversationHandler(
            entry_points=[CommandHandler('import', self.import_cmd)],
            states={
                IMPORT_TINGKAT: [CallbackQueryHandler(self.import_tingkat_handler, pattern='^import_tingkat_')],
                IMPORT_FILE: [MessageHandler(filters.Document.ALL, self.import_file_handler)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
        
        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(import_handler)
        application.add_handler(CommandHandler('lunas', self.lunas))
        application.add_handler(CallbackQueryHandler(self.lunas_tingkat_handler, pattern='^lunas_tingkat_'))
        application.add_handler(CallbackQueryHandler(self.lunas_handler, pattern='^bayar_'))
        application.add_handler(CommandHandler('cek', self.cek))
        application.add_handler(CommandHandler('stats', self.stats))
        application.add_handler(CommandHandler('export', self.export))
        
        # Start bot
        logger.info("Bot is starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = KasirBot()
    bot.run()
