from .dto import QuestionDTO, QuizDTO, AnswersDTO
from typing import Set


class QuizResultService:
    def __init__(self, quiz_dto: QuizDTO, answers_dto: AnswersDTO):
        self.quiz_dto = quiz_dto
        self.answers_dto = answers_dto

    def get_result(self) -> float:
        questions_dict: dict = self.get_questions_dict()
        n_correct_answers = 0
        for answer in self.answers_dto.answers:
            if correct_answer := questions_dict.get(answer.question_uuid, None):
                if correct_answer == set(answer.choices):
                    n_correct_answers += 1
        return n_correct_answers / len(questions_dict)

    def get_questions_dict(self) -> dict:
        """
        Формирует словарь, где ключи - uuid вопросов квиза, значения - множества правильных ответов
        :return: dict
        """
        questions_dict = dict()
        for question in self.quiz_dto.questions:
            correct_answers = self.get_correct_answers(question)
            questions_dict[question.uuid] = correct_answers
        return questions_dict

    def get_correct_answers(self, question: QuestionDTO) -> Set[str]:
        """
        Формирует множество из правильных ответов на определенный вопрос
        :param question: вопрос, для которого сформируется множество
        :return: Set[str]
        """
        correct_answers = set()
        for choice in question.choices:
            if choice.is_correct:
                correct_answers.add(choice.uuid)
        return correct_answers
