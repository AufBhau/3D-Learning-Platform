from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def signup_view(request):
    """User registration page"""
    if request.user.is_authenticated:
        # Already logged in, redirect to home
        return redirect('home')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Automatically log in after registration
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account has been created.')
            return redirect('home')
    else:
        form = UserCreationForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    """User login page"""
    if request.user.is_authenticated:
        # Already logged in
        return redirect('home')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                # Redirect to 'next' parameter if exists, else home
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def profile_view(request):
    """User profile/dashboard"""
    # Get courses and progress
    from courses.models import Course, StudentProgress
    
    all_courses = Course.objects.all()
    user_progress = StudentProgress.objects.filter(student=request.user)
    
    # Calculate stats
    total_courses = all_courses.count()
    completed_lessons = user_progress.filter(completed=True).count()
    
    context = {
        'courses': all_courses,
        'user_progress': user_progress,
        'total_courses': total_courses,
        'completed_lessons': completed_lessons,
    }
    
    return render(request, 'accounts/profile.html', context)