from services.sheet_writer import write_to_sheet
from models.booking import BookingData
import re
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from imap_tools import MailBox, AND
from bs4 import BeautifulSoup
import traceback
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.currency_service import convert_usd_to_vnd
import time
from email.header import decode_header
from models.settings import SettingsManager

settings = SettingsManager()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
LIMIT = 1000

def findDataByKeyword(target: BeautifulSoup, keyword: str) -> str:
    element = target.find(id=lambda value: value and keyword in value)
    if element:
        return element.text
    return ''


def extract_commission(soup: BeautifulSoup) -> Optional[str]:
    # Tìm <span> hoặc <td> chứa từ "Commission"
    for tag in soup.find_all(['span', 'td']):
        if tag.get_text(strip=True).lower().startswith("commission"):
            # Lấy thẻ cha <tr> của nó để lấy dòng đó
            row = tag.find_parent("tr")
            if row:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    return cells[1].get_text(strip=True)
    return ''


def parse_booking_date(date_str: str) -> str:
    """
    Parse booking date from two specific formats:
    1. Vietnamese format: "16 tháng 5 năm 2025 8:58 PM PST"
    2. English format: "May 3, 2025 1:05 AM PST"
    Returns date in format: "DD/MM/YYYY"
    """
    try:
        if not date_str:
            return ''

        # Remove timezone information
        date_str = date_str.split(' PST')[0].strip()

        # Try Vietnamese format first (e.g., "16 tháng 5 năm 2025 8:58 PM")
        try:
            dt = datetime.strptime(date_str, '%d tháng %m năm %Y %I:%M %p')
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            pass

        # Try English format (e.g., "May 3, 2025 1:05 AM")
        try:
            dt = datetime.strptime(date_str, '%b %d, %Y %I:%M %p')
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            pass

        try:
            dt = datetime.strptime(date_str, '%b %d, %Y')
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            pass
        try:
            dt = date_obj = datetime.strptime(date_str, "%B %d, %Y")
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            pass

        print(f"Could not parse booking date format: {date_str}")
        return date_str

    except Exception as e:
        print(f"Error parsing booking date: {str(e)}")
        return date_str


def normalize_price_text(price_str: str) -> float:
    try:
        if not price_str:
            return 0.0

        # Convert to string and strip whitespace
        price_str = str(price_str).strip().replace('-', '')

        # Handle negative numbers
        is_negative = False
        if price_str.startswith('-') or price_str.startswith('(') and price_str.endswith(')'):
            is_negative = True
            price_str = price_str.strip('()-')

        # Remove currency symbols and text
        currency_symbols = ['$', '€', '£', '¥', '₫', 'VND', 'USD', 'EUR', 'GBP']
        for symbol in currency_symbols:
            price_str = price_str.replace(symbol, '')

        # Remove all whitespace
        price_str = ''.join(price_str.split())

        # Handle different decimal/thousand separators
        if ',' in price_str and '.' in price_str:
            # If both separators exist, determine which is decimal
            last_comma = price_str.rindex(',')
            last_dot = price_str.rindex('.')
            if last_comma > last_dot:
                # Comma is decimal separator
                price_str = price_str.replace('.', '').replace(',', '.')
            else:
                # Dot is decimal separator
                price_str = price_str.replace(',', '')
        elif ',' in price_str:
            # Check if comma is used as thousand separator
            parts = price_str.split(',')
            if len(parts[-1]) == 3 and len(parts) > 1:
                # Comma is thousand separator
                price_str = price_str.replace(',', '')
            else:
                # Comma is decimal separator
                price_str = price_str.replace(',', '.')

        # Remove any remaining non-numeric characters except decimal point
        price_str = re.sub(r'[^\d\.]', '', price_str)

        # Handle multiple decimal points
        if price_str.count('.') > 1:
            price_str = price_str.replace('.', '')

        # Convert to float and handle negative
        result = float(price_str)
        return -result if is_negative else result

    except (ValueError, IndexError) as e:
        print(f"Error normalizing price '{price_str}': {str(e)}")
        print(traceback.format_exc())
        return 0.0


def extract_phone_number(soup: BeautifulSoup) -> Optional[str]:
    # Common patterns for phone numbers
    phone_patterns = [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 10 digits
        r'\b\d{2}[-.]?\d{3}[-.]?\d{4}\b',  # 9 digits
        r'\b\d{4}[-.]?\d{3}[-.]?\d{3}\b'  # 10 digits with different grouping
    ]

    for pattern in phone_patterns:
        matches = re.findall(pattern, soup.get_text())
        if matches:
            return matches[0]
    return ''


