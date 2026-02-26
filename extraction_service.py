import easyocr
import numpy as np
import re

reader = easyocr.Reader(['en'], gpu=False)


def run_ocr(image):
    image_np = np.array(image)
    results = reader.readtext(image_np)

    # Sort primarily by vertical (y) position, secondarily by horizontal (x)
    results.sort(key=lambda x: (x[0][0][1], x[0][0][0]))

    lines_data = []
    for r in results:
        text = r[1].strip()
        if text:
            box = r[0]
            # Calculate horizontal span and center
            x_min = min(pt[0] for pt in box)
            x_max = max(pt[0] for pt in box)
            x_center = (x_min + x_max) / 2
            lines_data.append({
                "text": text,
                "x_min": x_min,
                "x_max": x_max,
                "x_center": x_center,
                "y": box[0][1]
            })

    return lines_data


def get_value(lines_data, label_pattern, multi_line=False):
    """
    Finds a value based on a label or pattern.
    Supports spatial awareness to stay within columns.
    """
    for i, line_obj in enumerate(lines_data):
        line_text = line_obj["text"]
        if re.search(label_pattern, line_text, re.IGNORECASE):
            # Try to find value on the same line after a separator
            parts = re.split(r'[:\-—/]', line_text, maxsplit=1)
            value = ""
            label_x_max = line_obj["x_max"]
            label_x_min = line_obj["x_min"]

            if len(parts) > 1 and parts[1].strip():
                value = parts[1].strip()
            
            if not value or multi_line:
                look_ahead = 1
                while i + look_ahead < len(lines_data):
                    next_obj = lines_data[i + look_ahead]
                    next_text = next_obj["text"].strip()
                    
                    # Stop if we hit something that looks like another label
                    if re.search(r'[:\-—/]', next_text) and len(re.split(r'[:\-—/]', next_text)[0]) < 18:
                        break
                    
                    # Column Filtering: For multi-line, text should roughly align horizontally
                    # Description columns are usually wide, but shouldn't jump across the whole page
                    if multi_line:
                        # If the text is far to the left of the label's start, it's likely a different row/column
                        if next_obj["x_max"] < label_x_min - 50: break
                    
                    if not value:
                        value = next_text
                    elif multi_line:
                        # Noise Reduction: Don't append purely numeric or very short junk from other columns
                        if not (next_text.replace(".", "").isnumeric() and len(next_text) < 8):
                            value += " " + next_text
                    
                    look_ahead += 1
                    if not multi_line: break
            
            if value:
                return value.strip()
    return None


def extract_container_no(text):
    # Standard BIC code: 4 letters + 7 digits
    match = re.search(r'\b([A-Z]{4}\s?\d{7})\b', text.upper())
    return match.group(1).replace(" ", "") if match else None


def extract_hs_code(text):
    # 6 to 10 digits, often space or dot separated
    match = re.search(r'\b(\d{4}[\.\s]?\d{2}[\.\s]?\d{2,4})\b', text)
    if match:
        return re.sub(r'[.\s]', '', match.group(1))
    return None


def extract_weight(val):
    if not val: return None
    # Support more units and comma/dot variations
    match = re.search(r'(\d+[\s.,]?\d*)\s*(KG|KGS|LBS|MT|T|TONS|TNE)?', val.upper())
    if match:
        num = match.group(1).replace(",", "").replace(" ", "")
        unit = match.group(2) or "KG"
        # If it's just a number, ensure it's reasonable (not a year or HS code)
        if len(num) > 8: return None 
        return f"{num} {unit}"
    
    clean_val = re.sub(r'(GROSS|NET|WEIGHT|G\.?W\.?|N\.?W\.?|WGT|[:\-—/])', '', val, flags=re.IGNORECASE).strip()
    return clean_val if clean_val else val


