"""Authentication views."""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.conf import settings
from django.views import View

from accounts.forms import ADLoginForm


class LoginView(View):
    """Display and process the AD login form."""
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        form = ADLoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ADLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', settings.LOGIN_REDIRECT_URL)
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        return render(request, self.template_name, {'form': form})


def logout_view(request):
    """Log the user out and redirect to the login page."""
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)