def extract_check_in_time(soup: BeautifulSoup) -> Optional[str]:
    # Look for common time patterns
    time_patterns = [
        r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b',
        r'\b\d{1,2}h\b',
        r'\b\d{1,2}:\d{2}\b'
    ]

    for pattern in time_patterns:
        matches = re.findall(pattern, soup.get_text())
        if matches:
            return matches[0]
    return ''


def convert_date_format(date_str: str) -> str:
    try:
        # Handle Agoda format: 12-May-2025
        try:
            match = re.search(r'\((\d{2}-\d{2}-\d{4})\)', date_str)
            date_str = match.group(1)
            dt = datetime.strptime(date_str, '%d-%m-%Y')
            return dt.strftime('%d/%m/%Y')
        except Exception:
            pass
        try:
            match = re.search(r"\b\d{1,2}-\d{1,2}-\d{4}\b", date_str)
            if match:
                date_str = match.group()
                date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                return date_obj.strftime('%d/%m/%Y')
        except Exception:
            pass
        return date_str
    except Exception as e:
        print(f"Error converting date format: {str(e)}")
        return date_str


def convert_date_format_expedia(date_str: str) -> str:
    try:
        try:
            match = re.search(r'Ngày (\d{1,2}) tháng (\d{1,2}) năm (\d{4})', date_str)

            day, month, year = map(int, match.groups())
            dt = datetime(year, month, day)
            return dt.strftime('%d/%m/%Y')
        except Exception:
            pass

        try:
            dt = datetime.strptime(date_str, '%b %d, %Y')
            return dt.strftime('%d/%m/%Y')
        except Exception as e:
            pass

        try:
            match = re.search(r"\b\d{1,2}-\d{1,2}-\d{4}\b", date_str)

            if match:
                date_str = match.group()
                date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                return date_obj.strftime('%d/%m/%Y')
        except ValueError:
            pass
        return date_str
    except Exception as e:
        print(f"Error converting date format: {str(e)}")
        return date_str


def agoda_fetch_data(soup_body: BeautifulSoup) -> Optional[BookingData]:
    try:
        table = soup_body.find("table")

        booking_id = findDataByKeyword(table, 'BookingIDValue')
        guest_first_name = findDataByKeyword(table, 'CustomerFirstNameValue')
        guest_last_name = findDataByKeyword(table, 'CustomerLastNameValue')
        guest_name = f"{guest_first_name} {guest_last_name}" if guest_first_name and guest_last_name else ""
        check_in_date = convert_date_format(findDataByKeyword(table, 'CustomerArrival'))
        check_in_time = extract_check_in_time(table)
        check_out_date = convert_date_format(findDataByKeyword(table, 'CustomerDeparture'))
        amount = findDataByKeyword(table, 'AmountPayableData')
        listing_name = findDataByKeyword(table, 'HotelNameData')
        room_type = findDataByKeyword(table, 'RoomTypeData')
        pax = findDataByKeyword(table, 'OccupancyValue').split(' ')[0]
        phone_number = extract_phone_number(table)
        commission_value = extract_commission(table)
        ota = 'Agoda'
        payment_type = 'Card'

        return BookingData(
            listing_name=listing_name,
            guest_name=guest_name,
            check_in_date=check_in_date,
            check_in_time=check_in_time,
            check_out_date=check_out_date,
            pax=pax,
            total_price=normalize_price_text(amount),
            room_type=room_type,
            phone_number=phone_number,
            ota=ota,
            payment_type='OTA Collect',
            commission=normalize_price_text(commission_value),
            booking_code=booking_id
        )

    except Exception as e:
        print(traceback.format_exc())
        print(f"Error parsing email: {str(e)}")
    return None


