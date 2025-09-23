from django.contrib import admin
from .models import Citizen, Category, Department, Complaint, Feedback

admin.site.register(Citizen)
admin.site.register(Category)
admin.site.register(Department)
admin.site.register(Complaint)
admin.site.register(Feedback)
