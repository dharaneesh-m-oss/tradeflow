import json
import os

RULES_PATH = "rules.json"

def get_exchange_rates():
    """Mock exchange rates relative to USD."""
    return {
        "USD": 1.0,
        "EUR": 0.92,
        "INR": 83.0,
        "JPY": 150.0,
        "GBP": 0.79,
        "AED": 3.67
    }

def calculate_taxes(value, from_currency, target_country, category="standard"):
    """
    Calculates taxes and duties based on backend rules.
    """
    with open(RULES_PATH) as f:
        rules = json.load(f)
    
    country_rules = rules.get(target_country.lower())
    if not country_rules:
        return None

    rates = get_exchange_rates()
    
    # 1. Convert to Target Currency (or USD as base if target not in rates)
    # For this system, we'll calculate everything in a base unit then display target
    # Let's assume the rules.json tax_rates apply to the value in ANY currency (percentage-based)
    # But for a 'Challan', we need a consistent base. We'll use the 'from_currency' as input
    # and provide the breakdown.
    
    tax_config = country_rules.get("tax_rates", {})
    tax_percentage = tax_config.get(category, 0.10) # default 10%
    
    # If the specific category isn't there, try 'standard' or 'gst' or 'vat'
    if category != "standard" and category not in tax_config:
        tax_percentage = tax_config.get("standard") or tax_config.get("gst") or tax_config.get("vat") or 0.10

    # Basic Custom Duty (Mocking more depth)
    duty_percentage = 0.05 
    if target_country.lower() == "india":
        duty_percentage = 0.10 # BCD
    elif target_country.lower() == "usa":
        duty_percentage = 0.03

    tax_amount = value * tax_percentage
    duty_amount = value * duty_percentage
    total_payable = tax_amount + duty_amount

    return {
        "original_value": value,
        "currency": from_currency,
        "tax_percentage": tax_percentage * 100,
        "tax_amount": round(tax_amount, 2),
        "duty_percentage": duty_percentage * 100,
        "duty_amount": round(duty_amount, 2),
        "total_payable": round(total_payable, 2),
        "target_country": target_country.upper()
    }
