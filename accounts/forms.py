from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    # Explicitly define the choices to hide 'Admin' and 'Seller'
    role = forms.ChoiceField(
        choices=[('farmer', 'Farmer'), ('agronomist', 'Agronomist')],
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    # NEW FIELDS for Agronomists
    specialization = forms.CharField(
        max_length=100, 
        required=False, 
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Plant Pathology, Horticulture'})
    )
    experience_years = forms.IntegerField(
        required=False, 
        widget=forms.NumberInput(attrs={'placeholder': 'e.g. 5'})
    )

    class Meta:
        model = User
        # ADDED: first_name and last_name
        fields = ("username", "first_name", "last_name", "email", "phone", "role")
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Choose a username (no spaces)'}),
            # ADDED: widgets for names
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Kirti'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Patil'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Enter your email'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter your mobile number'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 focus:outline-none'
            })
        self.fields['password1'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Create a password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Confirm password'})