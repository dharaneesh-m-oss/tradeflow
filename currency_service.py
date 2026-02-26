# Simple static currency conversion (Hackathon Safe Version)

EXCHANGE_RATES = {
    "USD": 83.0,
    "EUR": 90.0,
    "GBP": 105.0,
    "JPY": 0.55,
    "INR": 1.0
}


def convert_currency(amount, currency):
    if not amount or not currency:
        return None

    currency = currency.upper()

    rate = EXCHANGE_RATES.get(currency)

    if not rate:
        return None

    return round(amount * rate, 2)