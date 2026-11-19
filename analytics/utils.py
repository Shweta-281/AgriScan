import os
import requests

def get_disease_risk_alert(lat=28.61, lon=77.20): # Default to New Delhi coords
    """
    Fetches weather and calculates fungal disease risk.
    High risk if humidity > 80% and temp is between 15-30C.
    """
    try:
        # Free API, no key required
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        temp = data['current']['temperature_2m']
        humidity = data['current']['relative_humidity_2m']
        
        risk_level = "Low"
        disease_name = "No immediate threat"
        advice = "Weather conditions are stable."
        
        if humidity > 80 and 15 <= temp <= 30:
            risk_level = "High"
            disease_name = "Fungal Infection Risk (Late Blight / Powdery Mildew)"
            advice = "High humidity detected. Apply preventative copper-based fungicide."
        elif humidity > 65 and temp > 30:
            risk_level = "Moderate"
            disease_name = "Bacterial Spot Risk"
            advice = "Warm and somewhat humid. Monitor leaves closely."
            
        return {
            "temp": temp,
            "humidity": humidity,
            "risk_level": risk_level,
            "disease_name": disease_name,
            "advice": advice
        }
    except Exception as e:
        print(f"Weather API Error: {e}")
        return None

def send_sms(phone_number, message):
    """
    Mock SMS Sender. 
    In production, you would replace the print statement with a real API call 
    to Twilio, Fast2SMS, or Gupshup.
    """
    if not phone_number:
        print(f"⚠️ Could not send SMS: No phone number provided.")
        return False
        
    print("\n" + "="*50)
    print(f"📱 MOCK SMS SENT TO: {phone_number}")
    print(f"💬 MESSAGE: {message}")
    print("="*50 + "\n")
    
    return True

# If you get a real API key in the future, you just change the code to this:
# def send_sms(phone, message):
#     import requests
#     url = "https://www.fast2sms.com/dev/bulkV2"
#     payload = f"authorization=YOUR_API_KEY&message={message}&language=english&route=q&numbers={phone}"
#     headers = {'content-type': "application/x-www-form-urlencoded"}
#     requests.request("POST", url, data=payload, headers=headers)

# utils.py (or analytics/utils.py)
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from django.http import HttpResponse
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def export_to_excel(headers, data, filename):
    """Generates an Excel file from a list of headers and row data."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"

    # Styling
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid") # Agri Green

    # Write Headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # Write Data
    for row_num, row_data in enumerate(data, 2):
        for col_num, cell_value in enumerate(row_data, 1):
            ws.cell(row=row_num, column=col_num, value=str(cell_value))

    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    wb.save(response)
    return response


def export_to_pdf(title, headers, data, filename):
    """Generates a generic Landscape PDF report."""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#2E7D32'))
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 15))

    # Table Data
    table_data = [headers] + data
    
    # Create Table
    t = Table(table_data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    elements.append(t)
    doc.build(elements)
    return response