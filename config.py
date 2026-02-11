import os
import base64
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for bot"""
    
    def __init__(self):
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
        
        # Check if credentials in base64 (for Railway/cloud deployment)
        credentials_base64 = os.getenv('CREDENTIALS_BASE64')
        if credentials_base64:
            print("✅ Found CREDENTIALS_BASE64, decoding...")
            try:
                # Decode base64 and save to file
                credentials_json = base64.b64decode(credentials_base64).decode('utf-8')
                with open('credentials.json', 'w') as f:
                    f.write(credentials_json)
                self.GOOGLE_SHEETS_CREDENTIALS = 'credentials.json'
                print("✅ credentials.json created successfully!")
            except Exception as e:
                print(f"❌ Error decoding CREDENTIALS_BASE64: {e}")
                raise
        else:
            print("ℹ️ CREDENTIALS_BASE64 not found, using local file")
            # Use local file
            self.GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS', 'credentials.json')
        
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
