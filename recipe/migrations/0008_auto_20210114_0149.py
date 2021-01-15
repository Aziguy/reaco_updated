# Generated by Django 3.1.4 on 2021-01-14 01:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipe', '0007_auto_20210113_0022'),
    ]

    operations = [
        migrations.RenameField(
            model_name='recipe',
            old_name='description',
            new_name='steps',
        ),
        migrations.AddField(
            model_name='recipe',
            name='glucids',
            field=models.IntegerField(default=5),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='recipe',
            name='kcal',
            field=models.IntegerField(default=340),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='recipe',
            name='lipids',
            field=models.IntegerField(default=23),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='recipe',
            name='origine',
            field=models.CharField(default='Normandie, France', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='recipe',
            name='proteins',
            field=models.IntegerField(default=28),
            preserve_default=False,
        ),
    ]