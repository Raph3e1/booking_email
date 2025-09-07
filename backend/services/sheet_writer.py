from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from models.booking import BookingData
from models.settings import SettingsManager
import time
from typing import List, Dict

settings = SettingsManager()
# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
BATCH_SIZE = 50  # Number of updates per batch
DELAY_BETWEEN_BATCHES = 1  # Delay in seconds between batches


def get_google_sheets_service():
    try:
        creds = Credentials.from_service_account_file(
            'credentials.json',  # Make sure to place your credentials file here
            scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        print(f"Error setting up Google Sheets service: {str(e)}")
        return None


def write_to_sheet(booking_data: list[BookingData]):
    try:
        print("Bắt đầu xử lý lên Google Sheet")
        SPREADSHEET_ID = settings.get_global_settings().get('googleSheetUrl')
        sheet_name = settings.get_global_settings().get('sheetName')
        service = get_google_sheets_service()
        if not service:
            return False

        # First, get all existing data from the sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{sheet_name}!A2:O'
        ).execute()
        existing_rows = result.get('values', [])

        # Create a map of booking codes to row indices
        booking_code_map = {row[0]: idx for idx, row in enumerate(existing_rows, start=2) if len(row) > 0}

        # Process bookings to handle CANCELLED status first
        processed_bookings = {}
        for booking in booking_data:
            # Validate required fields
            if not booking.booking_code:
                print(f"Skipping booking: Missing booking code")
                continue

            # If booking_code already exists in processed_bookings
            if booking.booking_code in processed_bookings:
                # If current booking is CANCELLED, update the status
                if booking.status == "CANCELLED":
                    processed_bookings[booking.booking_code][13] = "CANCELLED"
                # If existing booking is CANCELLED and current is not, keep the CANCELLED status
                elif processed_bookings[booking.booking_code][13] == "CANCELLED":
                    continue
                # Otherwise update with new data
                else:
                    processed_bookings[booking.booking_code] = [
                        booking.booking_code,
                        booking.listing_name,
                        booking.guest_name,
                        booking.check_in_date,
                        booking.check_in_time or '',
                        booking.check_out_date,
                        int(booking.pax) if booking.pax else 0,
                        booking.total_price or 0,
                        booking.room_type or '',
                        booking.phone_number or '',
                        booking.ota,
                        booking.payment_type or 'OTA Collect',
                        booking.commission or 0,
                        booking.status or 'CONFIRMED',
                        booking.book_on or '',
                    ]
            else:
                if booking.status != "CANCELLED":
                    processed_bookings[booking.booking_code] = [
                        booking.booking_code,
                        booking.listing_name,
                        booking.guest_name,
                        booking.check_in_date,
                        booking.check_in_time or '',
                        booking.check_out_date,
                        int(booking.pax) if booking.pax else 0,
                        booking.total_price or 0,
                        booking.room_type or '',
                        booking.phone_number or '',
                        booking.ota,
                        booking.payment_type or 'OTA Collect',
                        booking.commission or 0,
                        booking.status or 'CONFIRMED',
                        booking.book_on or '',
                    ]
                elif booking.ota == 'Booking':
                    processed_bookings[booking.booking_code] = [
                        booking.booking_code,
                        booking.listing_name,
                        booking.guest_name,
                        booking.check_in_date,
                        booking.check_in_time or '',
                        booking.check_out_date,
                        int(booking.pax) if booking.pax else 0,
                        booking.total_price or 0,
                        booking.room_type or '',
                        booking.phone_number or '',
                        booking.ota,
                        booking.payment_type or 'OTA Collect',
                        booking.commission or 0,
                        booking.status or 'CONFIRMED',
                        booking.book_on or '',
                    ]
        # Prepare updates and new records
        updates = []
        new_records = []

        for booking_code, row_data in processed_bookings.items():
            if booking_code in booking_code_map:
                row_index = booking_code_map[booking_code]
                if row_data[13] == "CANCELLED":

                    updates.append({
                        'range': f'{sheet_name}!N{row_index}',
                        'values': [["CANCELLED"]]
                    })
                    if row_data[1] != "":
                        updates.append({
                            'range': f'{sheet_name}!B{row_index}',
                            'values': [[row_data[1]]]
                        })
                    if row_data[2] != "":
                        updates.append({
                            'range': f'{sheet_name}!C{row_index}',
                            'values': [[row_data[2]]]
                        })
                    if row_data[11] != "":
                        updates.append({
                            'range': f'{sheet_name}!L{row_index}',
                            'values': [[row_data[11]]]
                        })
                    if row_data[14] != "":
                        updates.append({
                            'range': f'{sheet_name}!O{row_index}',
                            'values': [[row_data[14]]]
                        })
                else:
                    updates.append({
                        'range': f'{sheet_name}!A{row_index}:O{row_index}',
                        'values': [row_data]
                    })
            else:
                new_records.append(row_data)

        # Process updates in batches
        for i in range(0, len(updates), BATCH_SIZE):
            batch = updates[i:i + BATCH_SIZE]
            batch_requests = []

            for update in batch:
                batch_requests.append({
                    'range': update['range'],
                    'values': update['values']
                })

            try:
                body = {
                    'valueInputOption': 'RAW',
                    'data': batch_requests
                }
                service.spreadsheets().values().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body=body
                ).execute()

                if i + BATCH_SIZE < len(updates):
                    time.sleep(DELAY_BETWEEN_BATCHES)

            except Exception as e:
                print(f"Error in batch update: {str(e)}")
                continue

        # Process new records in batches
        for i in range(0, len(new_records), BATCH_SIZE):
            batch = new_records[i:i + BATCH_SIZE]
            try:
                body = {
                    'values': batch
                }
                service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f'{sheet_name}!A2',
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body=body
                ).execute()

                if i + BATCH_SIZE < len(new_records):
                    time.sleep(DELAY_BETWEEN_BATCHES)

            except Exception as e:
                print(f"Error in batch append: {str(e)}")
                continue

        print(f"Đã đẩy {len(new_records)} bản ghi mới và cập nhật {len(updates)} bản ghi lên Google Sheet")
        return True
    except Exception as e:
        print(f"Error writing to Google Sheet: {str(e)}")
        return False
