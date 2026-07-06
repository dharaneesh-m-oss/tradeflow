import hmac
import hashlib
import json
import os
import qrcode
from io import BytesIO
from datetime import datetime

# In a production environment, this should be a robust secret from env
SECRET_KEY = os.environ.get("FRAUD_PROTECTION_KEY", "tradeflow-secure-integrity-seal-2026")

def generate_integrity_seal(data: dict, doc_id: str) -> str:
    """
    Generates a cryptographic HMAC signature for the document data.
    """
    # Canonicalize data for consistent hashing
    canonical_data = json.dumps(data, sort_keys=True)
    message = f"{doc_id}|{canonical_data}"
    
    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature

def create_qr_seal(doc_id: str, signature: str) -> BytesIO:
    """
    Generates a QR code image containing the document verification link.
    """
    # In a real app, this would be a public verification URL
    verification_data = {
        "doc_id": doc_id,
        "sig": signature,
        "status": "VERIFIED",
        "timestamp": datetime.now().isoformat()
    }
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(json.dumps(verification_data))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return img_byte_arr

def verify_integrity(data: dict, doc_id: str, signature: str) -> bool:
    """
    Verifies if the data matches the provided cryptographic signature.
    """
    expected_signature = generate_integrity_seal(data, doc_id)
    return hmac.compare_digest(expected_signature, signature)
