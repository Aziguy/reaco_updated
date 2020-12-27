from django.db import models
from ckeditor.fields import RichTextField

# Create your models here.
class Slider(models.Model):
	titre = models.CharField(max_length=100, blank=False)
	description = RichTextField()
	image = models.ImageField(upload_to='slider/', blank=False)
	"""docstring for ClassName"""
	def __str__(self):
		return self.titre

class Info(models.Model):
	numero = models.CharField(max_length=50, blank=False)
	email = models.CharField(max_length=50, blank=False)
	horaire = models.CharField(max_length=50, blank=False)
	site = models.CharField(max_length=50, blank=False)
	fax = models.CharField(max_length=50, blank=False)
	"""docstring for ClassName"""
	def __str__(self):
		return self.numero

class Team(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    photo = models.ImageField(upload_to='teams/')
    facebook_link = models.URLField(max_length=100)
    twitter_link = models.URLField(max_length=100)
    linkedin_link = models.URLField(max_length=100)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.first_name

class Service(models.Model):
    icone = models.CharField(max_length=255)
    numero = models.IntegerField()
    titre = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre

class AboutDesc(models.Model):
	titre1 = models.CharField(max_length=20, blank=False)
	titre2 = models.CharField(max_length=20, blank=False)
	description = RichTextField()
	image1 = models.ImageField(upload_to='abouts/', blank=False)
	image2 = models.ImageField(upload_to='abouts/', blank=False)
	image3 = models.ImageField(upload_to='abouts/', blank=False)
	"""docstring for ClassName"""
	def __str__(self):
		return self.titre1
		