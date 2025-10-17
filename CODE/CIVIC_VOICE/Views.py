from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import Complaint, Feedback
from .forms import ComplaintForm, ComplaintSearchForm, FeedbackForm

def home(request):
    """Homepage view"""
    search_form = ComplaintSearchForm()
    return render(request, 'complaints/home.html', {'search_form': search_form})

@login_required
def dashboard(request):
    """User dashboard showing their complaints and quick actions"""
    user_complaints = Complaint.objects.filter(user=request.user)[:5]  # Latest 5 complaints
    complaint_stats = {
        'total': Complaint.objects.filter(user=request.user).count(),
        'pending': Complaint.objects.filter(user=request.user, status='PENDING').count(),
        'in_progress': Complaint.objects.filter(user=request.user, status='IN_PROGRESS').count(),
        'resolved': Complaint.objects.filter(user=request.user, status='RESOLVED').count(),
    }
    
    context = {
        'complaints': user_complaints,
        'stats': complaint_stats,
    }
    return render(request, 'complaints/dashboard.html', context)

@login_required
def submit_complaint(request):
    """Submit a new complaint"""
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.user = request.user
            complaint.save()
            
            # Create initial status history entry
            from .models import ComplaintStatusHistory
            ComplaintStatusHistory.objects.create(
                complaint=complaint,
                old_status='PENDING',  # Initial status
                new_status=complaint.status,
                changed_by=request.user,
                remarks='Complaint submitted by user'
            )
            
            # Send email notification to user
            send_complaint_email(complaint)
            
            messages.success(request, f'Your complaint has been submitted successfully! Complaint ID: {complaint.complaint_id}')
            return redirect('complaints:my_complaints')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ComplaintForm()
    
    return render(request, 'complaints/submit_complaint.html', {'form': form})

@login_required
def my_complaints(request):
    """Display all complaints by the logged-in user"""
    complaints = Complaint.objects.filter(user=request.user)
    return render(request, 'complaints/my_complaints.html', {'complaints': complaints})

def track_complaint(request):
    """Track complaint by ID (public view)"""
    complaint = None
    if request.method == 'POST':
        form = ComplaintSearchForm(request.POST)
        if form.is_valid():
            complaint_id = form.cleaned_data['complaint_id']
            try:
                complaint = Complaint.objects.get(complaint_id=complaint_id)
            except Complaint.DoesNotExist:
                messages.error(request, f'No complaint found with ID: {complaint_id}')
    else:
        form = ComplaintSearchForm()
    
    return render(request, 'complaints/track_complaint.html', {'form': form, 'complaint': complaint})

def complaint_detail(request, complaint_id):
    """Display complaint details"""
    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    
    # Check if user can view this complaint (either owner or staff)
    if not (request.user.is_authenticated and (request.user == complaint.user or request.user.is_staff)):
        messages.error(request, 'You do not have permission to view this complaint.')
        return redirect('complaints:home')
    
    # Check if feedback exists
    feedback = None
    can_give_feedback = False
    
    if complaint.status == 'RESOLVED' and request.user == complaint.user:
        try:
            feedback = Feedback.objects.get(complaint=complaint)
        except Feedback.DoesNotExist:
            can_give_feedback = True
    
    # Get status history for timeline
    from .models import ComplaintStatusHistory
    status_history = ComplaintStatusHistory.objects.filter(complaint=complaint).order_by('changed_at')
    
    context = {
        'complaint': complaint,
        'feedback': feedback,
        'can_give_feedback': can_give_feedback,
        'status_history': status_history,
    }
    return render(request, 'complaints/complaint_detail.html', context)

