import requests
import json
import os
from datetime import datetime

def get_usd_vnd_exchange_rate() -> float:
    """
    Fetches the current USD to VND exchange rate from a free API
    Returns the exchange rate as a float
    """
    try:
        # Using exchangerate-api.com free API
        response = requests.get('https://open.er-api.com/v6/latest/USD')
        if response.status_code == 200:
            data = response.json()
            if data['result'] == 'success':
                return float(data['rates']['VND'])
        return 0.0
    except Exception as e:
        print(f"Error fetching exchange rate: {str(e)}")
        return 0.0

def update_exchange_rate():
    """
    Updates the exchange rate in settings.json
    """
    try:
        # Get the current exchange rate
        rate = get_usd_vnd_exchange_rate()
        if rate == 0.0:
            return False

        # Read current settings
        settings_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        # Update exchange rate
        settings['exchangeRate'] = rate

        # Save updated settings
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        return True
    except Exception as e:
        print(f"Error updating exchange rate: {str(e)}")
        return False

def convert_usd_to_vnd(usd_amount: float) -> float:
    """
    Converts USD amount to VND using the current exchange rate
    """
    try:
        # Read current settings
        settings_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        exchange_rate = settings.get('exchangeRate', 0.0)
        if exchange_rate == 0.0:
            # If exchange rate is not set, fetch it
            exchange_rate = get_usd_vnd_exchange_rate()
            if exchange_rate == 0.0:
                return 0.0

        return usd_amount * exchange_rate
    except Exception as e:
        print(f"Error converting USD to VND: {str(e)}")
        return 0.0 