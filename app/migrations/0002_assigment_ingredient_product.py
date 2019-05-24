# Generated by Django 2.2 on 2019-04-27 20:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sku', models.CharField(default='', max_length=10)),
                ('name', models.TextField()),
                ('description', models.TextField()),
                ('sale_price', models.IntegerField(default=0)),
                ('number_ingredients_needed', models.IntegerField(default=0)),
                ('number_products', models.IntegerField(default=0)),
                ('expected_duration_time', models.FloatField()),
                ('equivalence_units', models.FloatField()),
                ('measurement_unit', models.CharField(default='', max_length=10)),
                ('production_lot', models.IntegerField()),
                ('expected_production_time', models.IntegerField()),
                ('producer_groups', models.TextField()),
                ('dispatch_space', models.IntegerField()),
                ('reception_space', models.IntegerField()),
                ('minimum_stock', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.TextField()),
                ('ingredient_name', models.TextField()),
                ('quantity', models.FloatField()),
                ('measurement_unit', models.CharField(default='', max_length=10)),
                ('production_lot', models.IntegerField()),
                ('quantity_for_lot', models.FloatField()),
                ('units_quantity', models.IntegerField()),
                ('ingredient_sku', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ingredients_column', to='app.Product')),
                ('product_sku', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products_column', to='app.Product')),
            ],
        ),
        migrations.CreateModel(
            name='Assigment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.IntegerField()),
                ('sku', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.Product')),
            ],
        ),
    ]
