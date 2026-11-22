import os
import json
import random
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Avg
from django.http import FileResponse, JsonResponse
from django.contrib.auth import logout, get_user_model
from io import BytesIO

# ReportLab Imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from accounts.models import AgronomistProfile, FarmerProfile, User

# Project Imports
from .models import PredictionLog, Disease, MarketPrice, CropCycle, TreatmentPlan, Crop
from .forms import CropCycleForm 
from .gradcam import generate_gradcam
from .predictor import AgriPredictor
from analytics.utils import send_sms, get_disease_risk_alert
from community.models import ExpertConsultation, ForumPost

# Load AI Model
MODEL_PATH = os.path.join(settings.BASE_DIR, 'crop_disease_model.h5')
CLASS_NAMES_PATH = os.path.join(settings.BASE_DIR, 'class_names.txt')

try:
    with open(CLASS_NAMES_PATH, 'r') as f:
        CLASS_NAMES = [line.strip() for line in f.readlines()]
    AI_MODEL = AgriPredictor(MODEL_PATH, CLASS_NAMES)
except Exception as e:
    AI_MODEL = None
    print(f"⚠️ AI Model not loaded: {e}")


def upload_image(request):
    """Main Dashboard and Scan Upload View"""
    if request.user.is_authenticated:
        if request.user.role == 'agronomist': return redirect('agronomist_dashboard')
        elif request.user.role == 'admin' or request.user.is_superuser: return redirect('admin_dashboard')

    if request.method == 'POST' and request.FILES.get('leaf_image'):
        if not request.user.is_authenticated: 
            return redirect('login') 
            
        uploaded_file = request.FILES['leaf_image']
        if AI_MODEL is None: 
            return render(request, 'error.html', {'error': 'AI Model not loaded.'})
            
        temp_log = PredictionLog(
            user=request.user, 
            image=uploaded_file,
            predicted_disease="Processing...", 
            confidence=0.0,
            severity=0
            )
        temp_log.save() 
        
        file_path = temp_log.image.path
        filename = os.path.basename(temp_log.image.name)
        
        result = AI_MODEL.predict(file_path)
        severity = AI_MODEL.calculate_severity(file_path)
        
        raw_name = result["top_prediction"]
        if '___' in raw_name:
            crop, disease = raw_name.split('___', 1)
            disease = disease.replace('_', ' ').title()
            crop = crop.replace('_(maize)', '').replace('_(including_sour)', '').replace('_', ' ').title()
            clean_name = disease if disease.lower().startswith(crop.lower()) else f"{crop} {disease}"
        else:
            clean_name = raw_name.replace('_', ' ').title()

        alt_list = []
        if "alternatives" in result and result["alternatives"]:
            for alt in result["alternatives"]:
                if isinstance(alt, dict):
                    name = alt.get('class', alt.get('label', alt.get('name', 'Unknown')))
                    conf = alt.get('confidence', alt.get('score', alt.get('probability', 0.0)))
                elif isinstance(alt, (list, tuple)) and len(alt) >= 2:
                    name = alt[0]
                    conf = alt[1]
                else:
                    continue
                
                if isinstance(conf, (int, float)) and 0 <= conf <= 1.0:
                    conf = conf * 100
                    
                alt_list.append({
                    'name': str(name).replace('_', ' ').title(),
                    'confidence': round(float(conf), 2)
                })

        scan_lat, scan_lng = None, None
        if hasattr(request.user, 'farmer_profile'):
            scan_lat = request.user.farmer_profile.latitude
            scan_lng = request.user.farmer_profile.longitude

        temp_log.predicted_disease = clean_name
        temp_log.confidence = round(result["confidence"], 2)
        temp_log.alternatives = alt_list 
        temp_log.is_ood = result["is_ood"]
        temp_log.severity = severity
        temp_log.scan_latitude = scan_lat
        temp_log.scan_longitude = scan_lng
        
        try:
            disease_obj = Disease.objects.get(name__iexact=clean_name)
            temp_log.disease = disease_obj
        except Disease.DoesNotExist:
            pass
            
        temp_log.save()
        log = temp_log
        
        gradcam_filename = f"heatmap_{filename}"
        gradcam_path = os.path.join(settings.MEDIA_ROOT, 'uploads', gradcam_filename)
        heatmap_success = generate_gradcam(file_path, gradcam_path)
        if not os.path.exists(gradcam_path): 
            heatmap_success = False
        
        if request.user.phone and not result["is_ood"]:
            send_sms(request.user.phone, f"AgriScan Alert: Your crop has been diagnosed with {clean_name} ({log.confidence}% confidence).")
        
        disease_info = log.disease 
        if not disease_info:
            disease_info = Disease(
                name=clean_name,
                description=f"The AI has detected symptoms consistent with {clean_name}. Detailed agronomic data for this specific strain is currently being updated in our database.",
                treatment="Remove severely infected leaves immediately. Apply a broad-spectrum organic fungicide (like Neem oil) or a copper-based bactericide if bacterial.",
                prevention="Maintain proper plant spacing for air circulation, avoid overhead watering, and practice crop rotation.",
                dosage_instructions="Follow the manufacturer's instructions on the fungicide label. Typically 2-3 ml per liter of water.",
                safety_advisory="Always wear protective gear (gloves, mask) when applying chemical treatments."
            )

        return render(request, 'result.html', {
            'log': log, 
            'disease': disease_info, 
            'gradcam_image': f"{settings.MEDIA_URL}uploads/{gradcam_filename}" if heatmap_success else None,
            'original_image_url': log.image.url if log.image else None, 
            'needs_review': result.get("needs_review", False)
        })
        
    if request.user.is_authenticated:
        recent_scans = PredictionLog.objects.filter(user=request.user).order_by('-date_uploaded')[:3]
        all_user_scans = PredictionLog.objects.filter(user=request.user)
        total_scans = all_user_scans.count()
        healthy_count = all_user_scans.filter(predicted_disease__icontains='healthy').count()
        diseased_count = total_scans - healthy_count
        active_crops = CropCycle.objects.filter(farmer=request.user, is_active=True)[:3]
        
        active_treatments = TreatmentPlan.objects.filter(farmer=request.user, is_completed=False)[:3]
        
        verified_prescriptions = PredictionLog.objects.filter(
            user=request.user, 
            review_status='verified'
        ).order_by('-date_uploaded')[:3]
    else:
        recent_scans = []
        total_scans = 0
        healthy_count = 0
        diseased_count = 0
        active_crops = []
        active_treatments = []
        verified_prescriptions = []

    try: 
        latest_post = ForumPost.objects.order_by('-id').first()
    except: 
        latest_post = None
        
    weather_alert = get_disease_risk_alert()

    forecast = {'yield_estimate': 0, 'revenue_estimate': 0, 'health_score': 0}
    if request.user.is_authenticated and active_crops:
        crop = active_crops[0]
        health_score = max(0, 100 - (diseased_count / (total_scans if total_scans > 0 else 1) * 100))
        base_yield_per_acre = 20
        farm_size = getattr(request.user, 'farmer_profile', None)
        farm_size = farm_size.farm_size_acres if farm_size else 5
        yield_estimate = round(base_yield_per_acre * float(farm_size) * (health_score / 100), 1)
        
        crop_price = MarketPrice.objects.filter(crop_name__icontains=crop.crop.name).order_by('-date').first()
        price_per_quintal = float(crop_price.price_per_quintal) if crop_price else 2000
        
        forecast = {
            'yield_estimate': yield_estimate, 
            'revenue_estimate': int(yield_estimate * price_per_quintal), 
            'health_score': int(health_score)
        }

    return render(request, 'upload.html', {
        'recent_scans': recent_scans, 
        'latest_post': latest_post,
        'total_scans': total_scans, 
        'healthy_count': healthy_count, 
        'diseased_count': diseased_count,
        'active_crops': active_crops, 
        'active_treatments': active_treatments,
        'verified_prescriptions': verified_prescriptions,
        'weather_alert': weather_alert, 
        'forecast': forecast,
    })    

