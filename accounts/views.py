from django.shortcuts import render, redirect
from django.contrib import messages, auth
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from pages.models import Info
from dashboard.models import Dashboard

# Create your views here.
def login(request):
	infosdata = Info.objects.all()[0]
	context = {
		'infos' : infosdata
	}
	if request.method == 'POST':
		username = request.POST['username']
		password = request.POST['password']

		user = auth.authenticate(username=username, password=password)

		if user is not None:
			auth.login(request, user)
			messages.success(request, 'Vous êtes maintenant connecté')
			return redirect('dashboard')
		else:
			messages.error(request, 'Identifiants de connexion non valides!')
			return redirect('login')
	return render(request, 'accounts/login.html', context)

def register(request):
	infosdata = Info.objects.all()[0]
	context = {
		'infos' : infosdata
	}

	if request.method == 'POST':
		firstname = request.POST['firstname']
		lastname = request.POST['lastname']
		username = request.POST['username']
		email = request.POST['email']
		password = request.POST['password']
		confirm_password = request.POST['confirm_password']

		if password == confirm_password:
			if User.objects.filter(username=username).exists():
				messages.error(request, 'Ce nom d\'utilisateur est déjà pris!')
				return redirect('register')
			else:
				if User.objects.filter(email=email).exists():
					messages.error(request, 'Cet email est déjà pris!')
					return redirect('register')
				else:
					user = User.objects.create_user(first_name=firstname, last_name=lastname, email=email, username=username, password=password)
					auth.login(request, user)
					messages.success(request, 'Vous êtes maintenant connecté')
					return redirect('dashboard')
					user.save()
					messages.success(request, 'Vous vous êtes inscrit avec succès.')
					return redirect('login')
		else:
			messages.error(request, 'Le mot de passe ne correspond pas')
			return redirect('register')
	else:
		return render(request, 'accounts/register.html', context)


@login_required(login_url = 'login')
def dashboard(request):
	user_inquiry = Dashboard.objects.order_by('-create_date').filter(user_id=request.user.id)
	infosdata = Info.objects.all()[0]
	context = {
		'infos' : infosdata,
		'inquiries': user_inquiry,
	}
	return render(request, 'accounts/dashboard.html', context)


@login_required(login_url = 'login')
def pdf(request):
	return render(request, 'accounts/pdf.html')


def logout(request):
    if request.method == 'POST':
        auth.logout(request)
        return redirect('home')
    return redirect('home')

# Random price
# list_for_random_1 = (3, 6, 2)
# return render(...{'list_for_random_1': list_for_random_1,}) 

# list_for_random_2 = (0, 99, 10)
# return render(...{'list_for_random_2': list_for_random_2,})