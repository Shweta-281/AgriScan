from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import CustomUserCreationForm

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('home')
        else:
            # THIS PRINTS THE EXACT ERROR IN YOUR TERMINAL
            print("REGISTRATION FAILED:", form.errors) 
    else:
        form = CustomUserCreationForm()
        
    return render(request, 'register.html', {'form': form})