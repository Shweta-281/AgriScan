from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.contrib.auth import views as auth_views
from accounts.views import register
from detector.views import custom_logout
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from accounts.models import FarmerProfile, AgronomistProfile
from detector.models import Disease, MarketPrice
from marketplace.models import Category, Product
from datetime import date, timedelta
import random

def setup_live_db(request):
    try:
        User = get_user_model()
        admin, _ = User.objects.get_or_create(username='admin')
        admin.set_password('pass12345'); admin.is_superuser = True; admin.is_staff = True; admin.role = 'admin'; admin.save()
        
        farmer, _ = User.objects.get_or_create(username='farmer_raj')
        farmer.set_password('pass12345'); farmer.role = 'farmer'; farmer.save()
        FarmerProfile.objects.get_or_create(user=farmer)
        
        seller, _ = User.objects.get_or_create(username='seller1')
        seller.set_password('pass12345'); seller.role = 'seller'; seller.save()

        experts = [{"username": "dr_smith", "spec": "Plant Pathology & Fungi", "exp": 12, "fee": 499.00}]
        for e in experts:
            u, _ = User.objects.get_or_create(username=e["username"])
            u.set_password('pass12345'); u.role = 'agronomist'; u.save()
            AgronomistProfile.objects.get_or_create(user=u, defaults={'specialization': e["spec"], 'experience_years': e["exp"], 'consultation_fee': e["fee"]})

        diseases = [
            ("Apple Scab", "Fungal disease.", "Apply fungicides.", "Prune trees."),
            ("Tomato Late Blight", "Devastating fungal disease.", "Copper fungicides.", "Air circulation."),
            ("Corn Northern Leaf Blight", "Cigar-shaped lesions.", "Apply fungicides.", "Crop rotation."),
            ("Grape Black Rot", "Brown spots.", "Remove berries.", "Fungicides.")
        ]
        for name, desc, treat, prev in diseases:
            Disease.objects.get_or_create(name=name, defaults={'description': desc, 'treatment': treat, 'prevention': prev, 'dosage_instructions': 'Follow label.', 'safety_advisory': 'Wear PPE.'})

        cat_fert, _ = Category.objects.get_or_create(name="Fertilizers")
        cat_pest, _ = Category.objects.get_or_create(name="Pesticides")
        
        products_data = [("Organic Vermicompost", cat_fert, 350.00, 50, "100% organic."), ("Chlorothalonil Fungicide", cat_pest, 550.00, 40, "Effective for Blight.")]
        for name, cat, price, stock, desc in products_data:
            Product.objects.get_or_create(name=name, defaults={'seller': seller, 'category': cat, 'price': price, 'stock': stock, 'description': desc})

        crops = ['Wheat', 'Tomato', 'Grapes', 'Potato']
        for crop in crops:
            base_price = random.randint(1500, 2500)
            for i in range(7):
                d = date.today() - timedelta(days=i)
                MarketPrice.objects.get_or_create(crop_name=crop, date=d, defaults={'price_per_quintal': base_price + random.randint(-150, 150)})
        
        return HttpResponse("🎉 SUCCESS! Database populated.")
    except Exception as e:
        return HttpResponse(f"❌ ERROR: {str(e)}")

urlpatterns = [
    path('setup-db/', setup_live_db),
    path('admin/', admin.site.urls),
    path('', include('detector.urls')),
    path('outbreak/', include('detector.outbreak_urls')), # NEW OUTBREAK MAP
    path('marketplace/', include('marketplace.urls')), 
    path('community/', include('community.urls')),
    path('weather/', include('analytics.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('register/', register, name='register'),
    path('logout/', custom_logout, name='logout'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]