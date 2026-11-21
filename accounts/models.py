from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('farmer', 'Farmer'),
        ('agronomist', 'Agronomist'),
        ('seller', 'Seller'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='farmer')
    phone = models.CharField(max_length=15, blank=True)

    class Meta:
        db_table = 'users'

class FarmerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile')
    location = models.CharField(max_length=100, help_text="City or District Name")
    
    # NEW: Exact coordinates for the Outbreak Map
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    farm_size_acres = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    soil_type = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'farmer_profiles'

class AgronomistProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agronomist_profile')
    specialization = models.CharField(max_length=100)
    experience_years = models.PositiveIntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    
    class Meta:
        db_table = 'expert_profiles'
    
class SellerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    store_name = models.CharField(max_length=100)
    gst_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        db_table = 'seller_profiles'

    def __str__(self):
        return f"{self.store_name} ({self.user.username})"