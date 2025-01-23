from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from web3 import Web3
import secrets
import eth_account
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.

class InvestmentPlan(models.Model):
    RISK_CHOICES = [
        ('STARTER', 'Starter'),
        ('ADVANCED', 'Advanced'),
        ('PREMIUM', 'Premium'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    minimum_investment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    maximum_investment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )
    daily_return = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        help_text='Daily return in percentage',
        default=0.05
    )
    level = models.IntegerField(
        default=1,
        help_text='Plan level (1 for starter, 2 for advanced, etc.)'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Level {self.level})"

    class Meta:
        ordering = ['level']

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    referral_code = models.CharField(max_length=20, unique=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    total_referral_earnings = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('0'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            # Générer un code de parrainage unique
            self.referral_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profile de {self.user.email}"

    class Meta:
        verbose_name = "Profil Utilisateur"
        verbose_name_plural = "Profils Utilisateurs"

class USDTWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='usdt_wallet')
    address = models.CharField(max_length=42, unique=True, blank=True)
    balance = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=Decimal('0'),
        validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_unique_address(self):
        """Génère une adresse Ethereum unique"""
        import secrets
        import eth_account

        while True:
            # Générer une clé privée aléatoire
            private_key = secrets.token_hex(32)
            account = eth_account.Account.from_key(private_key)
            address = account.address
            
            # Vérifier si l'adresse existe déjà
            if not USDTWallet.objects.filter(address=address).exists():
                return address

    def save(self, *args, **kwargs):
        if not self.address:
            self.address = self.generate_unique_address()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Portefeuille de {self.user.email}"

    class Meta:
        verbose_name = "Portefeuille USDT"
        verbose_name_plural = "Portefeuilles USDT"

class USDTTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('INVESTMENT', 'Investment'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('EARNINGS', 'Earnings'),
        ('REFERRAL_BONUS', 'Referral Bonus'),
        ('INVESTMENT_UPGRADE', 'Investment Upgrade')
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    wallet = models.ForeignKey(USDTWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=6)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    description = models.TextField(blank=True, null=True)
    tx_hash = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.wallet.user.username}'s {self.transaction_type} of {self.amount} USDT"

    class Meta:
        ordering = ['-created_at']

class Investment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('ACTIVE', 'Actif'),
        ('COMPLETED', 'Terminé'),
        ('CANCELLED', 'Annulé'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='investments')
    plan = models.ForeignKey(InvestmentPlan, on_delete=models.PROTECT, related_name='subscriptions')
    amount_invested = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(
        max_length=10,
        default='USDT',
        choices=[('USDT', 'USDT')]
    )
    current_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    total_withdrawn = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    start_date = models.DateTimeField(null=True, blank=True)
    last_earnings_update = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    usdt_transaction = models.ForeignKey(
        USDTTransaction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='investments'
    )
    end_date = models.DateTimeField(null=True, blank=True)
    upgraded_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='upgraded_from'
    )
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(status='ACTIVE'),
                name='unique_active_investment_per_user'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"

    def calculate_earnings(self):
        if self.status != 'ACTIVE' or not self.start_date:
            return Decimal('0')
        
        now = timezone.now()
        days = (now - self.start_date).days
        daily_return = self.plan.daily_return / Decimal('100')
        total_earnings = self.amount_invested * daily_return * days
        
        return total_earnings

    def get_available_earnings(self):
        """Calcule les bénéfices disponibles pour le retrait"""
        if self.status != 'ACTIVE':
            return Decimal('0')
            
        total_earnings = self.calculate_earnings()
        available_earnings = total_earnings - self.total_withdrawn
        
        return max(Decimal('0'), available_earnings)

    def can_withdraw(self, amount):
        """Vérifie si le montant peut être retiré"""
        if self.status != 'ACTIVE':
            return False, "L'investissement n'est pas actif"
            
        available = self.get_available_earnings()
        if amount <= 0:
            return False, "Le montant doit être supérieur à 0"
            
        if amount > available:
            return False, f"Le montant demandé ({amount} USDT) dépasse les bénéfices disponibles ({available} USDT)"
            
        return True, ""

    def save(self, *args, **kwargs):
        if not self.current_value:
            self.current_value = self.amount_invested
        super().save(*args, **kwargs)

    def upgrade_to_plan(self, new_plan, additional_amount):
        if new_plan.level <= self.plan.level:
            raise ValueError("Le nouveau plan doit être d'un niveau supérieur")

        if additional_amount < Decimal('0'):
            raise ValueError("Le montant additionnel doit être positif")

        # Calculer les gains jusqu'à maintenant
        self.calculate_earnings()

        # Créer le nouvel investissement
        new_investment = Investment.objects.create(
            user=self.user,
            plan=new_plan,
            amount_invested=self.current_value + additional_amount,
            currency='USDT',
            status='ACTIVE'
        )

        # Marquer l'ancien investissement comme mis à niveau
        self.status = 'UPGRADED'
        self.end_date = timezone.now()
        self.upgraded_to = new_investment
        self.save()

        return new_investment

# Signal pour créer automatiquement un profil utilisateur
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Signal pour créer automatiquement un profil utilisateur"""
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
        except Exception:
            pass

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Signal pour sauvegarder le profil utilisateur"""
    try:
        if not hasattr(instance, 'profile'):
            UserProfile.objects.create(user=instance)
        else:
            instance.profile.save()
    except Exception:
        pass
