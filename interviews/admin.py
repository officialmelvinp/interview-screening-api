from django.contrib import admin
from .models import User, InterviewTemplate, Question, InterviewSession, Answer

admin.site.register(User)
admin.site.register(InterviewTemplate)
admin.site.register(Question)
admin.site.register(InterviewSession)
admin.site.register(Answer)