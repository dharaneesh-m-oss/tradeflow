from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_pdf(path, data, compliance):

    doc = SimpleDocTemplate(path)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Trade Compliance Report", styles["Heading1"]))
    elements.append(Spacer(1,12))

    for k,v in data.items():
        elements.append(Paragraph(f"{k}: {v}", styles["Normal"]))
        elements.append(Spacer(1,6))

    elements.append(Spacer(1,12))
    elements.append(Paragraph(f"Status: {compliance['status']}", styles["Heading2"]))
    elements.append(Paragraph(f"Risk Score: {compliance['risk_score']}", styles["Normal"]))

    doc.build(elements)