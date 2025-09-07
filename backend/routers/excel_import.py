import traceback

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from services.sheet_writer import write_to_sheet
import pandas as pd
import io
from models.booking import BookingData
from datetime import datetime
import re
from fastapi import Request
from typing import Dict, Any, AnyStr

router = APIRouter(prefix="/api", tags=["excel"])


def clean_number(value):
    if pd.isna(value):
        return 0
    # Remove any non-numeric characters except decimal point and minus sign
    cleaned = re.sub(r'[^0-9.-]', '', str(value))
    try:
        return float(cleaned)
    except ValueError:
        return 0


def convert_date_format(date_str):
    """Convert date from YYYY-MM-DD to DD/MM/YYYY format"""
    if pd.isna(date_str) or not date_str:
        return ""
    try:
        # Try parsing the date string
        date_obj = pd.to_datetime(date_str)
        return date_obj.strftime("%d/%m/%Y")
    except:
        return str(date_str)


def calculate_commission_amount(price, commission_percent):
    price_num = clean_number(price)
    commission_num = clean_number(commission_percent)
    return (price_num * commission_num) / 100


# Define the column mapping using indices instead of column names
COLUMN_MAPPING = {
    1: 'guest_name',  # Booked by
    3: 'check_in_date',  # Check-in
    4: 'check_out_date',  # Check-out
    5: 'book_on',  # Booked on
    8: 'pax',  # People
    12: 'total_price',  # Price
    22: 'room_type',  # Unit type
    26: 'phone_number',  # Phone number
    10: 'ota',  # Booking
    11: 'payment_type',  # Payment method (payment provider)
    14: 'commission',  # Commission %
    0: 'booking_code',  # Book Number
    6: 'status'  # Status
}


@router.post("/import-excel")
async def import_excel(file: UploadFile = File(...), listing_name: str = Form(...)):
    try:
        # Read the Excel file
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # Map the Excel columns to our BookingData model using indices
        bookings = []
        for _, row in df.iterrows():
            booking_data = {
                'listing_name': listing_name,
                'check_in_time': ''  # Default empty value
            }

            # Map each column from the Excel file to our model using indices
            for col_index, model_field in COLUMN_MAPPING.items():
                if col_index < len(df.columns):
                    if model_field == 'ota':
                        # Set default value 'Booking' for OTA if not present
                        booking_data[model_field] = 'Booking'
                    elif model_field == 'listing_name':
                        # Always use the provided listing name
                        booking_data[model_field] = listing_name
                    elif model_field == 'payment_type':
                        # Set default value 'Hotel Collect' for Payment Type if not present
                        booking_data[model_field] = 'Hotel Collect'
                    elif model_field == 'status':
                        # Convert status to CONFIRMED or CANCELLED
                        status = str(row.iloc[col_index]) if pd.notna(row.iloc[col_index]) else ''
                        booking_data[model_field] = 'CONFIRMED' if status.lower() == 'ok' else 'CANCELLED'
                    elif model_field == 'total_price':
                        booking_data[model_field] = clean_number(row.iloc[col_index]) if pd.notna(
                            row.iloc[col_index]) else 0
                    elif model_field == 'commission':
                        booking_data[model_field] = clean_number(row.iloc[col_index])
                    elif model_field == 'check_in_date':
                        booking_data[model_field] = convert_date_format(row.iloc[col_index])
                    elif model_field == 'check_out_date':
                        booking_data[model_field] = convert_date_format(row.iloc[col_index])
                    elif model_field == 'phone_number':
                        booking_data[model_field] = ''
                    elif model_field == 'book_on':
                        booking_data[model_field] = convert_date_format(row.iloc[col_index])
                    else:
                        booking_data[model_field] = str(row.iloc[col_index]) if pd.notna(row.iloc[col_index]) else ''
                else:
                    if model_field == 'ota':
                        booking_data[model_field] = 'Booking'
                    elif model_field == 'listing_name':
                        booking_data[model_field] = listing_name
                    elif model_field == 'payment_type':
                        booking_data[model_field] = 'Hotel Collect'
                    elif model_field == 'status':
                        booking_data[model_field] = 'CANCELLED'  # Default to CANCELLED if status column is missing
                    else:
                        booking_data[model_field] = ''

            # Calculate commission amount

            booking = BookingData(**booking_data)
            bookings.append(booking)

        # Write to Google Sheet
        if write_to_sheet(bookings):
            return {"message": "Data imported successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to write to Google Sheet")

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import_booking")
async def import_booking(request: Request):
    try:
        body = await request.json()
        data = body.get("data")
        listing_name = body.get("listing_name")

        def convert_date_format(text):
            return datetime.strptime(text, '%Y-%m-%d').strftime('%d/%m/%Y')

        vals = []
        for rec in data['reservations']:
            rooms = ','.join([i['name'] for i in rec['rooms']])
            pax = rec['occupancy']['adults'] if rec['occupancy'].get('adults') else rec['occupancy']['guests']
            vals.append(BookingData(
                listing_name=listing_name,
                guest_name=rec['guestName'],
                check_in_date=convert_date_format(rec['checkin']),
                check_in_time='',
                check_out_date=convert_date_format(rec['checkout']),
                pax=str(pax),
                total_price=rec['price']['amount'],
                room_type=rooms,
                phone_number='',
                ota='Booking',
                payment_type='Hotel Collect',
                commission=rec['commission']['original']['amount'],
                status='CONFIRMED' if rec['reservationStatus'] == 'ok' else 'CANCELLED',
                booking_code=str(rec['id']),
                book_on=convert_date_format(rec['bookDate'])
            ))
        if write_to_sheet(vals):
            return {"message": "Data imported successfully"}
        return JSONResponse(content={"message": "Data received successfully"}, status_code=200)
    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(content={"error": str(e)}, status_code=400)
