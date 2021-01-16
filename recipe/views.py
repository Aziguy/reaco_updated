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

	category_search = Recipe.objects.values_list('category', flat=True).distinct().order_by('category')
	level_search = Recipe.objects.values_list('level', flat=True).distinct().order_by('level')
	origine_search = Recipe.objects.values_list('origine', flat=True).distinct().order_by('origine')
	time_search = Recipe.objects.values_list('cooking_time', flat=True).distinct().order_by('cooking_time')
	diet_search = Recipe.objects.values_list('diet', flat=True).distinct().order_by('diet')

	context = {
		'infos' : infosdata,
		'recipes' : paged_recipes,
		'category_search':category_search,
		'level_search':level_search,
		'origine_search':origine_search,
		'time_search':time_search,
		'diet_search':diet_search,
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

def search(request):
    infosdata = Info.objects.all()[0]
    recipes = Recipe.objects.order_by('-created_date')
    category_search = Recipe.objects.values_list('category', flat=True).distinct().order_by('category')
    level_search = Recipe.objects.values_list('level', flat=True).distinct().order_by('level')
    origine_search = Recipe.objects.values_list('origine', flat=True).distinct().order_by('origine')
    time_search = Recipe.objects.values_list('cooking_time', flat=True).distinct().order_by('cooking_time')
    diet_search = Recipe.objects.values_list('diet', flat=True).distinct().order_by('diet')
    portion_search = Recipe.objects.values_list('portion', flat=True).distinct().order_by('portion')

    if 'keyword' in request.GET:
    	keyword = request.GET['keyword']
    	if keyword:
    		recipes = recipes.filter(name__icontains=keyword)

    if 'category' in request.GET:
    	category = request.GET['category']
    	if category:
    		recipes = recipes.filter(category__iexact=category)

    if 'level' in request.GET:
    	level = request.GET['level']
    	if level:
    		recipes = recipes.filter(level__iexact=level)

    if 'origine' in request.GET:
    	origine = request.GET['origine']
    	if origine:
    		recipes = recipes.filter(origine__iexact=origine)

    if 'cooking_time' in request.GET:
    	cooking_time = request.GET['cooking_time']
    	if cooking_time:
    		recipes = recipes.filter(cooking_time__iexact=cooking_time)

    if 'diet' in request.GET:
    	diet = request.GET['diet']
    	if diet:
    		recipes = recipes.filter(diet__iexact=diet)

    if 'portion' in request.GET:
        portion = request.GET['portion']
        if portion:
            recipes = recipes.filter(portion__iexact=portion)

    if 'min_kcal' in request.GET:
    	min_kcal = request.GET['min_kcal']
    	max_kcal = request.GET['max_kcal']
    	if max_kcal:
    		recipes = recipes.filter(kcal__gte=min_kcal, kcal__lte=max_kcal)

    context = {
        'infos' : infosdata,
        'recipes': recipes,
        'category_search':category_search,
		'level_search':level_search,
		'origine_search':origine_search,
		'time_search':time_search,
		'diet_search':diet_search,
        'portion_search':portion_search,
    }
    return render(request, 'recipes/search.html', context)