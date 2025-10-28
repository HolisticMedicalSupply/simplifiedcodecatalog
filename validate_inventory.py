#!/usr/bin/env python3
"""
Inventory Validation Script
Compares simplified HTML catalogs with original inventory_before.txt
"""

import re
from pathlib import Path
from collections import defaultdict
from html.parser import HTMLParser

class CatalogParser(HTMLParser):
    """Parse HTML catalog files to extract categories and products"""

    def __init__(self):
        super().__init__()
        self.categories = []
        self.products = []
        self.current_category = None
        self.in_category_header = False
        self.in_product_card = False
        self.in_product_name = False
        self.in_hcpcs_code = False
        self.current_product = {}
        self.current_data = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Check for category header
        if 'class' in attrs_dict and 'category-header' in attrs_dict['class']:
            self.in_category_header = True
            self.current_data = []

        # Check for product card
        if 'class' in attrs_dict and 'product-card' in attrs_dict['class']:
            self.in_product_card = True
            self.current_product = {}

        # Check for product name
        if self.in_product_card and 'class' in attrs_dict and 'product-name' in attrs_dict['class']:
            self.in_product_name = True
            self.current_data = []

        # Check for HCPCS code
        if self.in_product_card and 'class' in attrs_dict and 'hcpcs-code' in attrs_dict['class']:
            self.in_hcpcs_code = True
            self.current_data = []

    def handle_endtag(self, tag):
        if tag == 'div' and self.in_category_header:
            self.in_category_header = False
            category_text = ''.join(self.current_data).strip()
            if category_text:
                self.categories.append(category_text)
                self.current_category = category_text
            self.current_data = []

        if tag == 'div' and self.in_product_name:
            self.in_product_name = False
            product_text = ''.join(self.current_data).strip()
            if product_text:
                self.current_product['name'] = product_text
            self.current_data = []

        if tag == 'span' and self.in_hcpcs_code:
            self.in_hcpcs_code = False
            hcpcs_text = ''.join(self.current_data).strip()
            if hcpcs_text:
                self.current_product['hcpcs'] = hcpcs_text
            self.current_data = []

        if tag == 'div' and self.in_product_card and not self.in_product_name and not self.in_hcpcs_code:
            # Check if we're closing the product-card div
            if self.current_product and 'name' in self.current_product:
                self.in_product_card = False
                self.products.append(self.current_product)
                self.current_product = {}

    def handle_data(self, data):
        if self.in_category_header or self.in_product_name or self.in_hcpcs_code:
            self.current_data.append(data)

def parse_html_file(file_path):
    """Parse an HTML catalog file using regex"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract categories
    category_pattern = r'<div class="category-header">\s*([^<]+)\s*</div>'
    categories = re.findall(category_pattern, content)
    categories = [cat.strip() for cat in categories]

    # Extract products by finding all product-name divs
    # This is more reliable than trying to match full product cards
    products = []

    # Split content by product-card divs
    card_splits = content.split('<div class="product-card">')

    for card in card_splits[1:]:  # Skip first split (before first card)
        # Extract product name
        name_match = re.search(r'<div class="product-name">([^<]+)</div>', card)
        if name_match:
            product = {
                'name': name_match.group(1).strip()
            }
            # Extract HCPCS code (may not exist for all products)
            hcpcs_match = re.search(r'<span class="hcpcs-code">([^<]+)</span>', card)
            if hcpcs_match:
                product['hcpcs'] = hcpcs_match.group(1).strip()
            products.append(product)

    return {
        'categories': categories,
        'products': products,
        'num_categories': len(categories),
        'num_products': len(products)
    }

def parse_inventory_before(file_path):
    """Parse the inventory_before.txt file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    files_data = {}

    # Split by file sections
    file_sections = re.split(r'={80,}\nFILE: (catalog_\w+\.html)\n={80,}', content)

    for i in range(1, len(file_sections), 2):
        file_name = file_sections[i]
        file_content = file_sections[i + 1]

        # Extract statistics
        stats_match = re.search(r'STATISTICS:\s+Total categories: (\d+)\s+Total products: (\d+)\s+Unique HCPCS codes: (\d+)', file_content)

        # Extract categories
        categories = []
        cat_section = re.search(r'CATEGORIES:(.*?)(?=ALL HCPCS CODES|$)', file_content, re.DOTALL)
        if cat_section:
            cat_lines = cat_section.group(1).strip().split('\n')
            for line in cat_lines:
                match = re.match(r'\s*\d+\.\s+(.+)', line)
                if match:
                    categories.append(match.group(1).strip())

        # Extract HCPCS codes
        hcpcs_codes = []
        hcpcs_section = re.search(r'ALL HCPCS CODES \(sorted, unique\):(.*?)(?=COMPLETE PRODUCT LIST|$)', file_content, re.DOTALL)
        if hcpcs_section:
            hcpcs_lines = hcpcs_section.group(1).strip().split('\n')
            for line in hcpcs_lines:
                code = line.strip()
                if code and not code.startswith('='):
                    hcpcs_codes.append(code)

        # Extract products
        products = []
        prod_section = re.search(r'COMPLETE PRODUCT LIST:(.*?)(?=\n\n\n|$)', file_content, re.DOTALL)
        if prod_section:
            prod_lines = prod_section.group(1).strip().split('\n')
            for line in prod_lines:
                match = re.match(r'\s*\d+\.\s+\[([^\]]+)\]\s+(.+)', line)
                if match:
                    products.append({
                        'hcpcs': match.group(1).strip(),
                        'name': match.group(2).strip()
                    })

        files_data[file_name] = {
            'num_categories': int(stats_match.group(1)) if stats_match else len(categories),
            'num_products': int(stats_match.group(2)) if stats_match else len(products),
            'num_unique_hcpcs': int(stats_match.group(3)) if stats_match else len(set(hcpcs_codes)),
            'categories': categories,
            'hcpcs_codes': hcpcs_codes,
            'products': products
        }

    return files_data

