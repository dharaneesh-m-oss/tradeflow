import re

def clean_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_company_name(text):
    text = re.sub(r"\bSold by\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bVAT.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_hs_code(text):
    match = re.search(r"\b\d{6,8}\b", text)
    return match.group() if match else None


def extract_invoice_and_currency(text):

    patterns = [
        r"(₹|INR)\s?(\d+(?:\.\d+)?)",
        r"(\$|USD)\s?(\d+(?:\.\d+)?)",
        r"(€|EUR)\s?(\d+(?:\.\d+)?)",
        r"(£|GBP|GBR)\s?(\d+(?:\.\d+)?)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            symbol = match.group(1).upper()
            value = float(match.group(2))

            if symbol in ["₹", "INR"]:
                return value, "INR"
            if symbol in ["$", "USD"]:
                return value, "USD"
            if symbol in ["€", "EUR"]:
                return value, "EUR"
            if symbol in ["£", "GBP", "GBR"]:
                return value, "GBP"

    fallback = re.search(r"(total|amount|payable)\D+(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if fallback:
        value = float(fallback.group(2))
        if "GB" in text.upper() or "UK" in text.upper():
            return value, "GBP"
        return value, None

    return None, None


def extract_exporter(text):
    match = re.search(r"Sold by\s+([A-Z\s&]+)", text, re.IGNORECASE)
    if match:
        return clean_company_name(match.group(1))
    return None


def extract_consignee_name(text):
    match = re.search(r"Delivery address\s+([A-Z\s&]+)", text, re.IGNORECASE)
    if match:
        return clean_company_name(match.group(1))
    return None


def extract_address(text):
    match = re.search(r"\d+\s+[A-Z\s]+,\s*[A-Z\s]+,\s*[A-Z0-9\s]+", text)
    return match.group() if match else None


def extract_order_date(text):
    match = re.search(r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b", text)
    return match.group() if match else None


def extract_order_number(text):
    match = re.search(r"\b\d{3}-\d{7}-\d{7}\b", text)
    return match.group() if match else None


def extract_trade_fields(raw_text):

    text = clean_text(raw_text)

    hs_code = extract_hs_code(text)
    invoice_value, currency = extract_invoice_and_currency(text)
    exporter = extract_exporter(text)
    consignee_name = extract_consignee_name(text)
    address = extract_address(text)
    order_date = extract_order_date(text)
    order_number = extract_order_number(text)

    return {
        "hs_code": hs_code,
        "invoice_value": invoice_value,
        "currency": currency,
        "exporter_name": exporter,
        "consignee_name": consignee_name,
        "consignee_address": address,
        "order_date": order_date,
        "order_number": order_number
    }