@login_required
def give_feedback(request, complaint_id):
    """Give feedback for a resolved complaint"""
    complaint = get_object_or_404(Complaint, complaint_id=complaint_id, user=request.user)
    
    if complaint.status != 'RESOLVED':
        messages.error(request, 'You can only give feedback for resolved complaints.')
        return redirect('complaints:complaint_detail', complaint_id=complaint_id)
    
    # Check if feedback already exists
    if Feedback.objects.filter(complaint=complaint).exists():
        messages.info(request, 'You have already provided feedback for this complaint.')
        return redirect('complaints:complaint_detail', complaint_id=complaint_id)
    
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.complaint = complaint
            feedback.save()
            
            messages.success(request, 'Thank you for your feedback!')
            return redirect('complaints:complaint_detail', complaint_id=complaint_id)
    else:
        form = FeedbackForm()
    
    return render(request, 'complaints/give_feedback.html', {'form': form, 'complaint': complaint})


# Email utility functions
def send_complaint_email(complaint):
    """Send email notification when complaint is submitted"""
    from django.conf import settings
    
    # Check if email notifications are enabled
    if not getattr(settings, 'ENABLE_EMAIL_NOTIFICATIONS', True):
        print("Email notifications are disabled in settings")
        return
    
    subject = f'Complaint Submitted - {complaint.complaint_id}'
    
    # Use first name if available, otherwise username
    user_name = complaint.user.first_name or complaint.user.username
    
    # Create complaint view URL
    complaint_url = f"{settings.SITE_URL}/complaint/{complaint.complaint_id}/"
    
    message = f'''
Dear {user_name},

Your complaint has been successfully submitted and assigned ID: {complaint.complaint_id}

Complaint Details:
- Title: {complaint.title}
- Category: {complaint.category.name}
- Location: {complaint.location}
- Status: {complaint.get_status_display()}
- Submitted: {complaint.created_at.strftime('%B %d, %Y at %I:%M %p')}

You can track your complaint progress at:
{complaint_url}

We will review your complaint and keep you updated on the progress.

Thank you for using CivicVoice to make your community better.

Best regards,
CivicVoice Support Team
    '''
    
    # Create HTML version
    html_message = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f4f4f4; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; background: #007bff; color: white; padding: 20px; border-radius: 8px 8px 0 0; margin: -20px -20px 20px -20px; }}
            .complaint-box {{ background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff; margin: 15px 0; }}
            .button {{ display: inline-block; background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🏛️ CivicVoice</h2>
                <p>Complaint Successfully Submitted</p>
            </div>
            
            <p>Dear <strong>{user_name}</strong>,</p>
            
            <p>Your complaint has been successfully submitted and assigned the following ID:</p>
            
            <div class="complaint-box">
                <h3>📋 Complaint Details</h3>
                <p><strong>ID:</strong> {complaint.complaint_id}</p>
                <p><strong>Title:</strong> {complaint.title}</p>
                <p><strong>Category:</strong> {complaint.category.name}</p>
                <p><strong>Location:</strong> {complaint.location}</p>
                <p><strong>Status:</strong> <span style="background: #ffc107; color: #000; padding: 2px 8px; border-radius: 3px;">{complaint.get_status_display()}</span></p>
                <p><strong>Submitted:</strong> {complaint.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
            
            <p>You can track your complaint progress using the link below:</p>
            
            <div style="text-align: center;">
                <a href="{complaint_url}" class="button">🔍 Track Your Complaint</a>
            </div>
            
            <p>We will review your complaint and keep you updated on the progress.</p>
            
            <div class="footer">
                <p>Thank you for using CivicVoice to make your community better.</p>
                <p><strong>CivicVoice Support Team</strong></p>
            </div>
        </div>
    </body>
    </html>
    '''
    
    try:
        from django.core.mail import EmailMultiAlternatives
        
        msg = EmailMultiAlternatives(
            subject,
            message,  # Plain text version
            settings.DEFAULT_FROM_EMAIL,
            [complaint.user.email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_status_update_email(complaint, old_status):
    """Send email notification when complaint status is updated"""
    from django.conf import settings
    
    # Check if email notifications are enabled
    if not getattr(settings, 'ENABLE_EMAIL_NOTIFICATIONS', True):
        print("Email notifications are disabled in settings")
        return
    
    subject = f'Complaint Status Update - {complaint.complaint_id}'
    
    # Use first name if available, otherwise username
    user_name = complaint.user.first_name or complaint.user.username
    
    # Create complaint view URL
    complaint_url = f"{settings.SITE_URL}/complaint/{complaint.complaint_id}/"
    
    # Format old status for display
    old_status_display = old_status.replace('_', ' ').title() if old_status else 'Unknown'
    
    # Get status-specific message
    status_message = ""
    if complaint.status == 'IN_PROGRESS':
        status_message = "Your complaint is now being actively reviewed and processed by our team."
    elif complaint.status == 'RESOLVED':
        status_message = "Great news! Your complaint has been resolved. You can now provide feedback about your experience."
    elif complaint.status == 'ESCALATED':
        status_message = "Your complaint has been escalated to a senior team member for priority handling."
    elif complaint.status == 'CLOSED':
        status_message = "Your complaint has been closed. Thank you for using CivicVoice."
    
    message = f'''
Dear {user_name},

Your complaint status has been updated:

Complaint ID: {complaint.complaint_id}
Title: {complaint.title}
Previous Status: {old_status_display}
New Status: {complaint.get_status_display()}
Updated: {complaint.updated_at.strftime('%B %d, %Y at %I:%M %p')}

{status_message}

{f"Official Remarks: {complaint.admin_remarks}" if complaint.admin_remarks else ""}

View your complaint details:
{complaint_url}

Thank you for using CivicVoice.

Best regards,
CivicVoice Support Team
    '''
    
    # Status color mapping
    status_colors = {
        'PENDING': '#ffc107',
        'IN_PROGRESS': '#007bff', 
        'RESOLVED': '#28a745',
        'ESCALATED': '#dc3545',
        'CLOSED': '#6c757d'
    }
    
    status_color = status_colors.get(complaint.status, '#6c757d')
    
    # Create HTML version
    html_message = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f4f4f4; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; background: {status_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; margin: -20px -20px 20px -20px; }}
            .status-box {{ background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid {status_color}; margin: 15px 0; }}
            .status-change {{ background: #e9ecef; padding: 10px; border-radius: 5px; margin: 10px 0; }}
            .button {{ display: inline-block; background: {status_color}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }}
            .remarks {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 10px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🏛️ CivicVoice</h2>
                <p>Complaint Status Updated</p>
            </div>
            
            <p>Dear <strong>{user_name}</strong>,</p>
            
            <p>Your complaint status has been updated:</p>
            
            <div class="status-box">
                <h3>📊 Status Update</h3>
                <p><strong>Complaint ID:</strong> {complaint.complaint_id}</p>
                <p><strong>Title:</strong> {complaint.title}</p>
                
                <div class="status-change">
                    <p><strong>Previous Status:</strong> {old_status_display}</p>
                    <p><strong>New Status:</strong> <span style="background: {status_color}; color: white; padding: 2px 8px; border-radius: 3px;">{complaint.get_status_display()}</span></p>
                    <p><strong>Updated:</strong> {complaint.updated_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
            </div>
            
            <p>{status_message}</p>
            
            {f'<div class="remarks"><strong>📝 Official Remarks:</strong><br>{complaint.admin_remarks}</div>' if complaint.admin_remarks else ''}
            
            <div style="text-align: center;">
                <a href="{complaint_url}" class="button">🔍 View Complaint Details</a>
            </div>
            
            <div class="footer">
                <p>Thank you for using CivicVoice.</p>
                <p><strong>CivicVoice Support Team</strong></p>
            </div>
        </div>
    </body>
    </html>
    '''
    
    try:
        from django.core.mail import EmailMultiAlternatives
        
        msg = EmailMultiAlternatives(
            subject,
            message,  # Plain text version
            settings.DEFAULT_FROM_EMAIL,
            [complaint.user.email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
    except Exception as e:
        print(f"Failed to send email: {e}")
