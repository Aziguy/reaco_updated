from django.shortcuts import render
from . import views
from pages.models import Info
# Create your views here.

def recipe(request):
	infosdata = Info.objects.all()[0]
	context = {
		'infos' : infosdata,
	}
	return render(request, 'recipes/recipe.html', context)