def agoda_cancel_data(soup_body: BeautifulSoup) -> Optional[BookingData]:
    try:
        table = soup_body

        booking_id = findDataByKeyword(table, 'booking_id').split(':')[-1].strip()
        guest_first_name = findDataByKeyword(table, 'first_name').split(':')[-1].strip()
        guest_last_name = findDataByKeyword(table, 'last_name').split(':')[-1].strip()
        guest_name = f"{guest_first_name} {guest_last_name}" if guest_first_name and guest_last_name else ""
        check_in_date = parse_booking_date(findDataByKeyword(table, 'arrival').split(':')[-1].strip())
        check_in_time = ''
        check_out_date = parse_booking_date(findDataByKeyword(table, 'departure').split(':')[-1].strip())
        amount = '0'
        listing_name = findDataByKeyword(table, 'hotel_name').split(':')[-1].strip()
        room_type = findDataByKeyword(table, 'room_type').split(':')[-1].strip()
        pax = findDataByKeyword(table, 'number_of_adults').split(':')[-1].strip()
        phone_number = ''
        commission_value = '0'
        ota = 'Agoda'
        payment_type = 'Card'

        return BookingData(
            listing_name=listing_name,
            guest_name=guest_name,
            check_in_date=check_in_date,
            check_in_time=check_in_time,
            check_out_date=check_out_date,
            pax=pax,
            total_price=normalize_price_text(amount),
            room_type=room_type,
            phone_number=phone_number,
            ota=ota,
            payment_type='OTA Collect',
            commission=normalize_price_text(commission_value),
            booking_code=booking_id,
            status="CANCELLED"
        )

    except Exception as e:
        print(traceback.format_exc())
        print(f"Error parsing email: {str(e)}")
    return None


def parse_expedia_email(soup: BeautifulSoup) -> Optional[BookingData]:
    try:
        booking_code = ''
        guest_name = ''
        check_in_date = ''
        check_in_time = ''
        book_on = ''
        check_out_date = ''
        total_price = ''
        listing_name = ''
        room_type = ''
        pax = ''
        commission = 0
        phone_number = ''
        payment_type = 'OTA Collect'
        total_charge = ''
        total_amount_float = ''
        booking_amount = 0
        expedia_charge = 0

        def normalize_price(price_str: str) -> str:
            # Convert to string and strip whitespace
            price_str = str(price_str).strip().replace('-', '')

            # Handle negative numbers
            is_negative = False
            if price_str.startswith('-') or price_str.startswith('(') and price_str.endswith(')'):
                is_negative = True
                price_str = price_str.strip('()-')

            # Remove currency symbols and text
            currency_symbols = ['$', '€', '£', '¥', '₫', 'VND', 'VNĐ', 'USD', 'EUR', 'GBP']
            for symbol in currency_symbols:
                price_str = price_str.replace(symbol, '')
            price_str = price_str.replace('.', '')
            price_str = price_str.replace(',', '')
            result = float(price_str.strip())
            return -result if is_negative else result

        bold_tags = soup.find_all("b")
        for b in bold_tags:
            if "Mã đặt chỗ" in b.get_text() or "Reservation ID" in b.get_text():
                a_tag = b.find_next("a")
                if a_tag:
                    booking_code = a_tag.get_text(strip=True)
            if "Khách mời" in b.get_text() or "Guest:" in b.get_text():
                td = b.find_parent("td")
                guest_name = td.get_text(strip=True).split(":")[-1].strip()
        all_td = soup.find_all("td")
        for idx, td in enumerate(all_td):
            text = td.get_text(strip=True)
            if "Booked on:" in text or "Đã đặt vào:" in text:
                book_on = text.split(": ")[-1].strip()
                phone_number = all_td[idx + 2].get_text(strip=True)
            elif text == "Đăng ký vào" or text == 'Check-In':
                check_in_date = convert_date_format_expedia(all_td[idx + 6].get_text(strip=True))
            elif text == "Kiểm tra ra" or text == 'Check-Out':
                check_out_date = convert_date_format_expedia(all_td[idx + 6].get_text(strip=True))
            elif text == "Người lớn" or text == 'Adults':
                pax = all_td[idx + 6].get_text(strip=True)
            elif text == "Tổng số tiền đặt phòng:" or text == 'Total Booking Amount:':
                booking_amount = normalize_price(all_td[idx + 1].text)
            elif text == "Số tiền phải trả cho Expedia Group:" or text == 'Total:' or text == 'Amount to Charge Expedia Group:':
                expedia_charge = normalize_price(all_td[idx + 1].text)
            elif (text.startswith("Mã loại phòng:") or text.startswith("Room Type Code:")) and room_type == '':
                room_type = td.get_text(strip=True).split(':')[-1]
            elif (
                    'Hotel Collects' in text or 'Khách sạn thu tiền từ khách' in text) and payment_type != 'Hotel Collect':
                payment_type = 'Hotel Collect'
        all_tables = soup.find_all('table')
        for table in all_tables:
            if 'New Reservation' in table.get_text() or 'New Reservation' in table.get_text():
                listing_name = table.find_all('td')[3].get_text(strip=True)

        if listing_name == '':
            listing_name = soup.find_all('div')[0].get_text().split('  ')[1]

        if check_in_time:
            check_in_time = datetime.strptime(check_in_time, '%I:%M %p').strftime('%H:%M')

        total_price = 0
        commission = 0
        if booking_amount:
            if expedia_charge:
                commission = booking_amount - expedia_charge
            total_price = booking_amount
        else:
            total_price = expedia_charge

        return BookingData(
            listing_name=str(listing_name),
            guest_name=str(guest_name),
            check_in_date=check_in_date,
            check_in_time=check_in_time,
            check_out_date=check_out_date,
            book_on=parse_booking_date(book_on),
            pax=pax,
            total_price=total_price,
            room_type=room_type,
            phone_number=phone_number,
            ota="Expedia",
            payment_type=payment_type,
            commission=commission,
            booking_code=booking_code
        )
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error parsing Expedia email: {str(e)}")
        return None


