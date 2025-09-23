from django import forms
from .models import Complaint, Feedback
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# Form for citizens to submit a new complaint
class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['citizen', 'category', 'department', 'description']


# Form for staff/admin to update the complaint status
class ComplaintStatusForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['status']


# Form for citizens to submit feedback
class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['complaint', 'comments', 'rating']

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
