import re
import shutil
import csv
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime


def normalize_club_name(name: str) -> str:
    """
    Normalize club name for matching.
    Removes special characters, converts to lowercase, handles spaces/underscores.
    """
    # Remove prefixes like "CFF:", "In-Shape:", etc.
    name = re.sub(r'^(CFF|In-Shape):\s*', '', name, flags=re.IGNORECASE)
    
    # Convert to lowercase and replace underscores/hyphens with spaces
    name = name.lower().replace('_', ' ').replace('-', ' ')
    
    # Remove state names and zip codes (e.g., "california 95355")
    name = re.sub(r'\s+california\s+\d+', '', name)
    name = re.sub(r'\s+ca\s+\d+', '', name)
    
    # Normalize multiple spaces to single space
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def extract_club_name_from_txt(filepath: Path) -> str:
    """Extract club name from text file name."""
    # Get filename without extension
    filename = filepath.stem
    
    # Remove prefix (CFF__ or In-Shape__)
    club_name = re.sub(r'^(CFF__|In-Shape__)', '', filename)
    
    # Replace underscores with spaces
    club_name = club_name.replace('_', ' ')
    
    return club_name


def extract_club_name_from_md(filepath: Path) -> str:
    """Extract club name from markdown file name."""
    # Get filename without extension
    filename = filepath.stem
    
    # Remove prefix and suffix
    filename = re.sub(r'^www\.inshape\.com_gyms_', '', filename)
    filename = re.sub(r'_clean$', '', filename)
    
    # Remove state and zip code patterns
    filename = re.sub(r'-california-\d+', '', filename)
    filename = re.sub(r'-ca-\d+', '', filename)
    
    # Replace hyphens and underscores with spaces
    filename = filename.replace('-', ' ').replace('_', ' ')
    
    return filename