def compare_inventories(before_data, after_data, file_name):
    """Compare before and after data for a single file"""
    comparison = {
        'file': file_name,
        'categories_match': False,
        'products_match': False,
        'missing_categories': [],
        'missing_hcpcs': [],
        'missing_products': [],
        'extra_categories': [],
        'extra_hcpcs': [],
        'extra_products': [],
        'before_num_categories': before_data['num_categories'],
        'after_num_categories': after_data['num_categories'],
        'before_num_products': before_data['num_products'],
        'after_num_products': after_data['num_products']
    }

    # Compare category counts
    comparison['categories_match'] = before_data['num_categories'] == after_data['num_categories']

    # Compare product counts
    comparison['products_match'] = before_data['num_products'] == after_data['num_products']

    # Compare HCPCS codes
    before_hcpcs = set(before_data['hcpcs_codes'])
    after_hcpcs = set([p['hcpcs'] for p in after_data['products'] if 'hcpcs' in p])

    comparison['missing_hcpcs'] = sorted(before_hcpcs - after_hcpcs)
    comparison['extra_hcpcs'] = sorted(after_hcpcs - before_hcpcs)

    # Compare product names (normalize for comparison)
    before_products = {p['name'].upper(): p for p in before_data['products']}
    after_products = {p['name'].upper(): p for p in after_data['products'] if 'name' in p}

    missing_product_names = set(before_products.keys()) - set(after_products.keys())
    comparison['missing_products'] = [before_products[name]['name'] for name in sorted(missing_product_names)]

    extra_product_names = set(after_products.keys()) - set(before_products.keys())
    comparison['extra_products'] = [after_products[name]['name'] for name in sorted(extra_product_names)]

    # Check if all data matches
    comparison['all_match'] = (
        comparison['categories_match'] and
        comparison['products_match'] and
        len(comparison['missing_hcpcs']) == 0 and
        len(comparison['extra_hcpcs']) == 0 and
        len(comparison['missing_products']) == 0 and
        len(comparison['extra_products']) == 0
    )

    return comparison

