from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .forms import ParentSignupForm, StyledAuthenticationForm


class RoleBasedLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = StyledAuthenticationForm

    def get_success_url(self):
        user = self.request.user
        if user.role == 'parent':
            return '/parents/dashboard/'
        return super().get_success_url()


@require_http_methods(['GET', 'POST'])
def parent_signup(request):
    if request.user.is_authenticated:
        if request.user.role == 'parent':
            return redirect('parents:dashboard')
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = ParentSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            student_id = form.cleaned_data.get('student_id', '').strip()
            child_dob = form.cleaned_data.get('child_dob')

            if student_id and child_dob:
                from students.models import Student
                try:
                    student = Student.objects.get(
                        student_id__iexact=student_id,
                        date_of_birth=child_dob,
                        is_active=True,
                    )
                    if student.parent and student.parent != user:
                        messages.warning(
                            request,
                            'Account created, but that child is already linked to another parent. '
                            'Contact the school office for assistance.'
                        )
                    else:
                        student.parent = user
                        student.save()
                        messages.success(request, f'Successfully linked {student.get_full_name()}.')
                except Student.DoesNotExist:
                    messages.warning(
                        request,
                        'Account created, but we could not verify the child with that ID and date of birth. '
                        'You can link your child from the parent dashboard.'
                    )

            login(request, user)
            messages.success(request, 'Welcome! Your parent account is ready.')
            return redirect('parents:dashboard')
    else:
        form = ParentSignupForm()

    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.address = request.POST.get('address', user.address)
        if request.FILES.get('profile_pic'):
            user.profile_pic = request.FILES['profile_pic']
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html')