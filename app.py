from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from PIL import Image
import easyocr
import numpy as np
import io

from database import SessionLocal, engine, Base
from models import Document
from extraction_service import extract_trade_fields

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

reader = easyocr.Reader(['en'], gpu=False)


def run_ocr(image: Image.Image) -> str:
    image_np = np.array(image)
    results = reader.readtext(image_np)
    return " ".join([res[1] for res in results])


def convert_to_inr(value, currency):
    rates = {
        "USD": 83,
        "EUR": 90,
        "GBP": 104
    }
    if value and currency in rates:
        return round(value * rates[currency], 2)
    return None


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.post("/upload/")
async def upload_document(file: UploadFile = File(...)):

    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    raw_text = run_ocr(image)
    extracted = extract_trade_fields(raw_text)

    review_status = "AUTO_APPROVED"
    if not extracted.get("hs_code") or not extracted.get("invoice_value"):
        review_status = "PENDING_REVIEW"

    db: Session = SessionLocal()

    doc = Document(
        hs_code=extracted.get("hs_code"),
        invoice_value=extracted.get("invoice_value"),
        currency=extracted.get("currency"),
        exporter_name=extracted.get("exporter_name"),
        consignee_name=extracted.get("consignee_name"),
        consignee_address=extracted.get("consignee_address"),
        order_date=extracted.get("order_date"),
        order_number=extracted.get("order_number"),
        review_status=review_status
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    converted_value = convert_to_inr(
        extracted.get("invoice_value"),
        extracted.get("currency")
    )

    return {
        "document_id": doc.id,
        "review_status": review_status,
        "converted_value_inr": converted_value,
        "auto_filled_form": extracted
    }