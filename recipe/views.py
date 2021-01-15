from django.shortcuts import render, get_object_or_404
from pages.models import Info
from . models import Recipe
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
# Create your views here.

def recipe(request):
	infosdata = Info.objects.all()[0]
	context = {
		'infos' : infosdata,
	}
	return render(request, 'recipes/recipe.html', context)

def recipe_details(request, id):
	infosdata = Info.objects.all()[0]
	single_recipe = get_object_or_404(Recipe, pk=id)
	context = {
		'infos' : infosdata,
		'single_recipe' : single_recipe,
	}
	return render(request, 'recipes/recipe_details.html', context)
