from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import CustomUserCreationForm
from .models import AgronomistProfile, FarmerProfile

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Save the experience & specialization for Agronomists
            if user.role == 'agronomist':
                AgronomistProfile.objects.create(
                    user=user,
                    specialization=form.cleaned_data.get('specialization') or "General Agronomy",
                    experience_years=form.cleaned_data.get('experience_years') or 0
                )
            # Save the Farmer Profile
            elif user.role == 'farmer':
                FarmerProfile.objects.create(
                    user=user,
                    location="Not Set",
                    farm_size_acres=0.0
                )
            
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('home')
        else:
            # Prints errors in terminal for debugging
            print("REGISTRATION FAILED:", form.errors) 
    else:
        form = CustomUserCreationForm()
        
    return render(request, 'register.html', {'form': form})