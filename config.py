import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for bot"""
    
    def __init__(self):
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS', 'credentials.json')
        self.SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
        
        self._validate()
    
    def _validate(self):
        """Validate configuration"""
        if not self.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required in .env file")
        
        if not self.SPREADSHEET_ID:
            raise ValueError("SPREADSHEET_ID is required in .env file")
        
        if not os.path.exists(self.GOOGLE_SHEETS_CREDENTIALS):
            raise FileNotFoundError(
                f"Google Sheets credentials file not found: {self.GOOGLE_SHEETS_CREDENTIALS}"
            )