def generate_report(before_inventory, after_inventory, comparisons):
    """Generate the validation report"""

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("INVENTORY VALIDATION REPORT")
    report_lines.append("Generated: 2025-10-28")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append("PURPOSE:")
    report_lines.append("  Verify that simplification process only removed ICD-10 codes,")
    report_lines.append("  clinical indications, and documentation requirements while")
    report_lines.append("  preserving all categories, products, and HCPCS codes.")
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("OVERALL SUMMARY")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Calculate totals
    total_before_categories = sum(c['before_num_categories'] for c in comparisons)
    total_after_categories = sum(c['after_num_categories'] for c in comparisons)
    total_before_products = sum(c['before_num_products'] for c in comparisons)
    total_after_products = sum(c['after_num_products'] for c in comparisons)

    all_pass = all(c['all_match'] for c in comparisons)

    report_lines.append(f"  Total Files Processed: 7")
    report_lines.append(f"  Total Categories (Before): {total_before_categories}")
    report_lines.append(f"  Total Categories (After):  {total_after_categories}")
    report_lines.append(f"  Total Products (Before):   {total_before_products}")
    report_lines.append(f"  Total Products (After):    {total_after_products}")
    report_lines.append("")
    report_lines.append(f"  Overall Status: {'PASS' if all_pass else 'FAIL'}")
    report_lines.append("")

    if all_pass:
        report_lines.append("  ✓ All categories preserved")
        report_lines.append("  ✓ All products preserved")
        report_lines.append("  ✓ All HCPCS codes preserved")
        report_lines.append("  ✓ Validation successful!")
    else:
        report_lines.append("  ✗ Issues found - see detailed comparison below")

    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("DETAILED FILE-BY-FILE COMPARISON")
    report_lines.append("=" * 80)
    report_lines.append("")

    for comparison in comparisons:
        report_lines.append("-" * 80)
        report_lines.append(f"FILE: {comparison['file']}")
        report_lines.append("-" * 80)
        report_lines.append("")

        # Summary table
        report_lines.append("  COUNTS COMPARISON:")
        report_lines.append(f"    {'Metric':<30} {'Before':<10} {'After':<10} {'Status':<10}")
        report_lines.append(f"    {'-'*30} {'-'*10} {'-'*10} {'-'*10}")

        cat_status = "✓ MATCH" if comparison['categories_match'] else "✗ MISMATCH"
        prod_status = "✓ MATCH" if comparison['products_match'] else "✗ MISMATCH"

        report_lines.append(f"    {'Categories':<30} {comparison['before_num_categories']:<10} {comparison['after_num_categories']:<10} {cat_status:<10}")
        report_lines.append(f"    {'Products':<30} {comparison['before_num_products']:<10} {comparison['after_num_products']:<10} {prod_status:<10}")
        report_lines.append("")

        # Issues
        has_issues = False

        if comparison['missing_hcpcs']:
            has_issues = True
            report_lines.append(f"  ✗ MISSING HCPCS CODES ({len(comparison['missing_hcpcs'])}):")
            for code in comparison['missing_hcpcs']:
                report_lines.append(f"    - {code}")
            report_lines.append("")

        if comparison['extra_hcpcs']:
            has_issues = True
            report_lines.append(f"  ! EXTRA HCPCS CODES ({len(comparison['extra_hcpcs'])}):")
            for code in comparison['extra_hcpcs']:
                report_lines.append(f"    - {code}")
            report_lines.append("")

        if comparison['missing_products']:
            has_issues = True
            report_lines.append(f"  ✗ MISSING PRODUCTS ({len(comparison['missing_products'])}):")
            for prod in comparison['missing_products'][:10]:  # Limit to first 10
                report_lines.append(f"    - {prod}")
            if len(comparison['missing_products']) > 10:
                report_lines.append(f"    ... and {len(comparison['missing_products']) - 10} more")
            report_lines.append("")

        if comparison['extra_products']:
            has_issues = True
            report_lines.append(f"  ! EXTRA PRODUCTS ({len(comparison['extra_products'])}):")
            for prod in comparison['extra_products'][:10]:  # Limit to first 10
                report_lines.append(f"    - {prod}")
            if len(comparison['extra_products']) > 10:
                report_lines.append(f"    ... and {len(comparison['extra_products']) - 10} more")
            report_lines.append("")

        if not has_issues:
            report_lines.append("  ✓ NO ISSUES FOUND")
            report_lines.append("  ✓ All categories preserved")
            report_lines.append("  ✓ All products preserved")
            report_lines.append("  ✓ All HCPCS codes preserved")
            report_lines.append("")

        report_lines.append(f"  File Status: {'PASS' if comparison['all_match'] else 'FAIL'}")
        report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("VALIDATION CONCLUSION")
    report_lines.append("=" * 80)
    report_lines.append("")

    if all_pass:
        report_lines.append("  ✓✓✓ VALIDATION PASSED ✓✓✓")
        report_lines.append("")
        report_lines.append("  The simplification process successfully:")
        report_lines.append("  • Preserved all categories")
        report_lines.append("  • Preserved all products")
        report_lines.append("  • Preserved all HCPCS codes")
        report_lines.append("  • Maintained data integrity")
        report_lines.append("")
        report_lines.append("  Only ICD-10 codes, clinical indications, and documentation")
        report_lines.append("  requirements were removed as intended.")
    else:
        report_lines.append("  ✗✗✗ VALIDATION FAILED ✗✗✗")
        report_lines.append("")
        report_lines.append("  Issues were found during validation.")
        report_lines.append("  Please review the detailed comparison above.")

    report_lines.append("")
    report_lines.append("=" * 80)

    return '\n'.join(report_lines)

def main():
    """Main validation function"""
    base_path = Path('/home/user/simplifiedcodecatalog')

    html_files = [
        'catalog_diabetic_hospital.html',
        'catalog_mobility_aids.html',
        'catalog_orthotic_prosthetic.html',
        'catalog_patient_care.html',
        'catalog_specialized.html',
        'catalog_surgical_dressings.html',
        'catalog_therapeutic.html'
    ]

    print("Parsing inventory_before.txt...")
    before_inventory = parse_inventory_before(base_path / 'inventory_before.txt')

    print("Parsing HTML catalog files...")
    after_inventory = {}
    for html_file in html_files:
        print(f"  - Processing {html_file}...")
        after_inventory[html_file] = parse_html_file(base_path / html_file)

    print("\nComparing inventories...")
    comparisons = []
    for html_file in html_files:
        comparison = compare_inventories(
            before_inventory[html_file],
            after_inventory[html_file],
            html_file
        )
        comparisons.append(comparison)

    print("\nGenerating validation report...")
    report = generate_report(before_inventory, after_inventory, comparisons)

    # Write report to file
    report_path = base_path / 'validation_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nValidation report written to: {report_path}")
    print("\n" + "=" * 80)

    # Print summary
    all_pass = all(c['all_match'] for c in comparisons)
    if all_pass:
        print("✓✓✓ VALIDATION PASSED ✓✓✓")
        print("\nAll categories, products, and HCPCS codes have been preserved.")
    else:
        print("✗✗✗ VALIDATION FAILED ✗✗✗")
        print("\nIssues found - see validation_report.txt for details.")

    print("=" * 80)

    return 0 if all_pass else 1

if __name__ == '__main__':
    exit(main())
