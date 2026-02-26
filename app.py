import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image
import io
import easyocr
import numpy as np
import re
from extraction_service import run_ocr, extract_trade_fields
from government_rules import validate_compliance, GOVERNMENT_RULES
from calculator_service import calculate_taxes
from report_generator import generate_docx, generate_pdf, generate_challan
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
print(f"DEBUG: API Key Loaded: {'Yes' if os.environ.get('OPENAI_API_KEY') else 'No'}")
client = OpenAI()

app = FastAPI()

# ===============================
# FOLDERS SETUP
# ===============================
UPLOAD_DIR = "uploads"
GENERATED_DIR = "generated"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

# Mount static
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/files", StaticFiles(directory=GENERATED_DIR), name="files")

# ===============================
# OCR SETUP
# ===============================
reader = easyocr.Reader(['en'], gpu=False)

# Removed local helpers, using extraction_service instead


@app.get("/api/rules-updates/")
def get_rules_updates():
    return GOVERNMENT_RULES.get("updates", [])


# ===============================
# ROUTES – PAGES
# ===============================

@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.get("/app")
def app_page():
    return FileResponse("static/app.html")


@app.get("/about")
def about_page():
    return FileResponse("static/about.html")


@app.get("/rules")
def rules_page():
    return FileResponse("static/rules.html")


@app.get("/manual")
def manual_page():
    return FileResponse("static/manual.html")


@app.get("/calculator")
def calculator_page():
    return FileResponse("static/calculator.html")


@app.get("/login")
def login_page():
    return FileResponse("static/login.html")


@app.post("/api/manual-entry/")
async def manual_entry(data: dict):
    # This endpoint will mirror the upload processing but with direct data
    compliance_results = {}
    # Dynamically validate against all countries in the rules engine
    countries_to_check = list(GOVERNMENT_RULES.keys())
    # Remove 'updates' if it exists in keys
    if "updates" in countries_to_check:
        countries_to_check.remove("updates")

    for country in countries_to_check:
        compliance_results[country] = validate_compliance(country, data)
    
    return {
        "document_id": 999,
        "data": data,
        "compliance": compliance_results
    }


# ===============================
# UPLOAD + OCR
# ===============================