def parse_expedia_cancel_email(soup: BeautifulSoup) -> Optional[BookingData]:
    try:
        booking_code = ''
        guest_name = ''
        check_in_date = ''
        check_in_time = ''
        check_out_date = ''
        total_price = ''
        listing_name = ''
        room_type = ''
        pax = ''
        phone_number = ''
        book_on = ''
        payment_type = ''
        cancel_date = ''
        cancel_by = ''

        # Find booking code
        bold_tags = soup.find_all("b")
        for b in bold_tags:
            if "Mã đặt chỗ" in b.get_text() or 'Reservation ID:' in b.get_text():
                a_tag = b.find_next("a")
                if a_tag:
                    booking_code = a_tag.get_text(strip=True)
            if "Khách mời" in b.get_text() or 'Guest:' in b.get_text():
                td = b.find_parent("td")
                guest_name = td.get_text(strip=True).split(":")[-1].strip()

        # Find check-in and check-out dates
        date_tags = soup.find_all('td')
        for idx, td in enumerate(date_tags):
            text = td.get_text(strip=True)
            if "Booked on:" in text or "Đã đặt vào:" in text:
                book_on = text.split(": ")[-1].strip()
                phone_number = date_tags[idx + 2].get_text(strip=True)
            if text == 'Đăng ký vào' or text == 'Check-In':
                check_in_date = convert_date_format_expedia(date_tags[idx + 7].get_text(strip=True))
            elif text == 'Kiểm tra ra' or text == 'Check-Out':
                check_out_date = convert_date_format_expedia(date_tags[idx + 7].get_text(strip=True))
            elif text == 'Người lớn' or text == 'Adults':
                pax = date_tags[idx + 7].get_text(strip=True)
            elif (text.startswith("Mã loại phòng:") or text.startswith("Room Type Code:")) and room_type == '':
                room_type = td.get_text(strip=True).split(':')[-1]
            elif (
                    'Hotel Collects' in text or 'Khách sạn thu tiền từ khách' in text) and payment_type != 'Hotel Collect':
                payment_type = 'Hotel Collect'
        all_tables = soup.find_all('table')
        for table in all_tables:
            if 'New Reservation' in table.get_text() or 'Cancellation' in table.get_text():
                listing_name = table.find_all('td')[3].get_text(strip=True)
        if listing_name == '':
            listing_name = soup.find_all('div')[0].get_text().split('  ')[1]
        # Find total price
        total_price_tag = soup.find('td', string=lambda x: x and 'Tổng cộng:' in x)
        if total_price_tag:
            price_td = total_price_tag.find_next('td')
            if price_td:
                price_text = price_td.get_text(strip=True)
                match = re.search(r'([0-9\.]+)\s*', price_text)
                if match:
                    # Remove thousand separators and convert to float
                    total_price = match.group(1).replace('.', '')

        # Find cancellation date and who cancelled
        cancel_date_tag = soup.find('td', string=lambda x: x and 'Đã hủy vào:' in x)
        if cancel_date_tag:
            cancel_date = cancel_date_tag.get_text(strip=True).replace('Đã hủy vào:', '').strip()

        cancel_by_tag = soup.find('td', string=lambda x: x and 'Đã hủy bởi:' in x)
        if cancel_by_tag:
            cancel_by = cancel_by_tag.get_text(strip=True).replace('Đã hủy bởi:', '').strip()

        return BookingData(
            listing_name=listing_name,
            guest_name=guest_name or "Unknown",
            check_in_date=check_in_date,
            check_in_time=check_in_time,
            check_out_date=check_out_date,
            pax=pax,
            total_price=normalize_price_text(total_price) if total_price else 0,
            book_on=parse_booking_date(book_on),
            room_type=room_type,
            phone_number=phone_number,
            ota="Expedia",
            payment_type=payment_type,
            commission=0,
            booking_code=booking_code,
            status="CANCELLED"
        )
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error parsing Expedia cancellation email: {str(e)}")
        return None


