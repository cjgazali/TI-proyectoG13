# Generated by Django 2.2 on 2019-04-24 21:36

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('client_group', models.IntegerField(default=0)),
                ('sku', models.CharField(default='', max_length=10)),
                ('amount', models.IntegerField(default=0)),
                ('storeId', models.CharField(default='', max_length=30)),
                ('accepted', models.BooleanField(default=False)),
                ('dispatched', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('created',),
            },
        ),
    ]
