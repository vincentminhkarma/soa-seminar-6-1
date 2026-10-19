# Tồn kho giả lập và định nghĩa tool cho Function Calling. AI chỉ đề xuất gọi; backend mới chạy hàm này.
from datetime import timedelta

from app.config import CAPACITY, MAX_NIGHTS, RESERVATIONS
from app.schemas import Booking


def check_room_availability(room_type, check_in, check_out):
    booking = Booking(room_type=room_type, check_in=check_in, check_out=check_out)
    if None in (booking.room_type, booking.check_in, booking.check_out):
        raise ValueError('Cần loại phòng và đủ hai ngày')
    days = (booking.check_out - booking.check_in).days
    if days > MAX_NIGHTS:
        raise ValueError(f'Demo chỉ hỗ trợ tối đa {MAX_NIGHTS} đêm')
    remaining = min(CAPACITY[booking.room_type] - sum(
        room == booking.room_type and start <= booking.check_in + timedelta(days=i) < end
        for room, start, end in RESERVATIONS) for i in range(days))
    return {'available': remaining > 0, 'rooms_left': remaining, 'simulated': True}


TOOL = {'type': 'function', 'function': {
    'name': 'check_room_availability', 'description': 'Tra cứu tồn kho mô phỏng theo khoảng ngày.',
    'parameters': {'type': 'object', 'properties': {
        'room_type': {'type': 'string', 'enum': list(CAPACITY)},
        'check_in': {'type': 'string'}, 'check_out': {'type': 'string'}},
        'required': ['room_type', 'check_in', 'check_out'], 'additionalProperties': False}}}