def parse_airbnb_email(soup: BeautifulSoup, msg) -> Optional[BookingData]:
    try:
        # Helper functions
        def extract_date(text):
            try:
                try:
                    vi_date_pattern = r'(\d+)\s+thg\s+(\d+)'
                    match = re.search(vi_date_pattern, text)
                    if match:
                        day = match.group(1)
                        month = match.group(2)
                        return f"{day}/{month}"
                except:
                    pass

                try:
                    date_obj = datetime.strptime(text, "%a, %b %d")
                    return f"{date_obj.day}/{date_obj.month}"
                except:
                    pass

                try:
                    date_obj = datetime.strptime(text, "%a, %b %d, %Y")
                    return f"{date_obj.day}/{date_obj.month}/{date_obj.year}"
                except:
                    pass

            except:
                return text

        def extract_time(text):
            if not text:
                return ''
            time_pattern = r'(\d{1,2}:\d{2})'
            match = re.search(time_pattern, text)
            if match:
                return match.group(1)
            return ''

        def extract_amount(text):
            if not text:
                return ''
            amount_pattern = r'\$(\d+),(\d+)'
            match = re.search(amount_pattern, text)
            if match:
                dollars = match.group(1)
                cents = match.group(2)
                return float(f"{dollars}.{cents}")
            return ''

        # Initialize variables
        listing_name = ''
        check_in_date = ''
        check_in_time = ''
        check_out_date = ''
        room_type = ''
        commission = ''
        payment_type = ''

        # Extract guest name
        guest_name = ''
        message_link = soup.find('a', href=lambda x: x and ('https://www.airbnb.com.vn/hosting/thread/' in x or 'https://www.airbnb.com/hosting/thread' in x or 'https://www.airbnb.com/z/q' in x))
        if message_link:
            spans = message_link.find_all('span')
            for span in spans:
                text = span.get_text()
                if 'Gửi tin nhắn cho' in text:
                    guest_name = text.replace('Gửi tin nhắn cho', '').strip()
                    break
            if guest_name == '':
                text = message_link.get_text()
                if 'a message' in text.lower():
                    guest_name = re.search(r"send (.+?) a message", message_link.text.strip().lower()).group(1).strip().capitalize()

        # Extract booking code
        booking_code = ''
        confirmation_heading = soup.find('h2', string=lambda text: 'Mã xác nhận'.lower() in text.lower()) or soup.find('h2', string=lambda text: 'Confirmation code'.lower() in text.lower()) or soup.find('p', string=lambda text: 'Confirmation code' in text)
        if confirmation_heading:
            booking_code_p = confirmation_heading.find_next('p')
            if booking_code_p:
                booking_code = booking_code_p.get_text().strip()
        # Extract number of guests (pax)

        pax = ''
        guest_heading = soup.find('h2', string='Khách') or soup.find('h2', string='Guests') or soup.find('p', string=lambda text: 'Guests' in text)
        if guest_heading:
            guest_p = guest_heading.find_next('p')
            if guest_p:
                guest_text = guest_p.get_text().strip()
                if guest_text:
                    pax = guest_text.strip(' ')[0]

        # Extract total amount
        total_price = ''
        total_heading = soup.find('h3', string=lambda text: text and ('Tổng ' in text or 'Total ' in text)) or soup.find('p', string=lambda text: text and 'Total' in text)
        if total_heading:
            # Find the next h3 tag which contains the amount
            amount_h3 = total_heading.find_next('h3') or total_heading.find_next('p')
            if amount_h3:
                amount_text = amount_h3.text.strip()
                total_price = amount_text

        commission_cell = soup.find('h3', string=lambda text: text and ('Bạn kiếm được' in text or 'You earn' in text))
        if commission_cell:
            commission_value = commission_cell.find_next('h3')
            if commission_value:
                commission = commission_value.text.strip()

        # Find all tables in the email
        tables = soup.find_all('table')

        airbnb_links = soup.find_all('a', href=lambda href: href and (
                    'https://www.airbnb.com.vn/rooms/' in href or 'https://www.airbnb.com/rooms/' in href))
        for link in airbnb_links:
            if link.get_text(strip=True):
                link_table = link.find_all('table')
                if link_table:
                    listing_name = link.find_all('table')[0].get_text(strip=True)
                    room_type = link.find_all('table')[1].get_text(strip=True)
                else:
                    listing_name = link.find_all('p')[0].get_text(strip=True)
                    room_type = link.find_all('p')[1].get_text(strip=True)

        # Iterate through tables to find relevant information
        for table in tables:
            # Find check-in information
            check_in_cell = table.find('td', string=lambda text: text and ('Nhận phòng' in text or 'Check-in' in text))
            if check_in_cell:
                date_cell = check_in_cell.find_next('td')
                if date_cell:
                    check_in_date = extract_date(date_cell.text)
                time_cell = date_cell.find_next('td') if date_cell else None
                if time_cell:
                    check_in_time = extract_time(time_cell.text)
            else:
                all_p = soup.select('p.body-text-lg.light')
            # Find check-out information
            check_out_cell = table.find('td', string=lambda text: text and ('Trả phòng' in text or 'Checkout' in text))
            if check_out_cell:
                date_cell = check_out_cell.find_next('td')
                if date_cell:
                    check_out_date = extract_date(date_cell.text)

            # Find payment type
            payment_cell = table.find('td', string=lambda text: text and 'Phương thức thanh toán' in text)
            if payment_cell:
                payment_type = payment_cell.text.strip()
        amount_float = convert_usd_to_vnd(normalize_price_text(total_price)) if '$' in total_price else normalize_price_text(total_price)
        commission_float = convert_usd_to_vnd(normalize_price_text(commission)) if '$' in commission else normalize_price_text(commission)
        # Create BookingData object
        booking_data = BookingData(
            listing_name=listing_name or "",
            guest_name=guest_name or "",
            check_in_date=check_in_date,
            check_in_time=check_in_time,
            check_out_date=check_out_date,
            pax=pax,
            total_price=int(amount_float) or 0,
            room_type=room_type,
            phone_number="",  # Not available in Airbnb email
            ota="Airbnb",
            payment_type='OTA Collect',
            commission=int(commission_float),
            booking_code=booking_code,
            status="CONFIRMED"
        )

        return booking_data

    except Exception as e:
        print(traceback.format_exc())
        print(f"Error parsing Airbnb email: {str(e)}")
        return None


