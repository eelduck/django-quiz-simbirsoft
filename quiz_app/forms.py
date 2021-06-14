from typing import List
from django import forms
from quiz.dto import QuestionDTO


class QuestionForm(forms.Form):
    def __init__(self, question: QuestionDTO, previously_selected, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        self.fields["choices"] = forms.MultipleChoiceField(
            widget=forms.CheckboxSelectMultiple,
            choices=[[choice.uuid, choice.text] for choice in question.choices],
            initial=previously_selected
        )

    def is_valid(self):
        return True
