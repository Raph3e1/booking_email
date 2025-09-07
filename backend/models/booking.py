from pydantic import BaseModel
from typing import Optional


class BookingData(BaseModel):
    listing_name: Optional[str] = ''
    guest_name: Optional[str] = ''
    check_in_date: Optional[str] = ''
    check_in_time: Optional[str] = ''
    cancel_date: Optional[str] = ''
    check_out_date: Optional[str] = ''
    book_on: Optional[str] = ''
    pax: Optional[str] = ''
    total_price: Optional[float] = 0
    room_type: Optional[str] = ''
    phone_number: Optional[str] = ''
    ota: Optional[str] = ''
    payment_type: Optional[str] = ''
    commission: Optional[float] = 0
    booking_code: Optional[str] = ''
    status: Optional[str] = 'CONFIRMED'