def parse_airbnb_email_cancel(soup: BeautifulSoup, mail_obj) -> Optional[BookingData]:
    try:
        booking_code = mail_obj.subject.split('Canceled: Reservation ')[1].split(' ')[0]
        return BookingData(
            listing_name='',
            guest_name='',
            check_in_date='',
            check_in_time='',
            check_out_date='',
            pax='0',
            total_price=0,
            book_on='',
            room_type='',
            phone_number='',
            ota="Airbnb",
            payment_type='',
            commission=0,
            booking_code=booking_code,
            status="CANCELLED"
        )
    except:
        print(traceback.format_exc())
        print("Error parsing Airbnb email Cancel")
        return None


def extract_booking_code(soup: BeautifulSoup) -> str:
    # Find the booking code in the email
    booking_code = soup.find("p", {
        "style": "font-size:18px;line-height:28px;font-family:Cereal,Helvetica Neue,Helvetica,sans-serif;margin:0!important;font-weight:400!important"})
    if booking_code:
        return booking_code.text.strip()
    return ""


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


def save_offset(email_name, email_address, offset):
    """Lưu offset vào file JSON"""
    try:
        SPREADSHEET_ID = settings.get_global_settings().get('googleSheetUrl')
        sheet_name = settings.get_global_settings().get('sheetName')
        offset_file = "data/email_offsets.json"
        offsets = {}

        # Đọc offset hiện tại nếu file tồn tại
        if os.path.exists(offset_file):
            with open(offset_file, "r") as f:
                offsets = json.load(f)

        # Ghi đè offset cho email address (không cộng dồn)
        offsets[f'{SPREADSHEET_ID}_{sheet_name}_{email_name}_{email_address}'] = offset

        # Lưu lại vào file
        with open(offset_file, "w") as f:
            json.dump(offsets, f, indent=4)

    except Exception as e:
        print(f"Error saving offset for {email_address}: {str(e)}")


