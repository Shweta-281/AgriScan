import requests
import time
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.http import HttpResponse

# Import your models
from .models import WeatherLog
from accounts.models import AgronomistProfile, User, FarmerProfile
from detector.models import CropCycle, Disease, PredictionLog
from community.models import ForumPost, ExpertConsultation

# Import your utilities for PDF/Excel generation
from .utils import export_to_excel, export_to_pdf

@login_required
def weather_dashboard(request):
    api_key = settings.WEATHER_API_KEY
    city = request.GET.get('city', 'Mumbai') # Default city
    weather_data = None
    agricultural_alert = None

    if api_key and api_key != 'paste_your_api_key_here':
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        try:
            response = requests.get(url).json()

            if response.get('cod') == 200:
                temp = response['main']['temp']
                humidity = response['main']['humidity']
                rainfall = response.get('rain', {}).get('1h', 0) # Rainfall in last 1 hour
                description = response['weather'][0]['description'].title()
                wind_speed = response['wind']['speed']

                weather_data = {
                    'city': response['name'],
                    'temp': temp,
                    'humidity': humidity,
                    'description': description,
                    'wind': wind_speed,
                    'rainfall': rainfall
                }

                # Save to database
                WeatherLog.objects.create(
                    location=response['name'],
                    temperature=temp,
                    humidity=humidity,
                    rainfall_mm=rainfall
                )

                # Generate Agricultural Alerts based on data
                if humidity > 80:
                    agricultural_alert = "⚠️ HIGH HUMIDITY WARNING: Conditions are highly favorable for fungal diseases (like Late Blight). Ensure proper air circulation in your fields."
                elif rainfall > 5:
                    agricultural_alert = "🌧️ HEAVY RAIN WARNING: High risk of soil erosion and runoff. Postpone any scheduled pesticide spraying today."
                elif temp > 38:
                    agricultural_alert = "🔥 HEATWAVE WARNING: Extreme heat detected. Ensure your crops are adequately irrigated to prevent heat stress."
                else:
                    agricultural_alert = "✅ OPTIMAL CONDITIONS: The current weather is favorable for normal farming activities."
        except Exception as e:
            print(f"Error fetching weather: {e}")

    return render(request, 'analytics/weather.html', {
        'weather': weather_data,
        'alert': agricultural_alert,
        'city': city
    })
    
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect


@login_required
def admin_reports(request):
    """Renders the page with the download buttons."""
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')
    return render(request, 'analytics/admin_reports.html')

import csv
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

def export_admin_data(request, data_type, file_format):
    # 1. Ensure only admins can export
    if not request.user.is_authenticated or (request.user.role != 'admin' and not request.user.is_superuser):
        return redirect('home')

    # 2. Define the data based on the requested type
    if data_type == 'users':
        title = "System Users"
        headers = ['Username', 'Email', 'Role', 'Phone', 'Joined']
        data = [[u.username, u.email, u.role, u.phone, u.date_joined.strftime('%Y-%m-%d')] for u in User.objects.all()]
        
    elif data_type == 'farmers':
        title = "Farmer Profiles"
        headers = ['Username', 'Location', 'Farm Size (Acres)', 'Soil Type']
        data = [[f.user.username, f.location, f.farm_size_acres, f.soil_type] for f in FarmerProfile.objects.all()]
        
    elif data_type == 'experts':
        title = "Expert Profiles"
        headers = ['Username', 'Specialization', 'Experience (Yrs)', 'Consultation Fee']
        data = [[e.user.username, e.specialization, e.experience_years, e.consultation_fee] for e in AgronomistProfile.objects.all()]
        
    elif data_type == 'crops':
        title = "Active Crop Cycles"
        headers = ['Farmer', 'Crop Name', 'Sowing Date', 'Status']
        data = [[c.farmer.username, c.crop.name, c.sowing_date.strftime('%Y-%m-%d'), 'Active' if c.is_active else 'Inactive'] for c in CropCycle.objects.all()]
        
    elif data_type == 'diseases':
        title = "Disease Catalog"
        headers = ['Disease Name', 'Treatment', 'Prevention']
        data = [[d.name, d.treatment[:50] + '...', d.prevention[:50] + '...'] for d in Disease.objects.all()]
        
    elif data_type == 'predictions':
        title = "AI Prediction Logs"
        headers = ['Scan ID', 'Farmer', 'Predicted Disease', 'Confidence', 'Severity', 'Date']
        data = [[str(p.id), p.user.username, p.predicted_disease, f"{p.confidence}%", f"{p.severity}%", p.date_uploaded.strftime('%Y-%m-%d')] for p in PredictionLog.objects.all()]
        
    elif data_type == 'forum':
        title = "Community Forum Posts"
        headers = ['Author', 'Title', 'Created At']
        data = [[post.author.username, post.title, post.created_at.strftime('%Y-%m-%d')] for post in ForumPost.objects.all()]
    else:
        return redirect('admin_dashboard')

    # 3. Generate PDF
    if file_format == 'pdf':
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{title}.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(f"AgriScan Admin Export - {title}", styles['Heading1']))
        
        table_data = [headers] + data
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#059669")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F9FAFB")),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
        ]))
        elements.append(t)
        doc.build(elements)
        return response

    # 4. Generate CSV (Excel)
    elif file_format == 'excel':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{title}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(headers)
        writer.writerows(data)
        return response

    return redirect('admin_dashboard')
@login_required
def admin_reports(request):
    """Renders the page with the download buttons."""
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')
    return render(request, 'analytics/admin_reports.html')