def notifications_api(request):
    if not request.user.is_authenticated: 
        return JsonResponse({'count': 0, 'messages': []})
        
    notif_messages = []
    if request.user.role == 'farmer':
        verified_scans = PredictionLog.objects.filter(user=request.user, review_status='verified').order_by('-date_uploaded')[:5]
        for scan in verified_scans:
            notif_messages.append(f"✅ Expert verified your scan for {scan.predicted_disease}.")
            
    elif request.user.role == 'agronomist':
        pending_scans = PredictionLog.objects.filter(confidence__lt=70, review_status='pending').order_by('-date_uploaded')[:5]
        for scan in pending_scans:
            notif_messages.append(f"⚠️ New low-confidence scan from {scan.user.username} needs review.")
            
    return JsonResponse({'count': len(notif_messages), 'messages': notif_messages})


def outbreak_map(request): 
    return render(request, 'outbreak_map.html')


def outbreak_data(request):
    real_logs = PredictionLog.objects.exclude(is_ood=True)\
                                     .exclude(predicted_disease__icontains='healthy')\
                                     .exclude(scan_latitude=None)\
                                     .order_by('-date_uploaded')[:20]
    
    data = []
    for l in real_logs:
        data.append({
            'lat': l.scan_latitude, 
            'lng': l.scan_longitude, 
            'disease': l.predicted_disease, 
            'confidence': l.confidence, 
            'farmer': l.user.username,
            'date': l.date_uploaded.strftime('%d %b %Y')
        })

    demo_maharashtra = [
        {"lat": 19.0760, "lng": 72.8777, "disease": "Grape Downy Mildew", "confidence": 92.5, "farmer": "raj_patil", "date": "22 Nov 2026"},
        {"lat": 18.5204, "lng": 73.8567, "disease": "Tomato Late Blight", "confidence": 88.1, "farmer": "amit_shinde", "date": "21 Nov 2026"},
        {"lat": 21.1458, "lng": 79.0882, "disease": "Cotton Leaf Curl Virus", "confidence": 95.3, "farmer": "suresh_pawar", "date": "20 Nov 2026"},
        {"lat": 19.9975, "lng": 73.7898, "disease": "Onion Purple Blotch", "confidence": 76.4, "farmer": "ganesh_deshmukh", "date": "22 Nov 2026"},
        {"lat": 17.6599, "lng": 75.9064, "disease": "Sugarcane Red Rot", "confidence": 84.0, "farmer": "vikas_jadhav", "date": "19 Nov 2026"},
        {"lat": 20.9320, "lng": 77.7523, "disease": "Soybean Rust", "confidence": 81.2, "farmer": "prakash_more", "date": "18 Nov 2026"}
    ]
    demo_punjab = [
        {"lat": 30.9010, "lng": 75.8573, "disease": "Wheat Yellow Rust", "confidence": 91.2, "farmer": "gurpreet_singh", "date": "22 Nov 2026"},
        {"lat": 31.6340, "lng": 74.8723, "disease": "Corn Common Rust", "confidence": 89.5, "farmer": "harpreet_kaur", "date": "21 Nov 2026"},
        {"lat": 30.2110, "lng": 74.9455, "disease": "Cotton Leaf Curl Virus", "confidence": 78.6, "farmer": "manpreet_singh", "date": "20 Nov 2026"},
    ]
    data.extend(demo_maharashtra)
    data.extend(demo_punjab)
    
    return JsonResponse({'scans': data})

