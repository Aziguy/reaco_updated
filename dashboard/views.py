from django.shortcuts import render, redirect
from django.contrib import messages
from . models import Dashboard
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required(login_url = 'login')
def inquiry(request):
	if request.method == 'POST':
		recipe_id = request.POST['recipe_id']
		recipe_name = request.POST['recipe_name']
		recipe_photo = request.POST['recipe_photo']
		user_id = request.POST['user_id']
		first_name = request.POST['first_name']
		last_name = request.POST['last_name']

		if request.user.is_authenticated:
			user_id = request.user.id
			has_contacted = Dashboard.objects.all().filter(recipe_id=recipe_id, user_id=user_id)
			if has_contacted:
				messages.error(request, 'Vous avez déjà cette recette dans votre tableau de bord !!!')
				return redirect('/recipe/'+recipe_id)

		dashboard = Dashboard(recipe_id=recipe_id, recipe_name=recipe_name, recipe_photo=recipe_photo, user_id=user_id, 
			first_name=first_name, last_name=last_name)

		admin_info = User.objects.get(is_superuser=True)
		admin_email = admin_info.email
		send_mail(
                'Ajout d\'une recette',
                'La recette ' + recipe_name + ' a été ajouté depuis le site. Connectez vous à l\'admin pour plus d\'informations.',
                'mandatairessm@gmail.com',
                [admin_email],
                fail_silently=False,
            )

		dashboard.save()
		messages.success(request, 'La recette a bien été ajouté à votre tableau de bord.')
		return redirect('/recipe/'+recipe_id)