from django.db import models
from django.conf import settings
from django.utils import timezone
from accounts.models import User

class Disease(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    treatment = models.TextField()
    prevention = models.TextField()
    dosage_instructions = models.TextField(blank=True, null=True)
    safety_advisory = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'diseases'

    def __str__(self):
        return self.name

class Crop(models.Model):
    name = models.CharField(max_length=100)
    season = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'crops'
        
    def __str__(self): 
        return self.name

class CropCycle(models.Model):
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'farmer'})
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    sowing_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    @property
    def days_since_sowing(self):
        if self.sowing_date:
            return (timezone.now().date() - self.sowing_date).days
        return 0

# --- RESTORED MODEL ---
class MarketPrice(models.Model):
    crop_name = models.CharField(max_length=100)
    price_per_quintal = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    
    class Meta:
        db_table = 'market_prices'
    
    def __str__(self):
        return f"{self.crop_name} - ₹{self.price_per_quintal} on {self.date}"

class PredictionLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    crop_cycle = models.ForeignKey(CropCycle, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Link to Disease model
    disease = models.ForeignKey(Disease, on_delete=models.SET_NULL, null=True, blank=True)
    
    image = models.ImageField(upload_to='uploads/')
    predicted_disease = models.CharField(max_length=100) 
    confidence = models.FloatField()
    severity = models.PositiveIntegerField(default=0, help_text="Percentage of leaf affected")
    
    # Location tracking for the map
    scan_latitude = models.FloatField(null=True, blank=True)
    scan_longitude = models.FloatField(null=True, blank=True)

    alternatives = models.JSONField(default=list, help_text="Top 3 predictions")
    is_ood = models.BooleanField(default=False, help_text="Is Out of Distribution?")
    
    date_uploaded = models.DateTimeField(auto_now_add=True)
    
    REVIEW_STATUS = [
        ('pending', 'Pending Review'),
        ('verified', 'Verified by Expert')
    ]
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='pending')
    expert_diagnosis = models.CharField(max_length=200, blank=True, null=True)
    
    class Meta:
        db_table = 'scan_history'

    def __str__(self): 
        return f"{self.user.username} - {self.predicted_disease}"
    
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='pending')
    expert_diagnosis = models.CharField(max_length=200, blank=True, null=True)
    
    # NEW FIELDS FOR EXPERT PRESCRIPTION
    expert_organic_cure = models.TextField(blank=True, null=True)
    expert_chemical_cure = models.TextField(blank=True, null=True)
    expert_prevention = models.TextField(blank=True, null=True)
    expert_amazon_link = models.URLField(blank=True, null=True, help_text="Link to purchase the recommended cure")

# New Model for Treatment Tracking
class TreatmentPlan(models.Model):
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    scan = models.ForeignKey(PredictionLog, on_delete=models.CASCADE)
    treatment_name = models.CharField(max_length=200)
    start_date = models.DateField(auto_now_add=True)
    duration_days = models.PositiveIntegerField(default=5)
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'treatment_plans'

    @property
    def current_day(self):
        return (timezone.now().date() - self.start_date).days + 1