def find_weight_globally(text, type_hint="GROSS"):
    """Searches for weights anywhere in the text block when label-based search fails."""
    # Look for patterns like "G.W. 500 KG" or "GROSS WT: 500"
    patterns = [
        rf"{type_hint}.*?(\d+[\s.,]?\d*)\s*(KG|KGS|MT|LBS|T)?",
        rf"(\d+[\s.,]?\d*)\s*(KG|KGS|MT|LBS|T)\s*{type_hint}?"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num = match.group(1).replace(",", "").replace(" ", "")
            unit = match.group(2) or "KG"
            if 0 < len(num) < 8:
                return f"{num} {unit}"
    return None


def parse_date(text):
    # Look for DD/MM/YYYY, YYYY-MM-DD, DD-MON-YYYY etc.
    match = re.search(r'\b(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4})\b', text)
    if not match:
        match = re.search(r'\b(\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[a-z]*\s+\d{2,4})\b', text, re.IGNORECASE)
    return match.group(1) if match else None


def find_description_globally(lines_data):
    """Advanced fallback: Detects the 'Description' column and extracts only within it."""
    stop_words = ["TOTAL", "QUANTITY", "UNIT", "PRICE", "AMOUNT", "HS CODE", "WEIGHT", "GROSS", "NET", "NW", "GW"]
    for i, line_obj in enumerate(lines_data):
        clean_line = line_obj["text"].strip().upper()
        # Find the Description Header
        if any(lbl in clean_line for lbl in ["DESCRIPTION OF GOODS", "NATURE OF GOODS", "CARGO DESCRIPTION", "PRODUCT DESCRIPTION"]):
            desc = []
            # Establish column bounds
            col_x_min = line_obj["x_min"] - 20
            col_x_max = line_obj["x_max"] + 20
            
            look_ahead = 1
            while i + look_ahead < len(lines_data):
                next_obj = lines_data[i + look_ahead]
                next_text = next_obj["text"].strip()
                
                # Check for column alignment - ONLY capture if it falls within the header's column
                # This is the key to removing noise from other columns
                is_in_column = (next_obj["x_center"] > col_x_min) and (next_obj["x_center"] < col_x_max)
                
                # Stop if it's clearly a different section
                if re.search(r'[:\-—/]', next_text) and len(re.split(r'[:\-—/]', next_text)[0]) < 12:
                    break
                    
                if is_in_column:
                    # Noise Filter: Ignore small numbers or stop words that might be fragments
                    is_noise = any(word in next_text.upper() for word in stop_words) and len(next_text) < 15
                    is_numeric_junk = next_text.replace(".", "").isnumeric() and len(next_text) < 10
                    
                    if not (is_noise or is_numeric_junk) and len(next_text) > 1:
                        desc.append(next_text)
                
                look_ahead += 1
                if look_ahead > 12: break 
            
            if desc:
                # Post-process: Remove accidental duplicates and join
                return " ".join(dict.fromkeys(desc)) # preserve order while removing dupes
    return None


def find_port_globally(text, type_hint="LOADING"):
    """Global search for ports like 'POL: MUMBAI' or 'LOADING PORT: MUNDRA'"""
    patterns = [
        rf"{type_hint}\s*PORT[:\-—/]\s*([A-Z\s,]+)",
        rf"{type_hint}\s*[:\-—/]\s*([A-Z\s,]+)",
        rf"P\.?O\.?L\.?\s*[:\-—/]\s*([A-Z\s,]+)" if type_hint == "LOADING" else rf"P\.?O\.?D\.?\s*[:\-—/]\s*([A-Z\s,]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            # Clean up if it captured too much (e.g. including following labels)
            val = re.split(r'[:\-—/]', val)[0].strip()
            if 3 < len(val) < 30:
                return val
    return None


def extract_trade_fields(lines_data):
    # Flatten text for global searches but keep spatial data for column extraction
    text_block = " ".join([l["text"] for l in lines_data])
    
    # Pre-extract currency
    currency = find_currency(text_block)

    data = {
        "hs_code": extract_hs_code(text_block) or get_value(lines_data, r"HS Code|Harmo[nized]* System|Tariff|Commodity Code"),
        "goods_description": get_value(lines_data, r"Goods Description|Description of( Goods)?|Nature of Goods|Cargo Description|Product Description", multi_line=True) or find_description_globally(lines_data),
        "invoice_value": get_value(lines_data, r"Invoice Value|Total Value|Grand Total|FOB Value|CIF Value|Amount"),
        "currency": currency,
        "importer_name": get_value(lines_data, r"Importer( Name)?|Consignee( Name)?|Buyer"),
        "consignee_name": get_value(lines_data, r"Consignee( Name)?|Deliver to"),
        "exporter_name": get_value(lines_data, r"Exporter( Name)?|Shipper( Name)?|Seller|Vendor"),
        "vessel_name": get_value(lines_data, r"Vessel|Flight|Carrier|Voyage|Truck"),
        "port_of_loading": get_value(lines_data, r"Port of Loading|Loading Port|POL|Departure Port|PORT\s*OF\s*LAD") or find_port_globally(text_block, "LOADING"),
        "arrival_port": get_value(lines_data, r"Arrival Port|Port of Entry|POD|Discharge Port|Destination Port") or find_port_globally(text_block, "ARRIVAL"),
        "net_weight": extract_weight(get_value(lines_data, r"Net\s*Weight|N\.?W\.?|NET\s*WGT|N\.\s*WT")),
        "gross_weight": extract_weight(get_value(lines_data, r"Gross\s*Weight|G\.?W\.?|GROSS\s*WGT|GR\.\s*WT|G\.\s*WT")) or find_weight_globally(text_block, "GROSS"),
        "container_number": extract_container_no(text_block) or get_value(lines_data, r"Container (No|Number)|Seal (No|Number)"),
        "importer_code": get_value(lines_data, r"Importer Code|IEC|VAT|EORI|Tax ID"),
        "country_of_origin": get_value(lines_data, r"Country of Origin|Origin|COO"),
        "date": parse_date(text_block) or get_value(lines_data, r"Date|Declaration Date"),
    }

    # Format numeric value but PRESERVE if it contains the amount
    if data["invoice_value"]:
        raw_val = data["invoice_value"]
        cleaned = clean_number(raw_val)
        if cleaned:
            data["invoice_value"] = cleaned
        else:
            # If clean_number failed, try to extract just the number part manually
            num_match = re.search(r'(\d+[.,]?\d*[.,]?\d*)', str(raw_val))
            if num_match:
                data["invoice_value"] = num_match.group(1).replace(",", "")
            else:
                data["invoice_value"] = raw_val

    filled = sum(1 for v in data.values() if v)
    confidence = round((filled / len(data)) * 100, 2)

    data["review_status"] = "AUTO_PROCESSED" if confidence >= 65 else "MANUAL_REVIEW_REQUIRED"
    data["confidence_score"] = confidence

    return data


def clean_number(val):
    if not val: return None
    # Remove currency symbols and common text
    val_str = str(val).replace(",", "")
    val_str = re.sub(r'[^\d.]', '', val_str)
    try:
        return float(val_str)
    except:
        return None


def find_currency(text):
    match = re.search(r"\b(USD|INR|JPY|EUR|GBP|AUD|CAD|SGD|AED|CNY)\b", text, re.IGNORECASE)
    return match.group(1).upper() if match else "USD"
