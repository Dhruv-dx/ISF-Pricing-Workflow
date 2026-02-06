#!/usr/bin/env python3
"""
InShape Club File Splitter

This script reads the formatted pricing data from inshape_pricing_formatted.txt
and creates separate text files for each club with the filename format {clubname}.txt

Author: AI Assistant
Date: 2025
"""

import os
import re
from typing import List, Dict
from datetime import datetime


class ClubFileSplitter:
    """
    Splits the formatted pricing data into separate files for each club.
    """
    
    def __init__(self, output_directory: str = None):
        self.club_sections = []
        # Use provided output directory or generate with current date
        if output_directory is not None:
            self.output_directory = output_directory
        else:
            current_date = datetime.now().strftime('%d-%m-%y')
            self.output_directory = f"club_files_{current_date}"
    
    def clean_filename(self, club_name: str) -> str:
        """
        Clean club name to create a valid filename.
        """
        # Remove "Club Name: " prefix
        clean_name = club_name.replace("Club Name: ", "")
        
        # Replace invalid filename characters
        clean_name = re.sub(r'[<>:"/\\|?*]', '_', clean_name)
        
        # Replace spaces with underscores
        clean_name = clean_name.replace(' ', '_')
        
        # Remove any trailing dots or spaces
        clean_name = clean_name.strip('. ')
        
        return clean_name
    
    def split_club_sections(self, file_path: str) -> List[Dict[str, str]]:
        """
        Split the formatted file into individual club sections.
        """
        club_sections = []
        current_club = None
        current_content = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            for line in lines:
                line = line.rstrip('\n')
                
                # Check if this is a new club section
                if line.startswith("Club Name: "):
                    # Save previous club if exists
                    if current_club and current_content:
                        club_sections.append({
                            'name': current_club,
                            'content': '\n'.join(current_content)
                        })
                    
                    # Start new club
                    current_club = line
                    current_content = [line]
                
                # Add line to current club content (skip the separator line)
                elif current_club:
                    # Skip the separator line at the end of each club section
                    if line != "================================================================================":
                        current_content.append(line)
            
            # Don't forget the last club
            if current_club and current_content:
                club_sections.append({
                    'name': current_club,
                    'content': '\n'.join(current_content)
                })
        
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            return []
        except Exception as e:
            print(f"Error reading file: {e}")
            return []
        
        return club_sections
    
    def create_output_directory(self):
        """
        Create the output directory if it doesn't exist.
        """
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)
            print(f"Created output directory: {self.output_directory}")
    
    def save_club_files(self, club_sections: List[Dict[str, str]]) -> int:
        """
        Save each club section to a separate file.
        """
        if not club_sections:
            print("No club sections to save.")
            return 0
        
        self.create_output_directory()
        saved_count = 0
        
        for club in club_sections:
            club_name = club['name']
            content = club['content']
            
            # Clean the club name for filename
            filename = self.clean_filename(club_name)
            file_path = os.path.join(self.output_directory, f"{filename}.txt")
            
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                print(f"Saved: {file_path}")
                saved_count += 1
            
            except Exception as e:
                print(f"Error saving {file_path}: {e}")
        
        return saved_count
    
    def process_file(self, input_file: str = None):
        """
        Main method to process the formatted file and create separate club files.
        If input_file is not provided, uses current date to construct filename.
        """
        if input_file is None:
            # Generate filename with current date
            current_date = datetime.now().strftime('%d-%m-%y')
            input_file = f"inshape_pricing_formatted_{current_date}.txt"
        
        print(f"Processing file: {input_file}")
        print("=" * 50)
        
        # Split the file into club sections
        club_sections = self.split_club_sections(input_file)
        
        if not club_sections:
            print("No club sections found in the file.")
            return
        
        print(f"Found {len(club_sections)} clubs:")
        for i, club in enumerate(club_sections, 1):
            club_name = club['name'].replace("Club Name: ", "")
            print(f"{i:2d}. {club_name}")
        
        print("\n" + "=" * 50)
        
        # Save each club to a separate file
        saved_count = self.save_club_files(club_sections)
        
        print(f"\nSuccessfully created {saved_count} club files in '{self.output_directory}' directory.")
        
        # Show some examples of created files
        if saved_count > 0:
            print("\nExample files created:")
            for i, club in enumerate(club_sections[:5], 1):
                filename = self.clean_filename(club['name'])
                print(f"  {i}. {filename}.txt")
            
            if len(club_sections) > 5:
                print(f"  ... and {len(club_sections) - 5} more files")


def main():
    """
    Main function to run the club file splitter.
    """
    print("InShape Club File Splitter")
    print("=" * 50)
    
    # Initialize the splitter
    splitter = ClubFileSplitter()
    
    # Process the formatted file (will use current date if not specified)
    splitter.process_file()


if __name__ == "__main__":
    main()
