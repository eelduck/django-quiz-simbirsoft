from typing import List, Type

from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from quiz.dto import QuizDTO, AnswerDTO, AnswersDTO, ChoiceDTO,  QuestionDTO
from quiz.services import QuizResultService
from quiz_app.forms import QuestionForm
from quiz_app.models import Quiz, Question, Choice


def result(request, quiz_id: str):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    result = request.session[quiz_id]['result']
    return render(request, 'quiz_app/result.html', {
        'result': result,
        'quiz': quiz
    })


def index(request):
    request.session.flush()
    quiz_list = Quiz.objects.all()
    return render(request, 'quiz_app/quiz_list.html', {'quiz_list': quiz_list})


def create_quiz_dto(quiz_id: int) -> QuizDTO:
    """
    Создаёт объект QuizDTO из объекта Quiz с идентификатором quiz_id
    :param quiz_id: идентификатор объекта Quiz
    :return: QuizDTO
    """
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = Question.objects.filter(quiz=quiz.id)
    questions_dto_list: List[QuestionDTO] = []
    for question in questions:
        choices = Choice.objects.filter(question=question.id)
        choices_dto_list: List[ChoiceDTO] = []
        for choice in choices:
            choice_dto: ChoiceDTO = ChoiceDTO(
                str(choice.id), choice.text,
                choice.is_correct
            )
            choices_dto_list.append(choice_dto)
        question_dto: QuestionDTO = QuestionDTO(
            str(question.id),
            question.text,
            choices_dto_list
        )
        questions_dto_list.append(question_dto)
    quiz_dto: QuizDTO = QuizDTO(str(quiz.id), quiz.title, questions_dto_list)
    return quiz_dto


class QuizView(FormView):
    form_class = QuestionForm
    template_name = 'quiz_app/question.html'

    def dispatch(self, request, *args, **kwargs):
        self.quiz_id: str = self.kwargs['quiz_id']
        self.question_number: int = self.kwargs['question_number']
        self.quiz: QuizDTO = create_quiz_dto(int(self.quiz_id))

        # Если пользователь не начинал прохождение квиза, инициализируются
        # новые переменные сессии для этого квиза
        if self.quiz_id not in self.request.session:
            self.new_quiz_session()
        return super(QuizView, self).dispatch(request, *args, **kwargs)

    def get_form(self, *args, **kwargs):
        form_class: Type[QuestionForm] = self.form_class
        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        kwargs = super(QuizView, self).get_form_kwargs()
        self.question: QuestionDTO = self.quiz.questions[
            self.question_number - 1
        ]
        previously_selected: List[str] = self.request.session[self.quiz.uuid][
            'user_answers'
        ].get(self.question.uuid, [])
        kwargs.update({
            'question': self.question,
            'previously_selected': previously_selected
        })
        return kwargs

    def form_valid(self, form):
        # Сохранение ответа на вопрос
        self.request.session[self.quiz.uuid]['user_answers'][
            self.question.uuid
        ] = dict(form.data).get('choices', [])

        # Параметр сессии, без которого происходит очистка user_answers
        self.request.session['temp'] = 'temporary field'

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self, **kwargs):
        # Функция определяет редирект после отправки формы,
        # если вопрос последний - редирект на результаты
        if self.question_number != len(self.quiz.questions):
            return reverse('question', kwargs={
                'quiz_id': self.quiz_id,
                'question_number': self.question_number + 1
            })
        else:
            self.save_quiz_result()
            return reverse('result', kwargs={
                'quiz_id': self.quiz_id
            })

    def get_context_data(self, **kwargs):
        # Функция определяет переменные контекста для использования в шаблонах
        context = super(QuizView, self).get_context_data(**kwargs)
        context['quiz']: QuizDTO = self.quiz
        context['question']: QuestionDTO = self.question
        context['question_number']: int = self.question_number
        if self.question_number != 1:
            context['previous_question_number']: int = self.question_number - 1
        context['n_questions']: int = len(self.quiz.questions)
        return context

    def new_quiz_session(self):
        self.request.session[self.quiz.uuid] = dict(
            user_answers={},
        )
        self.request.session[self.quiz.uuid].pop('result', None)
        """
        Cтруктура сессии:
        session
            quiz_uuid
                user_answers
                    question_uuid = choices (List[str])
                result = result (str)
        """

    def create_answers_dto(self) -> AnswersDTO:
        """
        Создает объект AnswersDTO, сформированный из ответов пользователя,
        сохранённых в переменной сессии user_answers
        :return: AnswersDTO
        """
        question_uuids: List[str] = self.request.session[self.quiz.uuid][
            'user_answers'
        ].keys()
        answers: List[AnswerDTO] = []
        for question_uuid in question_uuids:
            answer_dto: AnswerDTO = AnswerDTO(
                question_uuid,
                self.request.session[self.quiz.uuid][
                    'user_answers'
                ][question_uuid]
            )
            answers.append(answer_dto)
        answers_dto: AnswersDTO = AnswersDTO(self.quiz.uuid, answers)
        return answers_dto

    def save_quiz_result(self):
        """
        Функция сохраняет результат прохождения квиза в сессию
        :return: None
        """
        answers_dto: AnswersDTO = self.create_answers_dto()
        quiz_result_service = QuizResultService(self.quiz, answers_dto)
        result: float = quiz_result_service.get_result() * 100
        self.request.session[self.quiz.uuid]['result'] = '%.2f' % result
