from rest_framework import serializers
from .models import (
    InvestmentPlan, 
    Investment, 
    USDTWallet, 
    USDTTransaction,
    UserProfile
)
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal
from rest_framework.validators import UniqueValidator

class InvestmentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentPlan
        fields = [
            'id',
            'name',
            'description',
            'minimum_investment',
            'daily_return',
            'level',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class USDTWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = USDTWallet
        fields = [
            'id',
            'user',
            'address',
            'balance',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['user', 'balance', 'created_at', 'updated_at']

class USDTTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = USDTTransaction
        fields = [
            'id',
            'wallet',
            'transaction_type',
            'amount',
            'tx_hash',
            'status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['wallet', 'status', 'created_at', 'updated_at']

class InvestmentSerializer(serializers.ModelSerializer):
    plan = InvestmentPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=InvestmentPlan.objects.filter(is_active=True),
        source='plan',
        write_only=True
    )
    username = serializers.CharField(source='user.username', read_only=True)
    earnings = serializers.SerializerMethodField()
    usdt_transaction_details = USDTTransactionSerializer(source='usdt_transaction', read_only=True)

    class Meta:
        model = Investment
        fields = [
            'id',
            'user',
            'username',
            'plan',
            'plan_id',
            'amount_invested',
            'currency',
            'usdt_transaction',
            'usdt_transaction_details',
            'current_value',
            'status',
            'start_date',
            'last_earnings_update',
            'earnings',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'user',
            'username',
            'current_value',
            'status',
            'start_date',
            'last_earnings_update',
            'created_at',
            'updated_at'
        ]

    def get_earnings(self, obj):
        return obj.calculate_earnings() if obj.status == 'ACTIVE' else 0

    def validate(self, data):
        # Valider le montant minimum d'investissement
        plan = data.get('plan')
        amount = data.get('amount_invested')
        currency = data.get('currency', 'USD')

        if plan and amount:
            if amount < plan.minimum_investment:
                raise serializers.ValidationError(
                    f"Le montant minimum d'investissement pour ce plan est de {plan.minimum_investment}"
                )

        # Valider le solde USDT si nécessaire
        if currency == 'USDT':
            request = self.context.get('request')
            if not request or not request.user:
                raise serializers.ValidationError("Utilisateur non authentifié")

            try:
                wallet = USDTWallet.objects.get(user=request.user)
                if wallet.balance < amount:
                    raise serializers.ValidationError(
                        f"Solde USDT insuffisant. Solde actuel: {wallet.balance} USDT"
                    )
            except USDTWallet.DoesNotExist:
                raise serializers.ValidationError(
                    "Vous devez créer un portefeuille USDT avant d'investir en USDT"
                )

        return data

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    if not user.is_active:
                        raise serializers.ValidationError('Compte désactivé')
                    data['user'] = user
                    return data
                else:
                    raise serializers.ValidationError('Email ou mot de passe incorrect')
            except User.DoesNotExist:
                raise serializers.ValidationError('Email ou mot de passe incorrect')
        else:
            raise serializers.ValidationError('Veuillez fournir email et mot de passe')

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'password_confirm', 'first_name', 'last_name', 'referral_code')

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                "password": "Les mots de passe ne correspondent pas."
            })

        # Validation du code de parrainage
        referral_code = attrs.get('referral_code')
        if referral_code:
            try:
                UserProfile.objects.get(referral_code=referral_code)
            except UserProfile.DoesNotExist:
                raise serializers.ValidationError({
                    "referral_code": "Code de parrainage invalide."
                })

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        referral_code = validated_data.pop('referral_code', None)
        
        user = User.objects.create(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        
        user.set_password(validated_data['password'])
        user.save()
        
        return user

class WithdrawSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0
    )
    wallet_address = serializers.CharField(max_length=100)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à 0")
        return value