def history(request):
    if not request.user.is_authenticated: 
        return redirect('login')
    return render(request, 'history.html', {'logs': PredictionLog.objects.filter(user=request.user).order_by('-date_uploaded')})
  

def custom_logout(request): 
    logout(request)
    return redirect('login')


def admin_dashboard(request):
    if not request.user.is_authenticated or (request.user.role != 'admin' and not request.user.is_superuser): 
        return redirect('home')
    User = get_user_model()
    return render(request, 'admin_dashboard.html', {
        'total_scans': PredictionLog.objects.count(),
        'total_users': User.objects.count(),
        'total_profiles': FarmerProfile.objects.count() + AgronomistProfile.objects.count(),
        'total_crop_cycles': CropCycle.objects.count(),
        'total_consultations': ExpertConsultation.objects.count(),
        'common_diseases': PredictionLog.objects.values('predicted_disease').annotate(count=Count('predicted_disease')).order_by('-count')[:5],
        'recent_scans': PredictionLog.objects.order_by('-id')[:5],
    })


def scan_detail(request, pk):
    if not request.user.is_authenticated: 
        return redirect('login')
    log = get_object_or_404(PredictionLog, id=pk, user=request.user)
    
    gradcam_filename = f"heatmap_{os.path.basename(log.image.name)}"
    gradcam_path = os.path.join(settings.MEDIA_ROOT, 'uploads', gradcam_filename)
    if not os.path.exists(gradcam_path) and os.path.exists(log.image.path): 
        generate_gradcam(log.image.path, gradcam_path)
    heatmap_success = os.path.exists(gradcam_path)
    
    disease_info = log.disease 
    if not disease_info:
        disease_info = Disease(
            name=log.predicted_disease, 
            description=f"The AI has detected symptoms consistent with {log.predicted_disease}. Detailed agronomic data for this specific strain is currently being updated in our database.",
            treatment="Remove severely infected leaves immediately. Apply a broad-spectrum organic fungicide (like Neem oil) or a copper-based bactericide if bacterial.",
            prevention="Maintain proper plant spacing, avoid overhead watering, and rotate crops to prevent the spread of pathogens.",
            dosage_instructions="Follow the manufacturer's instructions on the fungicide label. Typically 2-3 ml per liter of water.",
            safety_advisory="Always wear protective gear (gloves, mask) when applying chemical treatments."
        )
        
    return render(request, 'result.html', {
        'log': log, 
        'disease': disease_info, 
        'gradcam_image': f"{settings.MEDIA_URL}uploads/{gradcam_filename}" if heatmap_success else None, 
        'original_image_url': log.image.url if log.image else None,
    })
    
    
