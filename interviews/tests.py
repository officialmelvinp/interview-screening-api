from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Answer, InterviewSession, InterviewTemplate, Question


User = get_user_model()


class InterviewAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # These users are force-authenticated, so password hashing is irrelevant
        # to this API authorization suite and would slow every test substantially.
        self.recruiter = User.objects.create(username="recruiter", role="recruiter")
        self.candidate = User.objects.create(username="candidate", role="candidate")
        self.template = InterviewTemplate.objects.create(recruiter=self.recruiter, title="Backend screen")
        self.question = Question.objects.create(template=self.template, text="Describe a REST API.", order=0)
        self.session = InterviewSession.objects.create(template=self.template, candidate=self.candidate)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_register_allows_public_creation(self):
        response = self.client.post(reverse("register"), {"username": "new-candidate", "password": "safe-password", "role": "candidate"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "new-candidate")
        self.assertEqual(response.data["role"], "candidate")
        self.assertNotIn("password", response.data)
        self.assertTrue(User.objects.filter(username="new-candidate").exists())

    def test_templates_lists_recruiters_templates(self):
        self.authenticate(self.recruiter)
        response = self.client.get(reverse("templates"), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], self.template.id)
        self.assertEqual(response.data[0]["questions"][0]["id"], self.question.id)

    def test_templates_creates_template_questions_and_session(self):
        self.authenticate(self.recruiter)
        response = self.client.post(reverse("templates"), {"title": "Python screen", "candidate_username": self.candidate.username, "questions": ["First question", "Second question", "Third question"]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        template = InterviewTemplate.objects.get(id=response.data["id"])
        self.assertEqual(template.recruiter, self.recruiter)
        self.assertEqual(list(template.questions.values_list("order", flat=True)), [0, 1, 2])
        self.assertTrue(InterviewSession.objects.filter(template=template, candidate=self.candidate).exists())

    def test_templates_denies_candidate(self):
        self.authenticate(self.candidate)
        response = self.client.get(reverse("templates"), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_interview_returns_latest_candidates_session(self):
        self.authenticate(self.candidate)
        response = self.client.get(reverse("my-interview"), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.session.id)
        self.assertEqual(response.data["template_title"], "Backend screen")
        self.assertEqual(response.data["questions"][0]["text"], self.question.text)

    def test_my_interview_denies_recruiter(self):
        self.authenticate(self.recruiter)
        response = self.client.get(reverse("my-interview"), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_submit_answers_creates_scored_answer_and_completes_session(self):
        self.authenticate(self.candidate)
        answer_text = "I would use clear resources, HTTP methods, validation, and useful status codes."
        response = self.client.post(reverse("submit-answers", kwargs={"session_id": self.session.id}), {"answers": [{"question_id": self.question.id, "text": answer_text}]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"detail": "Answers submitted successfully."})
        self.session.refresh_from_db()
        answer = Answer.objects.get(session=self.session, question=self.question)
        self.assertEqual(self.session.status, "completed")
        self.assertIsNotNone(self.session.completed_at)
        self.assertEqual(answer.score, 7.79)
        self.assertEqual(answer.feedback, "Adequate answer")

    def test_submit_answers_denies_recruiter(self):
        self.authenticate(self.recruiter)
        response = self.client.post(reverse("submit-answers", kwargs={"session_id": self.session.id}), {"answers": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_results_returns_owned_session_and_answers(self):
        Answer.objects.create(session=self.session, question=self.question, text="A concise answer.", score=3.0, feedback="Too brief or lacking detail")
        self.authenticate(self.recruiter)
        response = self.client.get(reverse("results", kwargs={"session_id": self.session.id}), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["candidate_username"], self.candidate.username)
        self.assertEqual(response.data["answers"][0]["question_text"], self.question.text)
        self.assertEqual(response.data["answers"][0]["score"], 3.0)

    def test_results_denies_candidate(self):
        self.authenticate(self.candidate)
        response = self.client.get(reverse("results", kwargs={"session_id": self.session.id}), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_results_returns_not_found_for_another_recruiters_session(self):
        other_recruiter = User.objects.create(username="other-recruiter", role="recruiter")
        self.authenticate(other_recruiter)
        response = self.client.get(reverse("results", kwargs={"session_id": self.session.id}), format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {"detail": "Session not found."})

    def test_protected_endpoint_requires_authentication(self):
        response = self.client.get(reverse("templates"), format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_answers_rejects_question_from_another_template(self):
        other_template = InterviewTemplate.objects.create(recruiter=self.recruiter, title="Other screen")
        other_question = Question.objects.create(template=other_template, text="Unrelated question", order=0)
        self.authenticate(self.candidate)
        response = self.client.post(reverse("submit-answers", kwargs={"session_id": self.session.id}), {"answers": [{"question_id": other_question.id, "text": "An answer."}]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"detail": f"Question {other_question.id} does not belong to this interview."})

    def test_submit_answers_rejects_completed_session(self):
        self.session.status = "completed"
        self.session.save()
        self.authenticate(self.candidate)
        response = self.client.post(reverse("submit-answers", kwargs={"session_id": self.session.id}), {"answers": [{"question_id": self.question.id, "text": "An answer."}]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"detail": "Interview already submitted."})

    def test_templates_rejects_unknown_candidate_username(self):
        self.authenticate(self.recruiter)
        response = self.client.post(reverse("templates"), {"title": "Python screen", "candidate_username": "missing-candidate", "questions": ["First question", "Second question", "Third question"]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"candidate_username": ["No candidate found with that username."]})