class UserDetailSerializer(serializers.ModelSerializer):
    wallet = serializers.SerializerMethodField()
    investments = serializers.SerializerMethodField()
    total_invested = serializers.SerializerMethodField()
    total_earnings = serializers.SerializerMethodField()
    total_withdrawn = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 
                 'date_joined', 'wallet', 'investments', 'total_invested',
                 'total_earnings', 'total_withdrawn')

    def get_wallet(self, obj):
        wallet, created = USDTWallet.objects.get_or_create(user=obj)
        return {
            'address': wallet.address,
            'balance': wallet.balance
        }

    def get_investments(self, obj):
        investments = Investment.objects.filter(user=obj)
        return [{
            'id': inv.id,
            'plan': inv.plan.name,
            'amount_invested': inv.amount_invested,
            'start_date': inv.start_date,
            'status': inv.status,
            'daily_return': inv.plan.daily_return,
            'current_earnings': inv.calculate_earnings(),
            'available_earnings': inv.get_available_earnings(),
            'total_withdrawn': inv.total_withdrawn
        } for inv in investments]

    def get_total_invested(self, obj):
        return Investment.objects.filter(user=obj).aggregate(
            total=Sum('amount_invested'))['total'] or Decimal('0')

    def get_total_earnings(self, obj):
        active_investments = Investment.objects.filter(user=obj, status='ACTIVE')
        return sum(inv.calculate_earnings() for inv in active_investments)

    def get_total_withdrawn(self, obj):
        return Investment.objects.filter(user=obj).aggregate(
            total=Sum('total_withdrawn'))['total'] or Decimal('0')

class ReferralUserSerializer(serializers.ModelSerializer):
    total_deposits = serializers.SerializerMethodField()
    commission_earned = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'date_joined', 'total_deposits', 'commission_earned')

    def get_total_deposits(self, obj):
        return USDTTransaction.objects.filter(
            wallet__user=obj,
            transaction_type='DEPOSIT'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    def get_commission_earned(self, obj):
        return USDTTransaction.objects.filter(
            wallet__user=obj.profile.referred_by.user,
            transaction_type='REFERRAL_BONUS',
            description__contains=obj.email
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

class ReferralProfileSerializer(serializers.ModelSerializer):
    referrals = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ('referral_code', 'total_referral_earnings', 'referrals')

    def get_referrals(self, obj):
        referred_users = User.objects.filter(profile__referred_by=obj)
        return ReferralUserSerializer(referred_users, many=True).data

class InvestmentUpgradeSerializer(serializers.Serializer):
    new_plan = serializers.PrimaryKeyRelatedField(queryset=InvestmentPlan.objects.all())
    additional_amount = serializers.DecimalField(max_digits=20, decimal_places=6, required=False, default=0)

    def validate(self, data):
        request = self.context.get('request')
        current_investment = self.context.get('investment')
        new_plan = data['new_plan']
        additional_amount = data.get('additional_amount', 0)

        # Vérifier si le nouveau plan est d'un niveau supérieur
        if new_plan.level <= current_investment.plan.level:
            raise serializers.ValidationError(
                "Le nouveau plan doit être d'un niveau supérieur"
            )

        # Calculer le montant total après l'upgrade
        total_amount = current_investment.current_value + Decimal(str(additional_amount))

        # Vérifier si le montant total respecte le minimum requis pour le nouveau plan
        if total_amount < new_plan.minimum_investment:
            raise serializers.ValidationError(
                f"Le montant total après upgrade ({total_amount} USDT) doit être supérieur "
                f"au minimum requis pour ce plan ({new_plan.minimum_investment} USDT)"
            )

        # Si un montant supplémentaire est fourni, vérifier le solde du wallet
        if additional_amount > 0:
            wallet = request.user.usdt_wallet
            if wallet.balance < additional_amount:
                raise serializers.ValidationError(
                    "Solde USDT insuffisant pour le montant supplémentaire"
                )

        return data