@login_required
def delete_scan(request, pk):
    log = get_object_or_404(PredictionLog, id=pk, user=request.user)
    try:
        if os.path.exists(log.image.path): 
            os.remove(log.image.path)
        heatmap_name = f"heatmap_{os.path.basename(log.image.name)}"
        heatmap_path = os.path.join(settings.MEDIA_ROOT, 'uploads', heatmap_name)
        if os.path.exists(heatmap_path): 
            os.remove(heatmap_path)
    except: 
        pass
    log.delete()
    messages.success(request, "🗑️ Scan deleted.")
    return redirect('history')


@login_required
def add_crop_cycle(request):
    if request.method == 'POST':
        form = CropCycleForm(request.POST)
        if form.is_valid():
            crop_name = form.cleaned_data['crop_name'].strip().title()
            crop_obj, created = Crop.objects.get_or_create(
                name=crop_name, 
                defaults={'season': 'Unknown'}
            )
            cycle = form.save(commit=False)
            cycle.farmer = request.user
            cycle.crop = crop_obj
            cycle.is_active = True
            cycle.save()
            messages.success(request, f"🌱 {crop_name} crop cycle added successfully!")
            return redirect('home')
    else: 
        form = CropCycleForm()
    return render(request, 'add_crop.html', {'form': form})

def download_report(request, pk):
    log = get_object_or_404(PredictionLog, id=pk, user=request.user)
    
    disease = log.disease
    if not disease:
        try: 
            disease = Disease.objects.get(name__iexact=log.predicted_disease)
        except: 
            disease = None
            
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], textColor=colors.HexColor("#059669"), spaceAfter=20)
    text_style = styles['Normal']
    
    elements.append(Paragraph("🌱 AgriScan AI - Crop Diagnosis Report", title_style))
    elements.append(Paragraph(f"Date: {log.date_uploaded.strftime('%d %B %Y, %I:%M %p')}", text_style))
    elements.append(Paragraph(f"Scanned by: {request.user.username}", text_style))
    elements.append(Spacer(1, 20))
    
    if log.image:
        try: 
            elements.append(Image(log.image.path, width=300, height=200))
            elements.append(Spacer(1, 20))
        except: 
            pass
            
    data = [
        ['Detected Condition:', log.predicted_disease.replace('_', ' ')],
        ['AI Confidence:', f"{log.confidence}%"],
        ['Severity (Leaf Area):', f"{log.severity}%"]
    ]
    table = Table(data, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#ECFDF5")), 
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#065F46")), 
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), 
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12), 
        ('TOPPADDING', (0, 0), (-1, -1), 12), 
        ('GRID', (0, 0), (-1, -1), 1, colors.white)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    if disease:
        for title, text in [
            ("Description", disease.description), 
            ("Treatment", disease.treatment), 
            ("Dosage Instructions", disease.dosage_instructions), 
            ("Ecosystem Safety", disease.safety_advisory), 
            ("Prevention", disease.prevention)
        ]:
            elements.append(Paragraph(title, styles['Heading3']))
            elements.append(Paragraph(text or "N/A", text_style))
            elements.append(Spacer(1, 10))
            
    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"AgriScan_Report_{log.id}.pdf")

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