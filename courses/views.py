from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Course, Lesson, StudentProgress, Annotation
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def home(request):
    """Homepage"""
    return render(request, 'courses/home.html')


def course_list(request):
    """List all courses"""
    courses = Course.objects.all()
    return render(request, 'courses/course_list.html', {'courses': courses})


def course_detail(request, course_id):
    """Show course details and lessons"""
    course = get_object_or_404(Course, id=course_id)
    lessons = course.lessons.all()
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'lessons': lessons
    })


@csrf_exempt
def lesson_viewer(request):
    """Simple 3D viewer without authentication (for testing drone)"""
    return render(request, 'courses/lesson_viewer.html')


@login_required
def lesson_viewer_authenticated(request, lesson_id):
    """Display the 3D model viewer page with lesson data"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.course
    
    # Get or create progress for this user and lesson
    progress, created = StudentProgress.objects.get_or_create(
        student=request.user,
        lesson=lesson
    )
    
    context = {
        'lesson': lesson,
        'course': course,
        'progress': progress,
    }
    return render(request, 'courses/lesson_viewer.html', context)


@login_required
def mark_complete(request, lesson_id):
    """Mark lesson as complete or incomplete"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Get or create progress
    progress, created = StudentProgress.objects.get_or_create(
        student=request.user,
        lesson=lesson
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'complete':
            progress.completed = True
            progress.completed_at = timezone.now()
            messages.success(request, f'✅ Lesson "{lesson.title}" marked as complete!')
        elif action == 'uncomplete':
            progress.completed = False
            progress.completed_at = None
            messages.info(request, f'Lesson "{lesson.title}" marked as incomplete.')
        
        progress.save()
    
    return redirect('lesson_viewer', lesson_id=lesson.id)