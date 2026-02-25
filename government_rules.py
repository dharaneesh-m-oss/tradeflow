import json

def load_rules():
    try:
        with open("rules.json", "r") as f:
            return json.load(f)
    except:
        return {}

def check_compliance(hs_code, country):
    rules = load_rules()

    if not hs_code or not country:
        return {"allowed": False, "message": "Insufficient data"}

    if country not in rules:
        return {"allowed": True, "message": "No restrictions found"}

    restricted = rules[country].get("restricted_hs", [])

    if hs_code in restricted:
        return {"allowed": False, "message": "Restricted under customs rule"}

    return {"allowed": True, "message": "Allowed"}