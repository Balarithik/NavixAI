"""
CSV import validation module for NavixAI.
"""

from navigation.models import Node


REQUIRED_COLUMNS = ['node_id', 'block', 'name', 'type', 'floor', 'x', 'y', 'qr_code']
ALLOWED_NODE_TYPES = {choice[0] for choice in Node.NODE_TYPES}


class CSVValidationError(Exception):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def validate_csv_rows(rows):
    """
    Validates a list of dictionary rows parsed from the CSV file.
    Returns (clean_rows, errors).
    """
    errors = []
    clean_rows = []
    seen_node_ids = set()
    seen_qr_codes = set()

    for idx, row in enumerate(rows, start=2):  # 1-based, starting after header
        # Check required columns
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in row or not str(row[col]).strip()]
        if missing_cols:
            errors.append(f"Row {idx}: Missing required values for columns: {', '.join(missing_cols)}")
            continue

        node_id = str(row['node_id']).strip()
        block = str(row['block']).strip()
        name = str(row['name']).strip()
        node_type = str(row['type']).strip().lower()
        qr_code = str(row['qr_code']).strip()

        # Check duplicates
        if node_id in seen_node_ids:
            errors.append(f"Row {idx}: Duplicate node_id '{node_id}' found in CSV")
            continue
        seen_node_ids.add(node_id)

        if qr_code in seen_qr_codes:
            errors.append(f"Row {idx}: Duplicate qr_code '{qr_code}' found in CSV")
            continue
        seen_qr_codes.add(qr_code)

        # Validate floor
        try:
            floor_num = int(row['floor'])
            if floor_num < 1:
                errors.append(f"Row {idx}: Floor must be a positive integer, got '{row['floor']}'")
                continue
        except (ValueError, TypeError):
            errors.append(f"Row {idx}: Invalid floor '{row['floor']}', must be an integer")
            continue

        # Validate coordinates
        try:
            x_coord = float(row['x'])
            y_coord = float(row['y'])
        except (ValueError, TypeError):
            errors.append(f"Row {idx}: Invalid coordinates x='{row.get('x')}', y='{row.get('y')}'")
            continue

        # Validate node type
        if node_type not in ALLOWED_NODE_TYPES:
            errors.append(f"Row {idx}: Unknown node type '{node_type}'. Allowed types: {', '.join(sorted(ALLOWED_NODE_TYPES))}")
            continue

        clean_rows.append({
            'node_id': node_id,
            'block': block,
            'name': name,
            'type': node_type,
            'floor': floor_num,
            'x': x_coord,
            'y': y_coord,
            'qr_code': qr_code,
        })

    return clean_rows, errors
