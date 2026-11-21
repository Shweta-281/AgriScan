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
from accounts.models import User, FarmerProfile
from marketplace.models import Product, Order
from detector.models import Disease, PredictionLog
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

def export_admin_data(request, data_type, file_format):
    """Handles generating PDF or Excel for 8 different data types."""
    # CUSTOM ADMIN CHECK (Matches your dashboard)
    if request.user.role != 'admin' and not request.user.is_superuser:
        return HttpResponse("Unauthorized. You must be an Admin to download reports.", status=403)
    
    timestamp = timezone.now().strftime("%Y%m%d_%H%M")
    
    # 1. Users
    if data_type == 'users':
        title = "System Users Report"
        headers = ['Username', 'Full Name', 'Email', 'Role', 'Phone', 'Date Joined']
        query = User.objects.all().order_by('date_joined')
        data = [[u.username, u.get_full_name(), u.email, u.role.title(), u.phone or "N/A", u.date_joined.strftime("%Y-%m-%d")] for u in query]
        
    # 2. Farmer Profiles
    elif data_type == 'farmers':
        title = "Farmer Profiles"
        headers = ['Username', 'Full Name', 'Location', 'Farm Size (Acres)', 'Soil Type']
        query = FarmerProfile.objects.select_related('user').all()
        data = [[f.user.username, f.user.get_full_name(), f.location, f.farm_size_acres, f.soil_type or "N/A"] for f in query]
        
    # 3. Products (Marketplace)
    elif data_type == 'products':
        title = "Product Catalog"
        headers = ['ID', 'Name', 'Category', 'Price (₹)', 'Stock', 'Seller']
        query = Product.objects.select_related('category', 'seller').all()
        data = [[p.id, p.name, p.category.name, p.price, p.stock, p.seller.username] for p in query]
        
    # 4. Orders (Marketplace)
    elif data_type == 'orders':
        title = "All Orders"
        headers = ['Order ID', 'Date', 'Farmer', 'Total Amount (₹)', 'Status']
        query = Order.objects.select_related('farmer').all().order_by('-created_at')
        data = [[o.id, o.created_at.strftime("%Y-%m-%d"), o.farmer.username, o.total_amount, o.status] for o in query]
        
    # 5. Disease Catalog
    elif data_type == 'diseases':
        title = "Disease Knowledge Base"
        headers = ['Disease Name', 'Description', 'Treatment', 'Prevention']
        query = Disease.objects.all()
        data = [[d.name, d.description[:50] + '...', d.treatment[:50] + '...', d.prevention[:50] + '...'] for d in query]
        
    # 6. AI Prediction Logs
    elif data_type == 'predictions':
        title = "AI Prediction Logs"
        headers = ['Date', 'Farmer', 'Crop Cycle', 'Predicted Disease', 'Confidence', 'Severity %', 'Review Status']
        query = PredictionLog.objects.select_related('user', 'crop_cycle').all().order_by('-date_uploaded')
        data = [[p.date_uploaded.strftime("%Y-%m-%d"), p.user.username, str(p.crop_cycle) if p.crop_cycle else "N/A", p.predicted_disease, f"{p.confidence:.1%}", p.severity, p.review_status.title()] for p in query]
        
    # 7. Forum Posts (Community)
    elif data_type == 'forum':
        title = "Community Forum Posts"
        headers = ['Date', 'Author', 'Title', 'Content Snippet']
        query = ForumPost.objects.select_related('author').all().order_by('-created_at')
        data = [[p.created_at.strftime("%Y-%m-%d"), p.author.username, p.title, p.content[:40] + '...'] for p in query]
        
    # 8. Expert Consultations
    elif data_type == 'consultations':
        title = "Expert Consultations"
        headers = ['Scheduled Time', 'Farmer', 'Agronomist', 'Issue', 'Status']
        query = ExpertConsultation.objects.select_related('farmer', 'agronomist').all().order_by('-scheduled_time')
        data = [[c.scheduled_time.strftime("%Y-%m-%d %H:%M"), c.farmer.username, c.agronomist.username, c.issue_description[:40] + '...', c.status.title()] for c in query]
        
    else:
        return redirect('admin_dashboard') # Redirect to dashboard if invalid type

    # Generate the File
    filename = f"AgriScan_{data_type}_{timestamp}"
    
    if file_format == 'excel':
        return export_to_excel(headers, data, filename)
    else:
        return export_to_pdf(title, headers, data, filename)


@login_required
def admin_reports(request):
    """Renders the page with the download buttons."""
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')
    return render(request, 'analytics/admin_reports.html')