def load_offset(email_name, email_address):
    """Đọc offset từ file JSON và tạo mới nếu chưa có"""
    try:
        offset_file = "data/email_offsets.json"
        offsets = {}
        SPREADSHEET_ID = settings.get_global_settings().get('googleSheetUrl')
        sheet_name = settings.get_global_settings().get('sheetName')
        # Đọc offset hiện tại nếu file tồn tại
        if os.path.exists(offset_file):
            with open(offset_file, "r") as f:
                offsets = json.load(f)
        offset_check = f"{SPREADSHEET_ID}_{sheet_name}_{email_name}_{email_address}"
        # Nếu email chưa có trong file, tạo mới với offset = 0
        if offset_check not in offsets:
            offsets[offset_check] = 0
            # Lưu lại vào file
            with open(offset_file, "w") as f:
                json.dump(offsets, f, indent=4)
            print(f"Created new offset entry for {offset_check}")

        return offsets.get(offset_check, 0)
    except Exception as e:
        print(f"Error loading offset for {email_address}: {str(e)}")
        return 0


def save_processed_email(email_name, email_address, message_id, booking_code):
    """Lưu thông tin email đã xử lý"""
    try:
        processed_file = "data/processed_emails.json"
        processed = {}

        # Đọc dữ liệu hiện tại nếu file tồn tại
        if os.path.exists(processed_file):
            with open(processed_file, "r") as f:
                processed = json.load(f)

        mail_check = f'{email_name}_{email_address}'
        # Khởi tạo dictionary cho email address nếu chưa có
        if mail_check not in processed:
            processed[mail_check] = []

        # Thêm thông tin email mới
        processed[mail_check].append({
            "message_id": message_id,
            "booking_code": booking_code,
            "processed_at": datetime.now().isoformat()
        })

        # Lưu lại vào file
        with open(processed_file, "w") as f:
            json.dump(processed, f, indent=4)

    except Exception as e:
        print(f"Error saving processed email for {email_address}: {str(e)}")


def is_email_processed(email_name, email_address, message_id, booking_code):
    """Kiểm tra xem email đã được xử lý chưa"""
    try:
        processed_file = "data/processed_emails.json"
        if os.path.exists(processed_file):
            mail_check = f'{email_name}_{email_address}'
            with open(processed_file, "r") as f:
                processed = json.load(f)
                if mail_check in processed:
                    # Kiểm tra theo message_id hoặc booking_code
                    for email in processed[mail_check]:
                        if email["message_id"] == message_id:
                            return True
        return False
    except Exception as e:
        print(f"Error checking processed email for {email_address}: {str(e)}")
        return False


