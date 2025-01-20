from abc import ABC, abstractmethod
from typing import List, Dict, Any
import csv
import json
import pandas as pd
from dataclasses import asdict

class BaseExporter(ABC):
    def __init__(self, data: List[Dict[str, Any]], fields: List[str]):
        self.data = data
        self.fields = fields
    
    @classmethod
    def from_json(cls, json_file: str, fields: List[str]):
        """Create exporter instance from JSON file"""
        data = SahibindenJSONImporter.import_file(json_file)
        return cls(data, fields)
        
    def _extract_fields(self, item: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for field in self.fields:
            # Split nested field paths (e.g., "listing.id" -> ["listing", "id"])
            parts = field.split('.')
            value = item
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
            result[field] = value
        return result

    @abstractmethod
    def export(self, output_path: str):
        pass

class CSVExporter(BaseExporter):
    def export(self, output_path: str):
        if not self.data:
            return
            
        extracted_data = [self._extract_fields(item) for item in self.data]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            writer.writeheader()
            writer.writerows(extracted_data)

class ExcelExporter(BaseExporter):
    def export(self, output_path: str):
        if not self.data:
            return
            
        extracted_data = [self._extract_fields(item) for item in self.data]
        df = pd.DataFrame(extracted_data)
        df.to_excel(output_path, index=False)

class JSONExporter(BaseExporter):
    def export(self, output_path: str):
        if not self.data:
            return
            
        extracted_data = [self._extract_fields(item) for item in self.data]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)

class SahibindenValidator:
    """Validates if the JSON data has Sahibinden source identifier"""
    @staticmethod
    def validate(data: List[Dict]) -> bool:
        if not isinstance(data, list) or not data:
            return False
            
        # Check if first item has data source identifier
        first_item = data[0]
        return first_item.get('data_source') == 'Sahibinden'

class SahibindenJSONImporter:
    """Imports JSON data and validates it follows Sahibinden format"""
    @staticmethod
    def import_file(file_path: str) -> List[Dict]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not SahibindenValidator.validate(data):
                raise ValueError("Not a valid Sahibinden data source")
                
            return data
        except Exception as e:
            raise ValueError(f"Error importing JSON file: {e}")

def get_available_fields() -> List[str]:
    """Returns list of all available fields that can be exported"""
    return [
        # Listing fields
        'listing.listing_id',
        'listing.title',
        'listing.size_m2',
        'listing.room_count',
        'listing.price',
        'listing.date',
        'listing.location',
        'listing.image_url',
        'listing.detail_url',
        
        # Property details fields
        'property_details.gross_area',
        'property_details.net_area',
        'property_details.room_count',
        'property_details.building_age',
        'property_details.floor',
        'property_details.total_floors',
        'property_details.heating',
        'property_details.bathroom_count',
        'property_details.balcony',
        'property_details.elevator',
        'property_details.parking',
        'property_details.furnished',
        'property_details.usage_status',
        'property_details.in_complex',
        'property_details.maintenance_fee',
        'property_details.credit_eligible',
        'property_details.deed_status',
        'property_details.listed_by',
        'property_details.exchangeable',
        'property_details.description',
        
        # Contact info fields
        'contact_info.agency_name',
        'contact_info.agent_name',
        'contact_info.office_phone',
        'contact_info.mobile_phone'
    ]
