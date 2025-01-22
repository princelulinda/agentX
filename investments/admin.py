from django.contrib import admin
from .models import InvestmentPlan, Investment, USDTWallet, USDTTransaction

# Register your models here.

@admin.register(InvestmentPlan)
class InvestmentPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'level',
        'minimum_investment',
        'daily_return',
        'is_active',
        'created_at'
    ]
    list_filter = ['level', 'is_active']
    search_fields = ['name']

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'plan',
        'amount_invested',
        'currency',
        'status',
        'current_value',
        'start_date'
    ]
    list_filter = ['status', 'currency', 'plan']
    search_fields = ['user__username', 'plan__name']
    raw_id_fields = ['user', 'plan']

@admin.register(USDTWallet)
class USDTWalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'address', 'balance', 'created_at']
    search_fields = ['user__username', 'address']
    raw_id_fields = ['user']

@admin.register(USDTTransaction)
class USDTTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'wallet',
        'transaction_type',
        'amount',
        'status',
        'created_at'
    ]
    list_filter = ['transaction_type', 'status']
    search_fields = ['wallet__user__username', 'tx_hash']
    raw_id_fields = ['wallet']
