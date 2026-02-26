import json

with open("form_templates.json", "r") as f:
    FORM_MAP = json.load(f)

def map_to_country(country, data):

    template = FORM_MAP.get(country.upper(), {})
    mapped = {}

    for key, source in template.items():
        mapped[key] = data.get(source, "")

    return mapped