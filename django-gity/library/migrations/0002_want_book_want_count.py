# Generated by Django 5.1 on 2024-08-18 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='want_book',
            name='want_count',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]