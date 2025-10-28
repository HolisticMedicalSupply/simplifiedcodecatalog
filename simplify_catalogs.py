#!/usr/bin/env python3
"""
Script to simplify catalog HTML files by removing ICD-10, clinical indications,
and documentation requirements, keeping only product names and HCPCS codes.
"""

import re
import sys
from pathlib import Path


def simplify_html(content):
    """
    Simplify HTML by removing unnecessary sections from product cards.
    """

    # Remove ICD-10 code rows (entire div with class code-row containing ICD-10)
    # Match from the opening div to its closing div
    content = re.sub(
        r'<div class="code-row">\s*<div class="code-label">ICD-10 Codes</div>.*?</div>\s*</div>',
        '',
        content,
        flags=re.DOTALL
    )

    # Remove clinical-box divs
    content = re.sub(
        r'<div class="clinical-box">.*?</div>',
        '',
        content,
        flags=re.DOTALL
    )

    # Remove med-necessity divs
    content = re.sub(
        r'<div class="med-necessity">.*?</div>',
        '',
        content,
        flags=re.DOTALL
    )

    # Remove CSS styles for deleted elements
    # Remove .clinical-box styles
    content = re.sub(
        r'\.clinical-box\s*\{[^}]*\}',
        '',
        content,
        flags=re.DOTALL
    )

    # Remove .med-necessity styles
    content = re.sub(
        r'\.med-necessity\s*\{[^}]*\}',
        '',
        content,
        flags=re.DOTALL
    )

    # Adjust product card padding/spacing for cleaner look
    content = re.sub(
        r'(\.product-card\s*\{[^}]*padding:\s*)\d+px',
        r'\g<1>15px',
        content
    )

    # Ensure proper page break settings for PDF
    content = re.sub(
        r'(\.product-card\s*\{[^}]*)(page-break-inside:\s*[^;]+;)',
        r'\g<1>page-break-inside: avoid;',
        content
    )

    # Add page-break-inside: avoid if not present in product-card
    if 'page-break-inside' not in re.search(r'\.product-card\s*\{[^}]*\}', content, re.DOTALL).group(0):
        content = re.sub(
            r'(\.product-card\s*\{)',
            r'\g<1>\n            page-break-inside: avoid;',
            content
        )

    # Clean up excessive whitespace
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

    return content


def process_file(filepath):
    """
    Process a single HTML file.
    """
    print(f"Processing {filepath.name}...")

    try:
        # Read the file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_size = len(content)

        # Simplify the content
        simplified = simplify_html(content)

        new_size = len(simplified)
        reduction = ((original_size - new_size) / original_size) * 100

        # Write back to the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(simplified)

        print(f"  ✓ Completed: Reduced from {original_size:,} to {new_size:,} bytes ({reduction:.1f}% reduction)")

        return True

    except Exception as e:
        print(f"  ✗ Error processing {filepath.name}: {e}")
        return False


def main():
    """
    Main function to process all catalog files.
    """
    base_path = Path('/home/user/simplifiedcodecatalog')

    # List of catalog files to process
    catalog_files = [
        'catalog_diabetic_hospital.html',
        'catalog_mobility_aids.html',
        'catalog_orthotic_prosthetic.html',
        'catalog_patient_care.html',
        'catalog_specialized.html',
        'catalog_surgical_dressings.html',
        'catalog_therapeutic.html',
    ]

    print("=" * 60)
    print("CATALOG SIMPLIFICATION SCRIPT")
    print("=" * 60)
    print()

    success_count = 0
    total_count = len(catalog_files)

    for filename in catalog_files:
        filepath = base_path / filename
        if filepath.exists():
            if process_file(filepath):
                success_count += 1
        else:
            print(f"  ✗ File not found: {filename}")

    print()
    print("=" * 60)
    print(f"SUMMARY: {success_count}/{total_count} files processed successfully")
    print("=" * 60)

    return success_count == total_count


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
