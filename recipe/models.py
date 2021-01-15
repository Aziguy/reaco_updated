from django.db import models
from ckeditor.fields import RichTextField
from django.contrib.postgres.fields import ArrayField

# Create your models here.
class Drive(models.Model):
	name = models.CharField(max_length=100, blank=False)
	image = models.ImageField(upload_to='drive/', blank=False)
	address = models.CharField(max_length=256, blank=False)
	created_date = models.DateTimeField(auto_now_add=True)
	"""docstring for ClassName"""
	def __str__(self):
		return self.name

class Categorie(models.Model):
	name = models.CharField(max_length=100, blank=False)
	"""docstring for ClassName"""
	def __str__(self):
		return self.name

class Ingredient(models.Model):
	name = models.CharField(max_length=100, blank=False)
	image = models.ImageField(upload_to='ingredient/', blank=False)
	drive = models.ManyToManyField(Drive, through='Drive_Ingredient')
	categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE)
	created_date = models.DateTimeField(auto_now_add=True)
	"""docstring for ClassName"""
	def __str__(self):
		return self.name

class Drive_Ingredient(models.Model):
	ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
	drive = models.ForeignKey(Drive, on_delete=models.CASCADE)
	price = models.DecimalField(max_digits=5, decimal_places=2)
	created_date = models.DateTimeField(auto_now_add=True)
	"""docstring for ClassName"""
	class Meta:
		unique_together = [['ingredient', 'drive']]

class Recipe(models.Model):
	categorie_choice = (
		('Entrées / Hors d\'oeuvre', 'Entrées / Hors d\'oeuvre'),
		('Soupes', 'Soupes'),
		('Salades', 'Salades'),
		('Plats principaux', 'Plats principaux'),
		('Desserts', 'Desserts'),
		('Collations', 'Collations'),
		('Petits déjeuner', 'Petits déjeuner'),
		('Sandwiches', 'Sandwiches'),
		('Boîte à lunch (Panier repas)', 'Boîte à lunch (Panier repas)'),
		('Sauces et trempettes', 'Sauces et trempettes'),
		('Vinaigrettes', 'Vinaigrettes'),
		('Boissons', 'Boissons'),
	)

	level_choice = (
		('Très facile', 'Très facile'),
		('Facile', 'Facile'),
		('Intermédiaire', 'Intermédiaire'),
		('Master', 'Master'),
	)

	portion_choice = (
		('1', '1'),
		('2', '2'),
		('3', '3'),
		('4', '4'),
		('5', '5'),
	)

	cook_choice = []
	for i in range(0, 65, 5):
		cook_choice.append((i,i))

	prep_choice = []
	for i in range(0, 35, 5):
		prep_choice.append((i,i))

	diet_choice = (
		('Hyperproteiné', 'Hyperproteiné'),
		('Protéiné', 'Protéiné'),
		('Dissocié', 'Hyperproteiné'),
		('Hyperproteiné', 'Dissocié'),
		('Anticellulite', 'Anticellulite'),
		('Détox', 'Détox'),
		('Sans sel', 'Sans sel'),
		('Hypoglucidique', 'Hypoglucidique'),
	)

	category = models.CharField(choices=categorie_choice, max_length=100)
	level = models.CharField(choices=level_choice, max_length=50)
	name = models.CharField(max_length=200, blank=False)
	ingredients = models.ManyToManyField(Ingredient)
	portion = models.CharField(choices=portion_choice, max_length=10)
	cooking_time = models.IntegerField(('cooking_time'), choices=cook_choice)
	preparation = models.IntegerField(('preparation'), choices=prep_choice)
	diet = models.CharField(choices=diet_choice, max_length=100)
	origine = models.CharField(max_length=200, blank=False)
	kcal = models.IntegerField()
	proteins = models.IntegerField()
	lipids = models.IntegerField()
	glucids = models.IntegerField()
	#test = ArrayField(ArrayField(models.DateTimeField(max_length=10, blank=True), size=8,), size=8,)
	is_feature = models.BooleanField(default=False)
	steps = RichTextField()
	recipe_photo = models.ImageField(upload_to='recipe/', blank=False)
	recipe_photo_1 = models.ImageField(upload_to='recipe/', blank=False)
	recipe_photo_2 = models.ImageField(upload_to='recipe/', blank=False)
	recipe_photo_3 = models.ImageField(upload_to='recipe/', blank=False)
	recipe_photo_4 = models.ImageField(upload_to='recipe/', blank=False)
	created_date = models.DateTimeField(auto_now_add=True)
	"""docstring for ClassName"""

# is_validate = models.BooleanField(default=False)
# categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL)
# Good will look to you today..