@app.post("/upload/")
async def upload_document(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Using the improved extraction service
        ocr_lines = run_ocr(image)
        extracted = extract_trade_fields(ocr_lines)

        # Default compliance check for all configured countries
        compliance_results = {}
        countries_to_check = [c for c in GOVERNMENT_RULES.keys() if c != "updates"]
        for country in countries_to_check:
            compliance_results[country] = validate_compliance(country, extracted)

        return {
            "document_id": 1, 
            "data": extracted,
            "compliance": compliance_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===============================
# REQUEST MODEL
# ===============================

class GenerateRequest(BaseModel):
    country: str
    importer_code: str | None = None
    arrival_port: str | None = None
    country_of_origin: str | None = None
    exporter_name: str | None = None
    vessel_name: str | None = None
    data: dict | None = None


class ChatRequest(BaseModel):
    message: str
    context: dict | None = None
    history: list[dict] | None = []


# ===============================
# AI CHAT ASSISTANCE
# ===============================

@app.post("/chat/")
async def chat_assistance(request: ChatRequest):
    try:
        system_prompt = (
            "You are TradeFlow AI, an expert customs and trade compliance assistant. "
            "Help users understand trade documents, HS codes, compliance risks, and customs procedures. "
            "Be professional, concise, and accurate."
        )
        
        user_message = request.message
        if request.context:
            user_message = f"Context: {request.context}\n\nUser Question: {request.message}"

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history (limit to last 10 messages for efficiency)
        if request.history:
            messages.extend(request.history[-10:])
            
        # Add current message with context
        messages.append({"role": "user", "content": user_message})

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                timeout=10.0
            )
            return {"response": response.choices[0].message.content}
        except Exception as api_error:
            print(f"DEBUG: OpenAI API Error (Fallback Triggered): {str(api_error)}")
            return {"response": get_local_fallback_response(request.message, request.context)}

    except Exception as e:
        print(f"DEBUG: Critical Chat Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI Chat error: {str(e)}")


def get_local_fallback_response(message: str, context: dict | None) -> str:
    """Provides a dynamic, varied response if the AI API is unavailable."""
    msg = message.lower()
    
    import random
    fallbacks = [
        "I'm operating in emergency local mode right now. ",
        "My advanced brain is resting, but I've got the facts for you. ",
        "Quick update from the local trade engine: ",
        "Here's what I've found in your current document: "
    ]
    prefix = random.choice(fallbacks)

    if not context:
        return prefix + "I can help much more if you upload a trade document or use the manual entry form first!"

    data = context
    if "data" in context:
        data = context["data"]

    if any(k in msg for k in ["hs", "code", "hsn"]):
        return f"{prefix}The detected HS Code is {data.get('hs_code', 'not assigned')}. Remember to verify this against the {data.get('target_country', 'target')} tariff schedule."
    
    if any(k in msg for k in ["risk", "compliance", "safe", "status"]):
        return f"{prefix}Current compliance profile: {data.get('review_status', 'PRELIMINARY')}. Risk Score: {data.get('risk_score', 'N/A')}/100. Always check the restricted HS list in Rules."

    if any(k in msg for k in ["value", "price", "invoice", "cost"]):
        return f"{prefix}Your invoice shows a value of {data.get('invoice_value', 'unspecified')} {data.get('currency', '')}."

    return (
        f"{prefix}I see we're discussing a shipment for {data.get('importer_name', 'a client')} "
        f"concerning {data.get('goods_description', 'goods')} from {data.get('country_of_origin', 'an unknown origin')}. "
        "I'm temporarily limited in complex reasoning, but I can confirm your document fields are extracted!"
    )


# ===============================
# GENERATE DOCUMENT
# ===============================

@app.post("/generate/{doc_id}")
def generate_document(doc_id: int, request: GenerateRequest):

    if not request.country:
        raise HTTPException(status_code=400, detail="Country required")

    # Use provided data or fallback to empty dict
    extracted_data = request.data or {}
    
    # Merge custom user inputs with priority
    if request.importer_code: extracted_data["importer_code"] = request.importer_code
    if request.arrival_port: extracted_data["arrival_port"] = request.arrival_port
    if request.country_of_origin: extracted_data["country_of_origin"] = request.country_of_origin
    if request.exporter_name: extracted_data["exporter_name"] = request.exporter_name
    if request.vessel_name: extracted_data["vessel_name"] = request.vessel_name

    docx_path = os.path.join(GENERATED_DIR, f"{request.country}_{doc_id}.docx")
    pdf_path = os.path.join(GENERATED_DIR, f"{request.country}_{doc_id}.pdf")

    try:
        generate_docx(extracted_data, request.country, docx_path)
        generate_pdf(extracted_data, request.country, pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

    return {
        "docx_url": f"/files/{request.country}_{doc_id}.docx",
        "pdf_url": f"/files/{request.country}_{doc_id}.pdf"
    }


# ===============================
# TAX CALCULATOR ENDPOINTS
# ===============================

@app.post("/api/calculate-tax/")
async def api_calculate_tax(request: dict):
    value = float(request.get("value", 0))
    currency = request.get("from_currency", "USD")
    country = request.get("target_country", "india")
    category = request.get("category", "standard")
    
    result = calculate_taxes(value, currency, country, category)
    if not result:
        raise HTTPException(status_code=400, detail="Calculation failed or country not supported")
    return result


@app.post("/api/generate-challan/")
async def api_generate_challan(request: dict):
    # Data expected: the result from calculate_taxes
    filename = f"challan_{os.urandom(4).hex()}.pdf"
    output_path = os.path.join(GENERATED_DIR, filename)
    
    try:
        generate_challan(request, output_path)
        return {"challan_url": f"/files/{filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Challan generation error: {str(e)}")


# ===============================
# HEALTH CHECK
# ===============================

@app.get("/health")
def health():
    return {"status": "running"}