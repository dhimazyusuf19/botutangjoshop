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
        
        # Cek total utang yang ada
        try:
            total_utang = self.sheets.get_total_debt(nama)
            utang_info = f'\n💰 Total utang saat ini: *Rp {total_utang:,}*' if total_utang > 0 else ''
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
                'total': total,
                'status': 'Belum Lunas'
            }
            
            self.sheets.add_transaction(transaction_data)
            
            # Get updated total debt
            nama = context.user_data['nama']
            total_utang = self.sheets.get_total_debt(nama)
            
            await update.message.reply_text(
                '✅ *Transaksi Berhasil Dicatat!*\n\n'
                f'👤 Nama: *{nama}*\n'
                f'🎓 Tingkat: *{context.user_data["tingkat"]}*\n'
                f'📦 Barang: *{item["name"]}*\n'
                f'🔢 Jumlah: *{jumlah}*\n'
                f'💵 Harga Satuan: *Rp {item["price"]:,}*\n'
                f'💰 Total Transaksi: *Rp {total:,}*\n\n'
                f'📊 *Total Utang {nama}: Rp {total_utang:,}*\n\n'
                'Ketik /start untuk transaksi baru\n'
                'Ketik /lunas untuk pelunasan\n'
                'Ketik /cek untuk cek utang',
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
        """Command untuk pelunasan"""
        try:
            customers = self.sheets.get_unpaid_customers()
            
            if not customers:
                await update.message.reply_text(
                    '✅ Tidak ada utang yang perlu dilunasi!'
                )
                return
            
            keyboard = []
            for customer in customers:
                nama = customer['nama']
                total = customer['total']
                keyboard.append([
                    InlineKeyboardButton(
                        f"{nama} - Rp {total:,}",
                        callback_data=f'lunas_{nama}'
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                '💳 *Pilih nama untuk pelunasan:*',
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in lunas command: {e}")
            await update.message.reply_text(
                '❌ Terjadi kesalahan. Pastikan spreadsheet sudah dikonfigurasi dengan benar.'
            )
    
    async def lunas_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pelunasan"""
        query = update.callback_query
        await query.answer()
        
        nama = query.data.replace('lunas_', '')
        
        try:
            total_sebelum = self.sheets.get_total_debt(nama)
            self.sheets.mark_as_paid(nama)
            
            await query.edit_message_text(
                '✅ *Pelunasan Berhasil!*\n\n'
                f'👤 Nama: *{nama}*\n'
                f'💰 Total Dilunasi: *Rp {total_sebelum:,}*\n\n'
                'Status di spreadsheet telah diupdate menjadi "Lunas"',
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
            total_utang = self.sheets.get_total_debt(nama)
            
            if total_utang > 0:
                await update.message.reply_text(
                    f'📊 *Status Utang*\n\n'
                    f'👤 Nama: *{nama}*\n'
                    f'💰 Total Utang: *Rp {total_utang:,}*',
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
        
        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler('lunas', self.lunas))
        application.add_handler(CallbackQueryHandler(self.lunas_handler, pattern='^lunas_'))
        application.add_handler(CommandHandler('cek', self.cek))
        
        # Start bot
        logger.info("Bot is starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = KasirBot()
    bot.run()