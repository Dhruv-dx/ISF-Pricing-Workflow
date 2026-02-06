#!/usr/bin/env python3
"""
InShape Pricing Data Formatter

This script processes the gym pricing data from Book2 (2).csv and formats it
according to the specification in Inshape_pricing_doc 1.txt.

Author: AI Assistant
Date: 2025
"""

import csv
import sys
from typing import Dict, List, Set
from collections import defaultdict, OrderedDict
from datetime import datetime


class InShapePricingFormatter:
    """
    Formats InShape pricing data from CSV to the specified text format.
    """
    
    def __init__(self):
        # Column mappings based on CSV header
        self.pricing_columns = {
            "One Club": 12,
            "Local Network": 13, 
            "Lifestyle Network Plus": 14
        }
        
        # Special programs columns (0-based indexing)
        self.programs = {
            "SILVER SNEAKERS": 25,
            "ASH": 26,  # Legacy - kept for backward compatibility
            "ASH - Standard": 26,
            "ASH - Premium": 27,
            "OPTUM RENEW": 31,  # OPTUM Renew - NFC
            "Optum - Classic Core": 29,
            "Optum - Premium Elite": 30,
            "Peer Fit": 32
        }
        
        # Fee type mappings for pricing details
        self.fee_types = [
            "Member Type",
            "Enrollment 12 M",
            "Main Dues 12M", 
            "Enrollment MTM",
            "Main Dues MTM",
            "Add Adult",
            "Add Youth", 
            "Add Child",
            "Preferred",
            "Elevate",
            "Non-EFT Fee",
            "Credit Card Service Fee"
        ]
        
    def clean_price(self, value: str) -> str:
        """Clean and format price values."""
        if not value or value.strip() == "" or value.strip() == "-":
            return "Not available"
        
        # Remove whitespace and clean the value
        value = value.strip()
        
        # Handle special cases
        if value == "$-":
            return "Not available"
        if value == "$":
            return "Not available"
        
        # Keep the value as is if it's already formatted
        return value
    
    def get_network_clubs(self, local_access: str, local_name: str, club_name: str, all_clubs: Dict) -> List[str]:
        """Get list of clubs in the same network based on local name."""
        if not local_name or local_name == "NA":
            return []
        
        # Find all clubs with the same local_name (network)
        network_clubs = []
        for club_id, club_data in all_clubs.items():
            if club_data.get('local_name') == local_name:
                network_clubs.append(club_data['name'])
        
        return sorted(network_clubs)
    
    def get_program_availability(self, rows: List[List[str]], available_programs: Dict[str, int]) -> Dict[str, str]:
        """Extract program availability information from all rows for a club.
        Only checks programs that exist in the CSV."""
        availability = {}
        
        # Only check programs that exist in the CSV
        for program, col_idx in available_programs.items():
            availability[program] = "not available"
            
            for row in rows:
                if col_idx < len(row):
                    value = row[col_idx].strip()
                    # Look for actual price values (containing $ and digits) or any non-empty value
                    if value and (("$" in value and any(c.isdigit() for c in value)) or (value != "" and value != "-")):
                        availability[program] = "available"
                        break
                        
        return availability
    
    def detect_availability_columns(self, headers: List[str]) -> Dict[str, int]:
        """Detect which availability/program columns exist in the CSV header.
        Only matches exact program names to avoid false positives."""
        detected_programs = {}
        
        # Map of program names to their exact header patterns
        # These must match exactly or be the main part of the column name
        program_exact_matches = {
            "SILVER SNEAKERS": ["silver sneakers"],
            "ASH - Standard": ["ash - standard", "ash standard"],
            "ASH - Premium": ["ash - premium", "ash premium"],
            "Optum - Classic Core": ["optum - classic core", "optum classic core"],
            "Optum - Premium Elite": ["optum - premium elite", "optum premium elite"],
            "OPTUM RENEW": ["optum renew", "optum renew - nfc"],
            "Peer Fit": ["peer fit", "peerfit"]
        }
        
        # Check each header column for exact program name matches
        for idx, header in enumerate(headers):
            header_clean = header.strip()
            header_lower = header_clean.lower()
            
            for program_name, exact_patterns in program_exact_matches.items():
                # Skip if already detected
                if program_name in detected_programs:
                    continue
                    
                # Check for exact matches - the header must contain the full program name
                for pattern in exact_patterns:
                    pattern_lower = pattern.lower()
                    # Must be exact match or the header must start/end with the pattern
                    # This prevents matching "Total Soccer Academy Silver" with "SILVER SNEAKERS"
                    if (pattern_lower == header_lower or
                        header_lower == pattern_lower or
                        header_lower.startswith(pattern_lower + " -") or
                        header_lower.startswith(pattern_lower + " ") or
                        header_lower.endswith(" - " + pattern_lower) or
                        header_lower.endswith(" " + pattern_lower)):
                        # Additional check: make sure it's not a false match
                        # For "silver sneakers", reject if header contains "soccer" or "academy"
                        if "silver sneakers" in pattern_lower:
                            if "soccer" in header_lower or "academy" in header_lower:
                                continue
                        detected_programs[program_name] = idx
                        break
        
        return detected_programs
    
    def process_csv_file(self, csv_file_path: str) -> str:
        """Process the CSV file and return formatted output."""
        all_clubs = {}
        club_data_by_name = defaultdict(list)
        availability_programs = {}  # Will be set after reading header
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                headers = next(csv_reader)  # Read header row
                
                # Detect which availability columns exist in the CSV
                availability_programs = self.detect_availability_columns(headers)
                
                for row in csv_reader:
                    if len(row) < 15:  # Ensure minimum required columns
                        continue
                    
                    club_id = row[0].strip()
                    club_name = row[1].strip()
                    club_level = row[2].strip()
                    local_name = row[3].strip()
                    local_access = row[4].strip()
                    elevate_offering = row[5].strip()
                    fee_type = row[6].strip()
                    
                    if not club_name or club_name == "Club Name":
                        continue
                    
                    # Store club basic info
                    if club_id not in all_clubs:
                        all_clubs[club_id] = {
                            'name': club_name,
                            'level': club_level,
                            'local_name': local_name,
                            'local_access': local_access,
                            'elevate_offering': elevate_offering
                        }
                    
                    # Store pricing data by fee type
                    club_data_by_name[club_name].append(row)
        
        except FileNotFoundError:
            return f"Error: File '{csv_file_path}' not found."
        except Exception as e:
            return f"Error processing file: {str(e)}"
        
        # Generate formatted output
        output_lines = []
        
        for club_name in sorted(club_data_by_name.keys()):
            rows = club_data_by_name[club_name]
            if not rows:
                continue
            
            # Get club basic info from first row
            first_row = rows[0]
            club_id = first_row[0].strip()
            club_level = first_row[2].strip()
            local_name = first_row[3].strip()
            local_access = first_row[4].strip()
            elevate_offering = first_row[5].strip()
            
            output_lines.append(f"Club Name: {club_name}")
            output_lines.append("")
            output_lines.append("Pricing Details:")
            
            # Process each fee type
            fee_data = {}
            
            for row in rows:
                if len(row) < 15:
                    continue
                    
                fee_type = row[6].strip()
                
                # Special handling for Member Type row (shows membership codes, not prices)
                if fee_type == "Member Type":
                    one_club = row[12].strip() if len(row) > 12 and row[12].strip() else "Not available"
                    local_network = row[13].strip() if len(row) > 13 and row[13].strip() else "Not available"  
                    lifestyle_plus = row[14].strip() if len(row) > 14 and row[14].strip() else "Not available"
                else:
                    # Get pricing for each membership type
                    one_club = self.clean_price(row[12]) if len(row) > 12 else "Not available"
                    local_network = self.clean_price(row[13]) if len(row) > 13 else "Not available"  
                    lifestyle_plus = self.clean_price(row[14]) if len(row) > 14 else "Not available"
                
                fee_data[fee_type] = {
                    "One Club": one_club,
                    "Local Network": local_network,
                    "Lifestyle Network Plus": lifestyle_plus
                }
            
            # Get program availability from all rows for this club (only for programs that exist in CSV)
            program_availability = self.get_program_availability(rows, availability_programs)
            
            # Output pricing details in the specified order
            for fee_type in self.fee_types:
                if fee_type in fee_data:
                    data = fee_data[fee_type]
                    output_lines.append(
                        f"{fee_type}: One Club: {data['One Club']} | "
                        f"Local Network: {data['Local Network']} | "
                        f"Lifestyle Network Plus: {data['Lifestyle Network Plus']}"
                    )
            
            output_lines.append("")
            
            # Add network information
            network_clubs = self.get_network_clubs(local_access, local_name, club_name, all_clubs)
            if local_name and local_name != "NA":
                # Include the current club in the "Other Clubs" list
                other_clubs_str = ", ".join(network_clubs) if network_clubs else ""
                output_lines.append(f"Network Name: {local_name} (Other Clubs: {other_clubs_str})")
            else:
                output_lines.append("Network Name: Not available (Other Clubs: )")
            
            # Add elevate offering
            if elevate_offering and elevate_offering.strip() not in ["", "NA", "Not available"]:
                output_lines.append(f"Elevate Offering: {elevate_offering.strip()}")
            else:
                output_lines.append("Elevate Offering: Not available")
            
            output_lines.append("")
            
            # Add program availability (only if programs exist in CSV)
            if availability_programs:
                availability_parts = []
                # Order: SILVER SNEAKERS, ASH - Standard, ASH - Premium, Optum - Classic Core, Optum - Premium Elite, OPTUM RENEW, Peer Fit
                # Only include programs that were detected in the CSV
                program_order = ["SILVER SNEAKERS", "ASH - Standard", "ASH - Premium", "Optum - Classic Core", "Optum - Premium Elite", "OPTUM RENEW", "Peer Fit"]
                for program in program_order:
                    if program in availability_programs:
                        status = program_availability.get(program, "not available")
                        availability_parts.append(f"{program}: {status}")
                
                if availability_parts:
                    output_lines.append("Availability:")
                    output_lines.append(" | ".join(availability_parts))
            
            output_lines.append("=" * 80)
            output_lines.append("")
        
        return "\n".join(output_lines)
    
    def save_output(self, formatted_data: str, output_file: str = "formatted_pricing.txt"):
        """Save the formatted output to a file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write(formatted_data)
            print(f"Formatted data saved to '{output_file}'")
        except Exception as e:
            print(f"Error saving file: {str(e)}")


def main():
    """Main function to run the formatter."""
    formatter = InShapePricingFormatter()
    
    # Process the CSV file
    csv_file = "ISS Pricing 01292026.csv"
    formatted_output = formatter.process_csv_file(csv_file)
    
    if formatted_output.startswith("Error"):
        print(formatted_output)
        sys.exit(1)
    
    # Save to output file with date in filename
    current_date = datetime.now().strftime('%d-%m-%y')
    output_file = f"inshape_pricing_formatted_{current_date}.txt"
    formatter.save_output(formatted_output, output_file)
    
    # Also print first few clubs as preview
    lines = formatted_output.split('\n')
    preview_lines = []
    club_count = 0
    
    for line in lines:
        preview_lines.append(line)
        if line.startswith("=" * 80):
            club_count += 1
            if club_count >= 3:  # Show first 3 clubs as preview
                break
    
    print("\nPreview of formatted output (first 3 clubs):")
    print("=" * 50)
    print('\n'.join(preview_lines))
    print(f"\nFull output saved to '{output_file}'")


if __name__ == "__main__":
    main()