def read_pricing_content_from_csv(csv_filepath: Path, club_name: str) -> Optional[Tuple[str, List[str]]]:
    """
    Read pricing content from CSV file and check for additional columns after Lifestyle Network Plus.
    Returns tuple of (pricing_content, additional_columns_data) where additional_columns_data is a list
    of column names and values if additional columns exist, empty list otherwise.
    """
    try:
        with open(csv_filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Read header row
            
            # Find the index of "Lifestyle Local Network" column (column 17, 0-based index)
            lifestyle_col_idx = None
            for idx, col_name in enumerate(header):
                if 'Lifestyle Local Network' in col_name or 'Lifestyle Network Plus' in col_name:
                    lifestyle_col_idx = idx
                    break
            
            if lifestyle_col_idx is None:
                print(f"  [!] Could not find Lifestyle Network Plus column in CSV")
                return None
            
            # Check if there are columns after Lifestyle Network Plus
            additional_columns = []
            if len(header) > lifestyle_col_idx + 1:
                # There are columns after Lifestyle Network Plus
                for idx in range(lifestyle_col_idx + 1, len(header)):
                    col_name = header[idx].strip()
                    if col_name:  # Only include non-empty column names
                        additional_columns.append((idx, col_name))
            
            # Normalize club name for matching (remove prefixes like "CFF:", "In-Shape:")
            normalized_club_name = normalize_club_name(club_name)
            
            # Read all rows for this club
            club_rows = []
            for row in reader:
                if len(row) > 1:
                    csv_club_name = row[1].strip()
                    normalized_csv_name = normalize_club_name(csv_club_name)
                    # Match if normalized names match
                    if normalized_club_name == normalized_csv_name:
                        club_rows.append(row)
            
            if not club_rows:
                print(f"  [!] Could not find club '{club_name}' in CSV")
                return None
            
            # Build pricing content (similar to text file format)
            pricing_lines = []
            fee_types = [
                "Member Type", "Enrollment 12 M", "Main Dues 12M", "Enrollment MTM",
                "Main Dues MTM", "Add Adult", "Add Youth", "Add Child",
                "Preferred", "Elevate", "Non-EFT Fee", "Credit Card Service Fee"
            ]
            
            # Column indices (0-based)
            add_on_fees_col = 6  # "Add On Fees" column
            local_network_col = 15  # "Basic Local Network"
            fitness_plus_col = 16  # "Fitness Plus Local Network"
            lifestyle_col = 17  # "Lifestyle Local Network"
            
            for fee_type in fee_types:
                # Find row for this fee type
                fee_row = None
                for row in club_rows:
                    if len(row) > add_on_fees_col and row[add_on_fees_col].strip() == fee_type:
                        fee_row = row
                        break
                
                if fee_row:
                    # Extract values
                    local_val = fee_row[local_network_col].strip() if len(fee_row) > local_network_col else ""
                    fitness_val = fee_row[fitness_plus_col].strip() if len(fee_row) > fitness_plus_col else ""
                    lifestyle_val = fee_row[lifestyle_col].strip() if len(fee_row) > lifestyle_col else ""
                    
                    # Format the line
                    pricing_line = f"{fee_type}: Local Network: {local_val or 'Not available'} | Fitness Plus Local Network: {fitness_val or 'Not available'} | Lifestyle Network Plus: {lifestyle_val or 'Not available'}"
                    
                    # Add additional columns if they exist and have values
                    if additional_columns:
                        additional_parts = []
                        for col_idx, col_name in additional_columns:
                            if len(fee_row) > col_idx:
                                col_value = fee_row[col_idx].strip()
                                # Only include if value exists and is not empty
                                if col_value and col_value not in ["", "-", "$-", "$-"]:
                                    # Clean column name for display
                                    clean_col_name = col_name.replace(' - NFC', '').strip()
                                    additional_parts.append(f"{clean_col_name}: {col_value}")
                        
                        if additional_parts:
                            pricing_line += " | " + " | ".join(additional_parts)
                    
                    pricing_lines.append(pricing_line)
            
            pricing_content = "\n".join(pricing_lines)
            
            # Return pricing content and list of additional column names
            additional_col_names = [col_name for _, col_name in additional_columns] if additional_columns else []
            return (pricing_content, additional_col_names)
        
        return None
    except Exception as e:
        print(f"Error reading CSV {csv_filepath}: {e}")
        import traceback
        traceback.print_exc()
        return None


def read_pricing_content_from_txt(filepath: Path) -> Optional[str]:
    """Read pricing content from text file (lines 4-22: Member Type through Availability)."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract content from "Member Type:" through "Availability:" section
        # This captures everything after "Pricing Details:" heading
        match = re.search(r'Member Type:.*?(?=\n\s*$|\Z)', content, re.DOTALL)
        if match:
            pricing_content = match.group(0).strip()
            return pricing_content
        
        return None
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None


def replace_pricing_section_in_md(md_filepath: Path, new_pricing_content: str, club_name: str) -> bool:
    """Replace the pricing content section in markdown file."""
    try:
        with open(md_filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to find the pricing content block:
        # Starts with "Member Type:" and ends with the Availability line
        # This matches the exact pattern from lines 4-22 in the text files
        pattern = r'Member Type:.*?(?:SILVER SNEAKERS|Insurance Availability):.*?(?:available|not available).*?(?:\n(?:Peer Fit|PeerFit):.*?(?:available|not available).*?)?(?=\n\n|\n\[Get Started\]|\Z)'
        
        match = re.search(pattern, content, re.DOTALL)
        if match:
            # Replace the old pricing content with new content
            new_content = content.replace(match.group(0), new_pricing_content)
            
            # Write back to file
            with open(md_filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
        else:
            print(f"  [!] Could not find pricing content pattern in file")
            return False
    
    except Exception as e:
        print(f"Error processing {md_filepath}: {e}")
        return False


def replace_enhancement_fee_text(md_filepath: Path) -> bool:
    """
    Replace all variations of Annual Enhancement Fee text with standardized version.
    Uses a flexible approach to find and replace any text containing:
    - "Annual Enhancement Fee" (case-insensitive)
    - "$49.99" and "$89.98"
    - "$2.99" credit card fee mention
    """
    try:
        with open(md_filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # New standardized enhancement fee text
        new_enhancement_fee_text = """*Annual enhancement fee of $49.95 for the first member and $89.95 for all memberships with two or more persons will be billed 60 days from the join date, then every 12 months thereafter for the duration of the membership. If you choose to use a credit or debit card for your method of payment, additional $4.99 credit card fee added to your dues.

*Amenities and programming vary by location. Monthly retail rebate valid on in-club purchases of drinks, snacks and shakes and excludes day passes and discounted items. Rebate not to exceed monthly dues amount. Relax & Recover available at select clubs. For guest passes, guest must be 18+ and accompany a member. One guest per visit. All access pass is one time per month and expires at the end of the month.

*Reservations are required. A $2 no-show fee will be applied if reservations are not cancelled 2 hours prior."""
        
        # Check if the new text is already present (file was already updated)
        # Look for the unique part of the new text: "$49.95 for the first member"
        if '$49.95 for the first member' in content and '$89.95 for all memberships' in content:
            # Already has the new text, return True (success - already updated)
            return True
        
        # Find the position of "Annual Enhancement Fee" (case-insensitive)
        fee_pos = content.lower().find('annual enhancement fee')
        if fee_pos == -1:
            return False
        
        # Check for generic pattern: "An Annual Enhancement Fee applies" without specific dollar amounts
        # Search in a wider range that includes text before fee_pos (since "An" comes before "Annual")
        search_start = max(0, fee_pos - 50)
        remaining_text = content[search_start:fee_pos+400]
        
        # Check if this is the generic pattern (has "applies" but no dollar amounts)
        has_applies = 'applies' in remaining_text.lower() and 'annual enhancement fee' in remaining_text.lower()
        has_dollar_amounts = '$49.99' in remaining_text or '$89.98' in remaining_text or '$2.99' in remaining_text
        
        if has_applies and not has_dollar_amounts:
            # Found generic pattern - find where "An Annual Enhancement Fee applies" starts
            an_pos = content.lower().find('an annual enhancement fee applies', search_start)
            if an_pos == -1:
                an_pos = fee_pos  # Fallback to fee_pos
            
            # Look backwards to find start (check for "**Note:**" heading)
            before_text = content[max(0, an_pos-200):an_pos]
            note_match = re.search(r'(\*\*Note:\*\*\s*)$', before_text, re.MULTILINE)
            
            if note_match:
                start_pos = an_pos - (len(before_text) - note_match.start())
            else:
                line_start = content.rfind('\n', max(0, an_pos-200), an_pos)
                if line_start != -1:
                    start_pos = line_start + 1
                else:
                    start_pos = max(0, an_pos - 50)
            
            # Find end - look for "Other terms and conditions apply" or link after the generic text
            after_text = content[an_pos:an_pos+300]
            
            preserved_text = ""
            end_pos = an_pos
            
            # Check for "Other terms and conditions apply" or link
            terms_match = re.search(r'(.*?Other\s+terms\s+and\s+conditions\s+apply[^.]*?\.?\s*(?:\[Click\s+here[^\]]*?\]\([^\)]+\))?)', after_text, re.IGNORECASE | re.DOTALL)
            link_match = re.search(r'(.*?\[Click\s+here[^\]]*?\]\([^\)]+\))', after_text, re.IGNORECASE | re.DOTALL)
            
            if terms_match:
                # Extract just the "Other terms" part for preservation
                preserved_match = re.search(r'(Other\s+terms\s+and\s+conditions\s+apply[^.]*?\.?\s*(?:\[Click\s+here[^\]]*?\]\([^\)]+\))?)', terms_match.group(0), re.IGNORECASE | re.DOTALL)
                if preserved_match:
                    preserved_text = "\n\n" + preserved_match.group(1).strip()
                    # End position is where "Other terms" starts
                    end_pos = an_pos + terms_match.start() + terms_match.group(0).find(preserved_match.group(1))
                else:
                    end_pos = an_pos + terms_match.end()
            elif link_match and link_match.start() < 200:
                preserved_match = re.search(r'(\[Click\s+here[^\]]*?\]\([^\)]+\))', link_match.group(0), re.IGNORECASE)
                if preserved_match:
                    preserved_text = "\n\n" + preserved_match.group(1).strip()
                    # End position is where link starts
                    end_pos = an_pos + link_match.start() + link_match.group(0).find(preserved_match.group(1))
                else:
                    end_pos = an_pos + link_match.end()
            else:
                # No "Other terms" or link found - find end of sentences
                end_match = re.search(r'(.*?\.\s*(?:\n|$))', after_text, re.DOTALL)
                if end_match:
                    # Check if there's another sentence
                    next_sentence = re.search(r'(.*?\.\s+.*?\.\s*(?:\n|$))', after_text, re.DOTALL)
                    if next_sentence:
                        end_pos = an_pos + next_sentence.end()
                    else:
                        end_pos = an_pos + end_match.end()
                else:
                    end_pos = an_pos + len(after_text.split('\n')[0]) if '\n' in after_text else len(after_text)
            
            # Perform replacement
            replacement = new_enhancement_fee_text + preserved_text
            new_content = content[:start_pos] + replacement + content[end_pos:]
            
            # Write back
            with open(md_filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
        
        # Check if old pattern "$49.99" exists nearby (within 500 chars) - this indicates old text needs replacement
        amount_pos = content.find('$49.99', fee_pos)
        if amount_pos == -1 or amount_pos > fee_pos + 500:
            # Check if old pattern "$89.98" exists (another indicator of old text)
            if '$89.98' in content[fee_pos:fee_pos+500]:
                # Has old $89.98 pattern, continue with replacement
                pass
            else:
                # No old pattern found - enhancement fee text exists but doesn't match old or new pattern
                # This might be a different format, return False (not found/not replaced)
                return False
        
        # Look backwards to find the start of this section
        # Check for "**Note:**" or "**Additional Fees:**" headings
        before_text = content[max(0, fee_pos-200):fee_pos]
        note_match = re.search(r'(\*\*Note:\*\*\s*)$', before_text, re.MULTILINE)
        additional_match = re.search(r'(\*\*Additional\s+Fees?:\*\*\s*)$', before_text, re.MULTILINE | re.IGNORECASE)
        
        if note_match:
            start_pos = fee_pos - (len(before_text) - note_match.start())
        elif additional_match:
            start_pos = fee_pos - (len(before_text) - additional_match.start())
        else:
            # Look for start of line or bullet point
            line_start = content.rfind('\n', max(0, fee_pos-200), fee_pos)
            if line_start != -1:
                start_pos = line_start + 1
            else:
                start_pos = max(0, fee_pos - 50)
        
        # Now find where this section ends
        # Start from the enhancement fee mention and look for the end
        search_start = fee_pos
        remaining = content[search_start:]
        
        # Try to find end by looking for:
        # 1. Period followed by newline(s) and next content
        # 2. "Other terms and conditions apply"
        # 3. Link pattern
        
        # First check for "Other terms" or link
        terms_pattern = r'.*?(?=\s+Other\s+terms\s+and\s+conditions\s+apply|\[Click\s+here|\n\n#|\Z)'
        terms_match = re.search(terms_pattern, remaining, re.IGNORECASE | re.DOTALL)
        
        if terms_match:
            matched_text = terms_match.group(0)
            # Check if we captured the credit card fee mention
            if '$2.99' in matched_text or 'credit card' in matched_text.lower() or 'debit card' in matched_text.lower():
                end_pos = search_start + len(matched_text)
                # Check what comes after
                after_text = remaining[len(matched_text):len(matched_text)+100]
                preserved_match = re.search(r'(Other\s+terms\s+and\s+conditions\s+apply[^.]*?\.?\s*(?:\[Click\s+here[^\]]*?\]\([^\)]+\))?|\[Click\s+here[^\]]*?\]\([^\)]+\))', after_text, re.IGNORECASE | re.DOTALL)
                if preserved_match:
                    end_pos += preserved_match.end()
                    preserved_text = "\n\n" + preserved_match.group(1).strip()
                else:
                    preserved_text = ""
            else:
                # Need to extend to find credit card fee
                extended_match = re.search(r'.*?\$2\.99.*?(?=\s+Other\s+terms\s+and\s+conditions\s+apply|\[Click\s+here|\n\n#|\Z)', remaining, re.IGNORECASE | re.DOTALL)
                if extended_match:
                    end_pos = search_start + len(extended_match.group(0))
                    after_text = remaining[len(extended_match.group(0)):len(extended_match.group(0))+100]
                    preserved_match = re.search(r'(Other\s+terms\s+and\s+conditions\s+apply[^.]*?\.?\s*(?:\[Click\s+here[^\]]*?\]\([^\)]+\))?|\[Click\s+here[^\]]*?\]\([^\)]+\))', after_text, re.IGNORECASE | re.DOTALL)
                    if preserved_match:
                        end_pos += preserved_match.end()
                        preserved_text = "\n\n" + preserved_match.group(1).strip()
                    else:
                        preserved_text = ""
                else:
                    end_pos = search_start + len(matched_text)
                    preserved_text = ""
        else:
            # Fallback: find end of paragraph/section
            end_match = re.search(r'.*?\.\s*\*?\s*(?:\n\n|\n#|\Z)', remaining, re.DOTALL)
            if end_match:
                matched_text = end_match.group(0)
                if '$2.99' in matched_text or 'credit card' in matched_text.lower() or 'debit card' in matched_text.lower():
                    end_pos = search_start + len(matched_text)
                    preserved_text = ""
                else:
                    # Look for next line with credit card fee
                    next_line_match = re.search(r'.*?\.\s*\*?\s*\n\s*\*?\s*.*?\$2\.99.*?(?:\n\n|\n#|\Z)', remaining, re.IGNORECASE | re.DOTALL)
                    if next_line_match:
                        end_pos = search_start + len(next_line_match.group(0))
                        preserved_text = ""
                    else:
                        end_pos = search_start + len(matched_text)
                        preserved_text = ""
            else:
                # Last resort: replace up to next major break
                end_match = re.search(r'.*?(?=\n\n|\n#|\Z)', remaining, re.DOTALL)
                if end_match:
                    end_pos = search_start + len(end_match.group(0))
                    preserved_text = ""
                else:
                    return False
        
        # Perform replacement
        replacement = new_enhancement_fee_text + preserved_text
        new_content = content[:start_pos] + replacement + content[end_pos:]
        
        # Write back
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    
    except Exception as e:
        print(f"Error replacing enhancement fee text in {md_filepath}: {e}")
        import traceback
        traceback.print_exc()
        return False


def build_club_mapping(txt_dir: Path, md_dir: Path) -> Dict[Path, list]:
    """Build mapping between text files and markdown files based on club names.
    Returns a dictionary where each text file can map to multiple markdown files."""
    mapping = {}
    
    # Special case mappings for files with different naming conventions
    special_mappings = {
        'sports complex': 'rocklin east',
        'east arden': 'carmichael arden',
        'madison': 'madison i 80',
        'sunrise': 'sunrise hwy 50',
        'modesto mchenry': 'modesto mchenry north',
        'suisun': 'suisun city',
        'turlock': 'turlock monte vista',
        'vallejo lincoln rd': 'vallejo lincoln road',
        'victorville': 'victorville north',
        'visalia mooney': 'visalia mooney north',
    }
    
    # Special case: one text file maps to multiple MD files
    multi_mappings = {
        'midtown': ['midtown', 'downtown'],  # Midtown content goes to both files
    }
    
    # Get all text files
    txt_files = list(txt_dir.glob('*.txt'))
    md_files = list(md_dir.glob('*_clean.md'))
    
    # Create normalized name to file mapping for markdown files
    md_name_map = {}
    for md_file in md_files:
        club_name = extract_club_name_from_md(md_file)
        normalized = normalize_club_name(club_name)
        md_name_map[normalized] = md_file
    
    # Match text files to markdown files
    for txt_file in txt_files:
        club_name = extract_club_name_from_txt(txt_file)
        normalized = normalize_club_name(club_name)
        
        # Check for multi-mappings first (one-to-many)
        if normalized in multi_mappings:
            md_file_list = []
            for target_name in multi_mappings[normalized]:
                if target_name in md_name_map:
                    md_file_list.append(md_name_map[target_name])
                else:
                    print(f"Warning: Multi-mapping target '{target_name}' not found for {txt_file.name}")
            if md_file_list:
                mapping[txt_file] = md_file_list
        # Check for direct match
        elif normalized in md_name_map:
            mapping[txt_file] = [md_name_map[normalized]]
        # Check for special case mappings
        elif normalized in special_mappings:
            special_normalized = special_mappings[normalized]
            if special_normalized in md_name_map:
                mapping[txt_file] = [md_name_map[special_normalized]]
            else:
                print(f"Warning: No matching MD file found for {txt_file.name} (normalized: '{normalized}', special: '{special_normalized}')")
        else:
            print(f"Warning: No matching MD file found for {txt_file.name} (normalized: '{normalized}')")
    
    return mapping


def run(
    txt_dir: Optional[Path] = None,
    md_dir: Optional[Path] = None,
    updated_dir: Optional[Path] = None,
    csv_file: Optional[Path] = None,
    project_dir: Optional[Path] = None,
) -> None:
    """
    Process all club files: map TXT pricing files to MD location files,
    copy MD to output dir and update pricing/enhancement fee sections.
    All path args are optional; defaults use project_dir and current date.
    """
    proj = project_dir or Path(__file__).parent
    current_date = datetime.now().strftime('%d-%m-%y')

    txt_dir = txt_dir or proj / f'club_files_{current_date}'
    md_dir = md_dir or proj / 'ISF_locations_22-01-26'
    updated_dir = updated_dir or proj / f'ISF_locations_{current_date}'
    csv_file = csv_file or proj / 'NFC_file.csv'

    # Validate directories exist
    if not txt_dir.exists():
        print(f"Error: Directory not found: {txt_dir}")
        return
    
    if not md_dir.exists():
        print(f"Error: Directory not found: {md_dir}")
        return
    
    # Create updated directory if it doesn't exist
    updated_dir.mkdir(exist_ok=True)
    print(f"Output directory: {updated_dir}")
    
    # Build mapping
    print("\nBuilding club file mappings...")
    mapping = build_club_mapping(txt_dir, md_dir)
    
    print(f"\nFound {len(mapping)} matching club pairs")
    print("-" * 60)
    
    # Process each pair (text file can map to multiple MD files)
    success_count = 0
    failed_count = 0
    total_files_processed = 0

    use_csv = csv_file.exists()
    
    if use_csv:
        print(f"\nCSV file found: {csv_file.name}")
        print("  Will check for additional columns after Lifestyle Network Plus")
    
    for txt_file, md_files in mapping.items():
        club_name = extract_club_name_from_txt(txt_file)
        print(f"\nProcessing: {club_name}")
        print(f"  TXT: {txt_file.name}")
        
        # Try to read from CSV first (to get additional columns), fallback to text file
        pricing_content = None
        additional_columns = []
        
        if use_csv:
            csv_result = read_pricing_content_from_csv(csv_file, club_name)
            if csv_result:
                pricing_content, additional_columns = csv_result
                if additional_columns:
                    print(f"  [✓] Found {len(additional_columns)} additional column(s): {', '.join(additional_columns)}")
                else:
                    print(f"  [i] No additional columns found after Lifestyle Network Plus")
        
        # Fallback to text file if CSV reading failed or not available
        if not pricing_content:
            pricing_content = read_pricing_content_from_txt(txt_file)
        
        if not pricing_content:
            print(f"  [X] Failed to read pricing content")
            failed_count += len(md_files)
            continue
        
        # Process each markdown file associated with this text file
        for md_file in md_files:
            print(f"  MD:  {md_file.name}")
            total_files_processed += 1
            
            # Copy markdown file to updated directory
            updated_md_file = updated_dir / md_file.name
            try:
                shutil.copy2(md_file, updated_md_file)
                print(f"    -> Copied to: {updated_md_file.name}")
            except Exception as e:
                print(f"    [X] Failed to copy file: {e}")
                failed_count += 1
                continue
            
            # Replace section in the copied markdown file
            pricing_success = replace_pricing_section_in_md(updated_md_file, pricing_content, club_name)
            
            # Replace enhancement fee text
            enhancement_fee_success = replace_enhancement_fee_text(updated_md_file)
            
            if pricing_success:
                print(f"    [OK] Successfully updated pricing section")
                success_count += 1
            else:
                print(f"    [X] Failed to update pricing section (section not found)")
                failed_count += 1
            
            if enhancement_fee_success:
                print(f"    [OK] Successfully updated enhancement fee text")
            else:
                print(f"    [!] Could not find enhancement fee text in: {md_file.name}")
    
    # Process all files in updated directory for enhancement fee replacement
    # (in case some files weren't processed in the mapping)
    print("\n" + "=" * 60)
    print("Replacing Annual Enhancement Fee text in all location files...")
    print("=" * 60)
    
    enhancement_fee_success_count = 0
    enhancement_fee_failed_count = 0
    
    for md_file in updated_dir.glob('*_clean.md'):
        if replace_enhancement_fee_text(md_file):
            enhancement_fee_success_count += 1
        else:
            enhancement_fee_failed_count += 1
            print(f"  [!] Could not find enhancement fee text in: {md_file.name}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"SUMMARY:")
    print(f"  Output directory: {updated_dir}")
    print(f"  Text files processed: {len(mapping)}")
    print(f"  Total MD files updated: {total_files_processed}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {failed_count}")
    print()
    print(f"  Enhancement Fee Text Replacement:")
    print(f"  Files processed: {enhancement_fee_success_count + enhancement_fee_failed_count}")
    print(f"  Successful: {enhancement_fee_success_count}")
    print(f"  Failed: {enhancement_fee_failed_count}")
    print("=" * 60)


def main():
    """Entry point: run with default paths (current date, project dir)."""
    run()


if __name__ == "__main__":
    main()