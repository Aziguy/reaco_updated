from django.shortcuts import render
from . import views
from . models import Info, Slider, Team, Service, AboutDesc

# Create your views here.

def home(request):
	sliderdata = Slider.objects.all()
	infosdata = Info.objects.all()[0]
	teams = Team.objects.all()
	context = {
		'slider': sliderdata,
		'infos' : infosdata,
		'teams': teams
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
		'services' : servicesdata
	}
	return render(request, 'pages/services.html', context)

def contact(request):
	infosdata = Info.objects.all()[0]
	context = {
		'infos' : infosdata
	}
	return render(request, 'pages/contact.html', context)