from django.db import models
from django.contrib.auth.models import User

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    thumbnail = models.ImageField(upload_to='course_thumbnails/' , blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    model_file = models.FileField(upload_to='3d_models/', blank=True, null=True)
    interaction_guide = models.TextField(blank=True, help_text="Guide for Students")

    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    class Meta:
        ordering = ['course', 'order']
        unique_together = ['course', 'order']

class StudentProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent = models.DurationField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.student.username} - {self.lesson.title}"
    
    class Meta:
        unique_together = ['student', 'lesson']
        verbose_name_plural = "Student Progress"

class Annotation(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='annotations')
    title = models.CharField(max_length=100)
    description = models.TextField()
    position_x = models.FloatField()
    position_y = models.FloatField()
    position_z = models.FloatField()
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"
    
    class Meta:
        ordering = ['lesson', 'order']