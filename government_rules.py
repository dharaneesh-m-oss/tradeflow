import json

with open("rules.json") as f:
    GOVERNMENT_RULES = json.load(f)


def validate_compliance(country: str, data: dict):
    rules = GOVERNMENT_RULES.get(country.lower())
    if not rules:
        return {"status": "UNKNOWN_COUNTRY", "risk_score": 50, "factors": ["Country not in database"]}

    risk_score = 0
    factors = []
    
    hs_code = str(data.get("hs_code", ""))
    exporter = str(data.get("exporter_name", "")).upper()

    # 1. Check HS length
    hs_length = rules.get("hs_length")
    if hs_code and hs_length and len(hs_code) != hs_length:
        risk_score += 30
        factors.append(f"Invalid HS format (Expected {hs_length} digits)")

    # 2. Check restricted codes
    restricted = rules.get("restricted_hs_codes", [])
    if hs_code in restricted:
        risk_score += 60
        factors.append("Restricted/Banned HS Code detected")

    # 3. Check high risk exporters
    high_risk_exporters = [exp.upper() for exp in rules.get("high_risk_exporters", [])]
    if exporter and any(bad_exp in exporter for bad_exp in high_risk_exporters):
        risk_score += 40
        factors.append("High-risk exporter identified in shipment")

    # 4. Value-based verification
    try:
        invoice_val = float(data.get("invoice_value", 0))
        if invoice_val > 50000:
            risk_score += 15
            factors.append("High-value cargo triggers secondary audit")
    except:
        pass

    if risk_score == 0:
        status = "COMPLIANT"
    elif risk_score < 40:
        status = "REVIEW_REQUIRED"
    else:
        status = "HIGH_RISK"

    return {
        "status": status,
        "risk_score": min(risk_score, 100),
        "factors": factors
    }