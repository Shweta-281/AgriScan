from django import forms
from .models import CropCycle

class CropCycleForm(forms.ModelForm):
    # Add a text field for the crop name
    crop_name = forms.CharField(
        max_length=100, 
        label="Crop Name",
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Wheat, Tomato, Cotton'})
    )

    class Meta:
        model = CropCycle
        fields = ['sowing_date']
        widgets = {
            'sowing_date': forms.DateInput(attrs={'type': 'date'}),
        }