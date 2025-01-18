from dataclasses import dataclass
from typing import Optional

@dataclass
class ListingData:
    listing_id: str
    title: str
    size_m2: float
    room_count: str
    price: str
    date: str
    location: str
    image_url: str
    detail_url: str

@dataclass
class PropertyDetails:
    gross_area: float
    net_area: float
    room_count: str
    building_age: str
    floor: str
    total_floors: int
    heating: str
    bathroom_count: int
    balcony: bool
    elevator: bool
    parking: str
    furnished: bool
    usage_status: str
    in_complex: bool
    maintenance_fee: str
    credit_eligible: bool
    deed_status: str
    listed_by: str
    exchangeable: bool
    description: Optional[str] = None

@dataclass
class ContactInfo:
    agency_name: str
    agent_name: str
    office_phone: str
    mobile_phone: str
