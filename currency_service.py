import requests

def convert_currency(amount, from_currency, to_currency="INR"):

    if not amount or not from_currency:
        return None

    try:
        response = requests.get(
            "https://api.exchangerate.host/convert",
            params={
                "from": from_currency,
                "to": to_currency,
                "amount": amount
            },
            timeout=4
        )

        data = response.json()
        result = data.get("result")

        return round(result, 2) if result else None

    except:
        return None