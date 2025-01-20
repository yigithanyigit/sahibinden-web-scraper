import argparse
from typing import Dict, Any
from exporters import get_available_fields

def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    
    # Scraping arguments
    parser.add_argument("--url", help="URL to scrape")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--max_pages", type=int, default=1, help="Maximum pages to scrape")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between requests")
    
    # Export arguments
    parser.add_argument("--export", choices=['csv', 'excel', 'json'], help="Export format")
    parser.add_argument("--export-file", help="Export file path")
    parser.add_argument("--fields", nargs='+', help="Fields to export")
    parser.add_argument("--list-fields", action="store_true", help="List available fields")
    
    # State management
    parser.add_argument("--state", help="State file to save/load")
    parser.add_argument("--resume", action="store_true", help="Resume from state file")
    
    return parser

def get_scraper_args(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        'max_pages': args.max_pages,
        'delay': args.delay,
        'headless': args.headless
    }

def handle_export_args(args: argparse.Namespace):
    if args.list_fields:
        print("\nAvailable fields for export:")
        for field in get_available_fields():
            print(f"  - {field}")
        return True
    return False
