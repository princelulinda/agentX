from django.db import migrations
from decimal import Decimal

def create_initial_plans(apps, schema_editor):
    InvestmentPlan = apps.get_model('investments', 'InvestmentPlan')
    
    # Plan Starter
    InvestmentPlan.objects.create(
        name='Plan Starter',
        description='Plan d\'investissement de départ avec un rendement quotidien de 0.05%',
        minimum_investment=Decimal('10.00'),
        daily_return=Decimal('0.05'),
        level=1,
        is_active=True
    )

    # Plan Advanced
    InvestmentPlan.objects.create(
        name='Plan Advanced',
        description='Plan d\'investissement intermédiaire avec un rendement quotidien de 0.1%',
        minimum_investment=Decimal('29.00'),
        daily_return=Decimal('0.1'),
        level=2,
        is_active=True
    )

    # Plan Premium
    InvestmentPlan.objects.create(
        name='Plan Premium',
        description='Plan d\'investissement premium avec un rendement quotidien de 0.15%',
        minimum_investment=Decimal('50.00'),
        daily_return=Decimal('0.15'),
        level=3,
        is_active=True
    )

def remove_initial_plans(apps, schema_editor):
    InvestmentPlan = apps.get_model('investments', 'InvestmentPlan')
    InvestmentPlan.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('investments', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_plans, remove_initial_plans),
    ]
