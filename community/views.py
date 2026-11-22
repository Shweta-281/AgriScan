from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from accounts.models import User, AgronomistProfile
from .models import ExpertConsultation, ForumPost, ForumComment
from detector.models import PredictionLog

# --- EXPERT & CONSULTATION VIEWS ---

@login_required
def expert_list(request):
    if request.user.role != 'farmer':
        return redirect('home')
    
    # Fetch all agronomists. Because we now create profiles on registration, new Drs will show up!
    experts = AgronomistProfile.objects.select_related('user').all()
    
    disease_context = request.GET.get('disease', '')
    scan_id = request.GET.get('scan_id', '')
    
    return render(request, 'community/expert_list.html', {
        'experts': experts,
        'disease_context': disease_context,
        'scan_id': scan_id
    })

@login_required
def book_consultation(request, expert_id):
    if request.user.role != 'farmer':
        return redirect('home')
        
    expert_profile = get_object_or_404(AgronomistProfile, user__id=expert_id)
    
    if request.method == 'POST':
        issue = request.POST.get('issue_description')
        date_str = request.POST.get('scheduled_time')
        
        ExpertConsultation.objects.create(
            farmer=request.user,
            agronomist=expert_profile.user,
            issue_description=issue,
            scheduled_time=date_str,
            status='pending'
        )
        messages.success(request, f"✅ Consultation requested with Dr. {expert_profile.user.username}!")
        return redirect('home')
        
    disease_context = request.GET.get('disease', '')
    scan_id = request.GET.get('scan_id', '')
    
    return render(request, 'community/book_consultation.html', {
        'expert': expert_profile,
        'disease_context': disease_context,
        'scan_id': scan_id
    })

@login_required
def update_consultation(request, consultation_id, status):
    if request.user.role != 'agronomist':
        return redirect('home')
        
    consultation = get_object_or_404(ExpertConsultation, id=consultation_id, agronomist=request.user)
    if status in ['approved', 'completed']:
        consultation.status = status
        consultation.save()
        messages.success(request, f"Consultation marked as {status}.")
    return redirect('agronomist_dashboard')

@login_required
def agronomist_dashboard(request):
    if request.user.role != 'agronomist':
        return redirect('home') 
        
    # 1. Fetch AI cases that need review
    escalated_cases = PredictionLog.objects.filter(confidence__lt=70).order_by('-date_uploaded')
    
    crop_filter = request.GET.get('crop')
    if crop_filter:
        escalated_cases = escalated_cases.filter(predicted_disease__icontains=crop_filter)
        
    # 2. Fetch Consultations booked with THIS specific expert
    consultations = ExpertConsultation.objects.filter(agronomist=request.user).order_by('-id')
    
    context = {
        'escalated_cases': escalated_cases,
        'consultations': consultations,
        'total_pending': escalated_cases.filter(review_status='pending').count(),
        'total_verified': escalated_cases.filter(review_status='verified').count(),
    }
    return render(request, 'community/agronomist_dashboard.html', context)

@login_required
def review_case(request, pk):
    # Added @login_required for security
    case = get_object_or_404(PredictionLog, id=pk)
    
    if request.method == 'POST':
        case.expert_diagnosis = request.POST.get('expert_diagnosis')
        case.expert_organic_cure = request.POST.get('expert_organic_cure')
        case.expert_chemical_cure = request.POST.get('expert_chemical_cure')
        case.expert_prevention = request.POST.get('expert_prevention')
        
        case.review_status = 'verified'
        case.save()
        
        messages.success(request, "✅ Prescription sent to farmer successfully.")
        return redirect('agronomist_dashboard')
        
    return render(request, 'community/review_case.html', {'case': case})

@login_required
def delete_triage_case(request, pk):
    if request.user.role != 'agronomist':
        return redirect('home')
    
    case = get_object_or_404(PredictionLog, id=pk)
    case.delete()
    
    messages.success(request, "🗑️ Case removed from Triage Inbox.")
    return redirect('agronomist_dashboard')


# --- FORUM VIEWS ---

def forum_list(request):
    posts = ForumPost.objects.all().order_by('-created_at')
    return render(request, 'community/forum_list.html', {'posts': posts})

@login_required
def create_post(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        ForumPost.objects.create(author=request.user, title=title, content=content)
        messages.success(request, "Post created successfully!")
        return redirect('forum_list')
    return render(request, 'community/create_post.html')

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    comments = post.comments.all().order_by('created_at')
    
    if request.method == 'POST':
        content = request.POST.get('content')
        ForumComment.objects.create(post=post, author=request.user, content=content)
        return redirect('post_detail', post_id=post.id)
        
    return render(request, 'community/post_detail.html', {'post': post, 'comments': comments})