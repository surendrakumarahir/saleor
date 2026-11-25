# Generated migration file for banner models

# After running: python manage.py makemigrations banner

# Copy this file to saleor/banner/migrations/0001_initial.py

"""
Initial migration for banner models.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('channel', '0001_initial'),  # Adjust based on your channel migration
    ]

    operations = [
        migrations.CreateModel(
            name='ImageCollection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='banner_collections', to='channel.channel')),
            ],
            options={
                'verbose_name': 'Image Collection',
                'verbose_name_plural': 'Image Collections',
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='Banner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('image', models.ImageField(upload_to='banners/')),
                ('alt_text', models.CharField(blank=True, max_length=255)),
                ('link_url', models.URLField(blank=True, null=True)),
                ('link_text', models.CharField(blank=True, max_length=100)),
                ('custom_field_1', models.CharField(blank=True, max_length=255)),
                ('custom_field_2', models.CharField(blank=True, max_length=255)),
                ('custom_field_3', models.CharField(blank=True, max_length=255)),
                ('key_values', models.JSONField(blank=True, default=dict)),
                ('position', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('image_collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='banners', to='banner.imagecollection')),
            ],
            options={
                'verbose_name': 'Banner',
                'verbose_name_plural': 'Banners',
                'ordering': ('position', '-created_at'),
            },
        ),
        migrations.AddIndex(
            model_name='banner',
            index=models.Index(fields=('image_collection', 'position'), name='banner_bann_image_c_idx'),
        ),
        migrations.AddIndex(
            model_name='banner',
            index=models.Index(fields=('is_active', 'start_date', 'end_date'), name='banner_bann_is_acti_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='imagecollection',
            unique_together={('name', 'channel')},
        ),
    ]
