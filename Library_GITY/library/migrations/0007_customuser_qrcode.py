# Generated by Django 4.2.7 on 2024-04-30 06:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0006_book_description_book_image_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='QRcode',
            field=models.ImageField(null=True, upload_to='media/image/'),
        ),
    ]