def fetch_emails_for_address(email_name, mailbox, from_address, limit=100, offset=0):
    bookings = []
    try:
        # Sử dụng date-based search thay vì lấy tất cả UID
        from datetime import datetime, timedelta

        # Chỉ tìm email từ 6 tháng gần đây để tránh quá nhiều UID
        six_months_ago = datetime(2024, 1, 1).strftime("%d-%b-%Y")

        # Tìm kiếm với điều kiện date và from_address
        mailbox.client.select('INBOX')
        search_criteria = f'(FROM "{from_address}" SINCE "{six_months_ago}")'
        typ, uid_data = mailbox.client.uid('SEARCH', None, search_criteria)

        if typ != 'OK' or not uid_data[0]:
            # print(f"Không tìm thấy email nào đến từ {from_address} trong mail {email_name}")
            return bookings

        # Chuyển đổi UID thành list integer
        uids = [int(uid) for uid in uid_data[0].split()]
        uids = sorted(uids, reverse=False)  # Mới nhất trước

        if not uids:
            # print(f"Không tìm thấy email nào đến từ {from_address} trong mail {email_name}")
            return bookings

        # Sắp xếp UID và lấy range theo offset và limit
        start_idx = offset
        end_idx = min(offset + limit, len(uids))

        if start_idx >= len(uids):
            # print(f"Không có email nào mới từ {from_address} trong mail {email_name}")
            # Vẫn cập nhật offset để tránh lặp lại
            save_offset(email_name, from_address, len(uids))
            print(f"Không có email mới, cập nhật offset cho {email_name} {from_address}: {len(uids)}")
            return bookings

        # Lấy range UID cần fetch
        range_uids = uids[start_idx:end_idx]
        print(f"Bắt đầu lấy {len(range_uids)} {email_name} {from_address}...")

        chunk_size = LIMIT
        messages = []
        processed_count = 0  # Đếm số email đã xử lý thành công

        for i in range(0, len(range_uids), chunk_size):
            chunk_uids = range_uids[i:i + chunk_size]
            uid_list = ','.join(map(str, chunk_uids))

            try:
                typ, msg_data = mailbox.client.uid('FETCH', uid_list, '(RFC822)')
                if typ == 'OK':
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            import email
                            email_msg = email.message_from_bytes(response_part[1])

                            # Tạo mock object giống như imap_tools
                            class MockMessage:
                                def __init__(self, email_msg):
                                    self.subject = self.decode_mime_words(email_msg.get('Subject', ''))
                                    self.uid = email_msg.get('Message-ID', '')

                                    # Lấy HTML body
                                    self.html = None
                                    if email_msg.is_multipart():
                                        for part in email_msg.walk():
                                            if part.get_content_type() == "text/html":
                                                self.html = part.get_payload(decode=True).decode('utf-8',
                                                                                                 errors='ignore')
                                                break
                                    else:
                                        if email_msg.get_content_type() == "text/html":
                                            self.html = email_msg.get_payload(decode=True).decode('utf-8',
                                                                                                  errors='ignore')

                                @staticmethod
                                def decode_mime_words(text):
                                    decoded_fragments = decode_header(text)
                                    return ''.join([
                                        fragment.decode(encoding or 'utf-8') if isinstance(fragment,
                                                                                           bytes) else fragment
                                        for fragment, encoding in decoded_fragments
                                    ])

                            mock_msg = MockMessage(email_msg)
                            if mock_msg.html:
                                messages.append(mock_msg)
                            processed_count += 1  # Đếm tất cả email đã xử lý (có hoặc không có HTML)
            except Exception as e:
                print(f"Error fetching chunk: {e}")
                continue

        print(f"Đã lấy được {len(messages)} từ email {email_name} {from_address}...")

        for msg in messages:
            body = msg.html

            if body is not None:
                booking = False
                soup = BeautifulSoup(body, "html.parser")
                if 'Agoda Booking'.lower() in msg.subject.lower():
                    if 'CANCELLED'.lower() in msg.subject.lower():
                        booking = agoda_cancel_data(soup)
                    else:
                        booking = agoda_fetch_data(soup)

                if 'Expedia - New Booking'.lower() in msg.subject.lower():
                    booking = parse_expedia_email(soup)

                elif 'Expedia - Booking Cancellation'.lower() in msg.subject.lower():
                    booking = parse_expedia_cancel_email(soup)

                if soup.find("img", {"alt": "Airbnb"}):
                    if 'Reservation confirmed'.lower() in msg.subject.lower() or 'đã xác nhận đặt phòng'.lower() in msg.subject.lower() or 'New booking confirmed'.lower() in msg.subject.lower() or 'reservation reminder' in msg.subject.lower() or 'nhắc nhở đặt phòng' in msg.subject.lower():
                        booking = parse_airbnb_email(soup, msg)
                    elif 'Canceled: Reservation'.lower() in msg.subject.lower():
                        booking = parse_airbnb_email_cancel(soup, msg)
                if booking:
                    bookings.append(booking)
        
        # Lưu offset mới dựa trên vị trí cuối đã xử lý
        # Offset mới = offset cũ + số email đã xử lý
        new_offset = offset + processed_count
        save_offset(email_name, from_address, new_offset)
        print(f"Đã cập nhật offset cho {email_name} {from_address}: {offset} -> {new_offset}")

    except Exception as e:
        print(traceback.format_exc())
        print(f"Error fetching {email_name} emails for {from_address}: {str(e)}")
        # Vẫn cập nhật offset để tránh lặp lại email đã xử lý
        try:
            new_offset = offset + processed_count if 'processed_count' in locals() else offset
            save_offset(email_name, from_address, new_offset)
            print(f"Đã cập nhật offset sau lỗi cho {email_name} {from_address}: {new_offset}")
        except Exception as offset_error:
            print(f"Error updating offset after exception: {str(offset_error)}")
    return bookings


def action_fetch_data(email, password):
    try:
        # Đọc danh sách email address từ file
        emails_file = "data/emails.json"
        if os.path.exists(emails_file):
            with open(emails_file, "r") as f:
                saved_emails = json.load(f)
            # Lấy danh sách address
            from_addresses = [item["email"] for item in saved_emails if "email" in item]
        else:
            from_addresses = []

        all_bookings = []
        limit = LIMIT  # Số lượng record mỗi lần fetch

        with MailBox('imap.gmail.com').login(email, password, initial_folder='INBOX') as mailbox:
            if from_addresses:

                for address in from_addresses:
                    all_bookings = fetch_emails_for_address(email, mailbox, address, limit, load_offset(email, address))
                    if all_bookings:
                        write_to_sheet(all_bookings)
                    else:
                        print(f"Không có email nào được xử lý trong {email} {address}")
            else:
                # Nếu không có danh sách, fetch như cũ
                all_bookings = fetch_emails_for_address(mailbox, None, limit, 0)


    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
