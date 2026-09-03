from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import InterviewTemplate, Question, InterviewSession, Answer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'role']

    def create(self, validated_data):
        user = User(username=validated_data['username'], role=validated_data['role'])
        user.set_password(validated_data['password'])
        user.save()
        return user


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'order']


class TemplateCreateSerializer(serializers.ModelSerializer):
    questions = serializers.ListField(
        child=serializers.CharField(), min_length=3, max_length=5, write_only=True
    )
    candidate_username = serializers.CharField(write_only=True)

    class Meta:
        model = InterviewTemplate
        fields = ['id', 'title', 'questions', 'candidate_username']

    def validate_candidate_username(self, value):
        if not User.objects.filter(username=value, role='candidate').exists():
            raise serializers.ValidationError("No candidate found with that username.")
        return value

    def create(self, validated_data):
        questions_data = validated_data.pop('questions')
        candidate_username = validated_data.pop('candidate_username')
        recruiter = self.context['request'].user

        template = InterviewTemplate.objects.create(recruiter=recruiter, title=validated_data['title'])
        for idx, q_text in enumerate(questions_data):
            Question.objects.create(template=template, text=q_text, order=idx)

        candidate = User.objects.get(username=candidate_username, role='candidate')
        InterviewSession.objects.create(template=template, candidate=candidate)
        return template


class TemplateListSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewTemplate
        fields = ['id', 'title', 'created_at', 'questions']


class MySessionSerializer(serializers.ModelSerializer):
    template_title = serializers.CharField(source='template.title')
    questions = QuestionSerializer(source='template.questions', many=True)

    class Meta:
        model = InterviewSession
        fields = ['id', 'template_title', 'status', 'questions']


class AnswerInputSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    text = serializers.CharField()


class SubmitAnswersSerializer(serializers.Serializer):
    answers = AnswerInputSerializer(many=True)


class AnswerResultSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text')

    class Meta:
        model = Answer
        fields = ['question_text', 'text', 'score', 'feedback']


class ResultsSerializer(serializers.ModelSerializer):
    candidate_username = serializers.CharField(source='candidate.username')
    answers = AnswerResultSerializer(many=True)

    class Meta:
        model = InterviewSession
        fields = ['id', 'candidate_username', 'status', 'answers']