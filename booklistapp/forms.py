from django import forms

class FeedbackForm(forms.Form):
    text = forms.CharField()