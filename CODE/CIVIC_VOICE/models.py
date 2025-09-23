from django.db import models

from django.contrib.auth.models import User

class Citizen(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # link to User table
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.user.username


class Category(models.Model):
    category_name = models.CharField(max_length=100)
    contact_info = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.category_name

class Department(models.Model):
    dept_name = models.CharField(max_length=100)
    contact_info = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.dept_name

class Complaint(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
    ]

    citizen = models.ForeignKey(Citizen, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Pending")
    submitted_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Complaint by {self.citizen.name}"

class Feedback(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE)
    comments = models.TextField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Feedback for {self.complaint.id}"
