from django.shortcuts import render, get_object_or_404
from pages.models import Info
from . models import Recipe
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
# Create your views here.

def recipe(request):
	infosdata = Info.objects.all()[0]
	recipes = Recipe.objects.order_by('-created_date')
	paginator = Paginator(recipes, 4)
	page = request.GET.get('page')
	paged_recipes = paginator.get_page(page)
	context = {
		'infos' : infosdata,
		'recipes' : paged_recipes,
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
