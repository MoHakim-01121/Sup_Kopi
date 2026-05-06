from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_cafeprofile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('supplier', 'Supplier'),
                    ('supplier_staff', 'Supplier Staff'),
                    ('cafe', 'Cafe'),
                ],
                default='cafe',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='SupplierStaff',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('ADMIN', 'Admin Order'), ('LOGISTICS', 'Logistik')],
                    default='ADMIN',
                    max_length=20,
                )),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_staff',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='staff_profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
