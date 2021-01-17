from django.db import models
from datetime import datetime

# Create your models here.
class Dashboard(models.Model):
	first_name = models.CharField(max_length=100)
	last_name = models.CharField(max_length=100)
	recipe_id = models.IntegerField()
	recipe_name = models.CharField(max_length=100)
	recipe_photo = models.CharField(max_length=100)
	user_id = models.IntegerField(blank=True)
	create_date = models.DateTimeField(blank=True, default=datetime.now)

	def __str__(self):
		return self.last_name

		