from allauth.mfa.utils import is_mfa_enabled
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import DeleteAccountForm, ProfileForm


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil mis à jour.")
        return redirect("accounts:profile")
    context = {"form": form, "mfa_enabled": is_mfa_enabled(request.user)}
    return render(request, "accounts/profile.html", context)


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Votre compte et vos données ont été supprimés.")
        return redirect("core:home")
    return render(request, "accounts/delete.html", {"form": form})
