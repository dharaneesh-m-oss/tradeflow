import json

def map_form(country, extracted):

    try:
        with open("form_templates.json", "r") as f:
            templates = json.load(f)
    except:
        return {}

    template = templates.get(country, {})

    return {
        field: extracted.get(source)
        for field, source in template.items()
    }