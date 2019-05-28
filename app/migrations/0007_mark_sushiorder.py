# Generated by Django 2.2.1 on 2019-05-27 23:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0006_idoc'),
    ]

    operations = [
        migrations.CreateModel(
            name='Mark',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='SushiOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('oc', models.TextField()),
                ('delivery_date', models.BigIntegerField()),
                ('dispatched', models.BooleanField(default=False)),
                ('sku', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.Product')),
            ],
            options={
                'ordering': ('delivery_date',),
            },
        ),
    ]