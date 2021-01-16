from django.shortcuts import render
from . import views
from . models import Info, Slider, Team, Service, AboutDesc
from recipe.models import Recipe

# Create your views here.

def home(request):
	sliderdata = Slider.objects.all()
	infosdata = Info.objects.all()[0]
	teams = Team.objects.all()
	recipe_feature = Recipe.objects.order_by('-created_date').filter(is_feature=True)
	all_recipe = Recipe.objects.order_by('-created_date')
	category_search = Recipe.objects.values_list('category', flat=True).distinct().order_by('category')
	level_search = Recipe.objects.values_list('level', flat=True).distinct().order_by('level')
	origine_search = Recipe.objects.values_list('origine', flat=True).distinct().order_by('origine')
	time_search = Recipe.objects.values_list('cooking_time', flat=True).distinct().order_by('cooking_time')
	diet_search = Recipe.objects.values_list('diet', flat=True).distinct().order_by('diet')
	context = {
		'slider': sliderdata,
		'infos' : infosdata,
		'teams': teams,
		'recipe_feature': recipe_feature,
		'all_recipe': all_recipe,
		'category_search':category_search,
		'level_search':level_search,
		'origine_search':origine_search,
		'time_search':time_search,
		'diet_search':diet_search,
	}
	return render(request, 'pages/index.html', context)

def about(request):
	infosdata = Info.objects.all()[0]
	teamdata = Team.objects.all()
	aboutdescdata = AboutDesc.objects.all()[0]
	context = {
		'infos' : infosdata,
		'teams': teamdata,
		'aboutdesc': aboutdescdata
	}
	return render(request, 'pages/about.html', context)

def services(request):
	infosdata = Info.objects.all()[0]
	servicesdata = Service.objects.all()
	context = {
		'infos' : infosdata,
		'services' : servicesdata,
	}
	return render(request, 'pages/services.html', context)

def contact(request):
	infosdata = Info.objects.all()[0]
	context = {
		'infos' : infosdata,
	}
	return render(request, 'pages/contact.html', context)