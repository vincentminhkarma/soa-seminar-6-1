# Hợp đồng dữ liệu (Pydantic): FastAPI dùng các class này để kiểm tra request và sinh Swagger.
import ipaddress
import re
from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import MAX_TEXT_LENGTH


class Booking(BaseModel):
    model_config = ConfigDict(extra='forbid')
    room_type: Literal['STANDARD', 'DELUXE', 'SUITE'] | None = None
    check_in: date | None = None
    check_out: date | None = None

    @model_validator(mode='after')
    def valid_interval(self):
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValueError('Ngày trả phải sau ngày nhận')
        return self


class Input(BaseModel):
    raw_text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    mode: Literal['regex', 'openai', 'tools'] = 'regex'

    @field_validator('raw_text')
    @classmethod
    def nonblank(cls, text):
        if not text.strip():
            raise ValueError('Văn bản không được trống')
        return text


class GatewayInput(BaseModel):
    base_url: str = Field(max_length=500)
    api_key: str = Field(min_length=1, max_length=1000)

    @field_validator('base_url')
    @classmethod
    def public_https(cls, value):
        parts = urlsplit(value)
        if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.port not in (None, 443):
            raise ValueError('Gateway cần HTTPS công khai, không credentials/query/port riêng')
        if parts.hostname.lower() == 'localhost':
            raise ValueError('Không hỗ trợ gateway nội bộ')
        try:
            if not ipaddress.ip_address(parts.hostname).is_global:
                raise ValueError('Không hỗ trợ IP nội bộ')
        except ValueError:
            if re.fullmatch(r'[0-9.:]+', parts.hostname):
                raise ValueError('Không hỗ trợ IP nội bộ')
        return value.rstrip('/')


class ModelInput(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    base_url: str = Field(default='', max_length=500)  # Base URL đang có trong form; trống = chỉ đổi model


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=2000)


class ExperimentInput(Input):
    model: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=6)
