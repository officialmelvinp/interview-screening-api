from django.urls import path
from .views import RegisterView, TemplateCreateListView, MyInterviewView, SubmitAnswersView, ResultsView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('interviews/templates/', TemplateCreateListView.as_view(), name='templates'),
    path('interviews/my/', MyInterviewView.as_view(), name='my-interview'),
    path('interviews/<int:session_id>/submit/', SubmitAnswersView.as_view(), name='submit-answers'),
    path('interviews/<int:session_id>/results/', ResultsView.as_view(), name='results'),
]