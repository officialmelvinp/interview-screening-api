from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions

from .models import InterviewTemplate, InterviewSession, Answer
from .serializers import (
    RegisterSerializer, TemplateCreateSerializer, TemplateListSerializer,
    MySessionSerializer, SubmitAnswersSerializer, ResultsSerializer
)
from .permissions import IsRecruiter, IsCandidate
from .utils import generate_feedback


class RegisterView(generics.CreateAPIView):
    queryset = None
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.all()


class TemplateCreateListView(generics.ListCreateAPIView):
    permission_classes = [IsRecruiter]

    def get_serializer_class(self):
        return TemplateCreateSerializer if self.request.method == 'POST' else TemplateListSerializer

    def get_queryset(self):
        return InterviewTemplate.objects.filter(recruiter=self.request.user)

    def get_serializer_context(self):
        return {'request': self.request}


class MyInterviewView(APIView):
    permission_classes = [IsCandidate]

    def get(self, request):
        session = InterviewSession.objects.filter(candidate=request.user).order_by('-created_at').first()
        if not session:
            return Response({"detail": "No interview assigned."}, status=status.HTTP_404_NOT_FOUND)
        return Response(MySessionSerializer(session).data)


class SubmitAnswersView(APIView):
    permission_classes = [IsCandidate]

    def post(self, request, session_id):
        try:
            session = InterviewSession.objects.get(id=session_id, candidate=request.user)
        except InterviewSession.DoesNotExist:
            return Response({"detail": "Interview session not found."}, status=status.HTTP_404_NOT_FOUND)

        if session.status == 'completed':
            return Response({"detail": "Interview already submitted."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SubmitAnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        valid_question_ids = set(session.template.questions.values_list('id', flat=True))

        for item in serializer.validated_data['answers']:
            q_id, text = item['question_id'], item['text']
            if q_id not in valid_question_ids:
                return Response(
                    {"detail": f"Question {q_id} does not belong to this interview."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            score, feedback = generate_feedback(text)
            Answer.objects.update_or_create(
                session=session, question_id=q_id,
                defaults={"text": text, "score": score, "feedback": feedback}
            )

        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()

        return Response({"detail": "Answers submitted successfully."}, status=status.HTTP_201_CREATED)


class ResultsView(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request, session_id):
        try:
            session = InterviewSession.objects.get(id=session_id, template__recruiter=request.user)
        except InterviewSession.DoesNotExist:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ResultsSerializer(session).data)