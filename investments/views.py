from rest_framework import viewsets, status, serializers, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import InvestmentPlan, Investment, USDTWallet, USDTTransaction, UserProfile
from .serializers import (
    InvestmentPlanSerializer, 
    InvestmentSerializer,
    USDTWalletSerializer,
    USDTTransactionSerializer,
    WithdrawSerializer,  # Ajouter l'import du serializer de retrait
    LoginSerializer,  # Importer le serializer de connexion
    RegisterSerializer,  # Importer le serializer d'enregistrement
    UserDetailSerializer,  # Importer le serializer des détails de l'utilisateur
    InvestmentUpgradeSerializer,  # Importer le serializer de mise à niveau d'investissement
    ReferralProfileSerializer  # Importer le serializer de profil de parrainage
)
from .blockchain import BlockchainClient
from decimal import Decimal
from django.db import transaction  # Importer transaction pour les opérations atomiques
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone

# Create your views here.

class InvestmentPlanViewSet(viewsets.ModelViewSet):
    queryset = InvestmentPlan.objects.all()
    serializer_class = InvestmentPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

class USDTWalletViewSet(viewsets.ModelViewSet):
    serializer_class = USDTWalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return USDTWallet.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Vérifier si l'utilisateur a déjà un portefeuille
        if USDTWallet.objects.filter(user=self.request.user).exists():
            raise serializers.ValidationError("Vous avez déjà un portefeuille USDT")
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def check_balance(self, request, pk=None):
        wallet = self.get_object()
        try:
            blockchain_client = BlockchainClient()
            blockchain_balance = blockchain_client.get_usdt_balance(wallet.address)
            return Response({
                'blockchain_balance': str(blockchain_balance),
                'local_balance': str(wallet.balance)
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class USDTTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = USDTTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return USDTTransaction.objects.filter(wallet__user=self.request.user)

    @action(detail=False, methods=['post'])
    def deposit(self, request):
        wallet = get_object_or_404(USDTWallet, user=request.user)
        tx_hash = request.data.get('tx_hash')

        if not tx_hash:
            return Response(
                {'error': 'Transaction hash is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Vérifier la transaction sur la blockchain
            blockchain_client = BlockchainClient()
            tx_info = blockchain_client.verify_transaction(tx_hash)

            if not tx_info['valid']:
                return Response(
                    {'error': tx_info['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Vérifier que la transaction est destinée à notre adresse
            if tx_info['to_address'].lower() != settings.COMPANY_USDT_ADDRESS.lower():
                return Response(
                    {'error': 'Invalid destination address'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            amount = Decimal(str(tx_info['amount']))

            # Créer la transaction
            with transaction.atomic():
                # Créer la transaction de dépôt
                usdt_transaction = USDTTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='DEPOSIT',
                    amount=amount,
                    status='COMPLETED',
                    tx_hash=tx_hash
                )

                # Mettre à jour le solde du portefeuille
                wallet.balance += amount
                wallet.save()

                # Gérer la commission de parrainage si l'utilisateur a été parrainé
                try:
                    profile = request.user.profile
                    if profile.referred_by:
                        # Calculer la commission (5% du dépôt)
                        referral_bonus = amount * Decimal('0.05')
                        
                        # Créer une transaction pour la commission
                        referrer_wallet = profile.referred_by.user.usdt_wallet
                        USDTTransaction.objects.create(
                            wallet=referrer_wallet,
                            transaction_type='REFERRAL_BONUS',
                            amount=referral_bonus,
                            status='COMPLETED',
                            description=f"Commission de parrainage pour le dépôt de {request.user.email}"
                        )
                        
                        # Mettre à jour le solde du parrain
                        referrer_wallet.balance += referral_bonus
                        referrer_wallet.save()
                        
                        # Mettre à jour les gains totaux de parrainage
                        profile.referred_by.total_referral_earnings += referral_bonus
                        profile.referred_by.save()
                except UserProfile.DoesNotExist:
                    pass

            return Response(USDTTransactionSerializer(usdt_transaction).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class InvestmentViewSet(viewsets.ModelViewSet):
    serializer_class = InvestmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        plan = serializer.validated_data['plan']
        amount = serializer.validated_data['amount_invested']
        
        # Vérifier si l'utilisateur a déjà un investissement actif
        active_investment = Investment.objects.filter(
            user=self.request.user,
            status='ACTIVE'
        ).first()

        if active_investment:
            raise serializers.ValidationError(
                "Vous avez déjà un investissement actif. Utilisez la mise à niveau pour changer de plan."
            )

        # Vérifier les limites du plan
        if amount < plan.minimum_investment:
            raise serializers.ValidationError(
                f"Le montant minimum pour ce plan est de {plan.minimum_investment} USDT"
            )
        if plan.maximum_investment and amount > plan.maximum_investment:
            raise serializers.ValidationError(
                f"Le montant maximum pour ce plan est de {plan.maximum_investment} USDT"
            )

        wallet = get_object_or_404(USDTWallet, user=self.request.user)
        
        if wallet.balance < amount:
            raise serializers.ValidationError("Solde USDT insuffisant")

        with transaction.atomic():
            # Créer la transaction USDT
            usdt_transaction = USDTTransaction.objects.create(
                wallet=wallet,
                transaction_type='INVESTMENT',
                amount=amount,
                status='COMPLETED',
                description=f"Investissement dans le plan {plan.name}"
            )

            # Mettre à jour le solde du portefeuille
            wallet.balance -= amount
            wallet.save()

            # Sauvegarder l'investissement
            serializer.save(
                user=self.request.user,
                status='ACTIVE',
                usdt_transaction=usdt_transaction,
                current_value=amount,
                start_date=timezone.now()
            )

    @action(detail=True, methods=['post'])
    def upgrade(self, request, pk=None):
        """
        Mettre à niveau un investissement vers un plan supérieur
        """
        current_investment = self.get_object()
        
        # Valider la demande d'upgrade
        serializer = InvestmentUpgradeSerializer(
            data=request.data,
            context={'request': request, 'investment': current_investment}
        )
        serializer.is_valid(raise_exception=True)
        
        new_plan = serializer.validated_data['new_plan']
        additional_amount = serializer.validated_data.get('additional_amount', 0)
        
        wallet = self.request.user.usdt_wallet
        
        with transaction.atomic():
            # Si un montant supplémentaire est fourni
            if additional_amount > 0:
                # Créer la transaction pour le montant supplémentaire
                USDTTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='INVESTMENT_UPGRADE',
                    amount=additional_amount,
                    status='COMPLETED',
                    description=f"Montant supplémentaire pour upgrade vers {new_plan.name}"
                )
                
                # Mettre à jour le solde du portefeuille
                wallet.balance -= additional_amount
                wallet.save()
            
            # Calculer les gains actuels
            current_earnings = current_investment.calculate_earnings()
            
            # Mettre à jour l'investissement
            current_investment.plan = new_plan
            current_investment.amount_invested += additional_amount
            current_investment.current_value = current_investment.amount_invested + current_earnings
            current_investment.start_date = timezone.now()  # Réinitialiser la date de début
            current_investment.save()
            
            return Response({
                'status': 'success',
                'message': f'Investissement mis à niveau vers {new_plan.name}',
                'investment': InvestmentSerializer(current_investment).data
            })

    @action(detail=True, methods=['get'])
    def calculate_earnings(self, request, pk=None):
        investment = self.get_object()
        earnings = investment.calculate_earnings()
        return Response({
            'earnings': str(earnings),
            'current_value': str(investment.current_value),
            'last_update': investment.last_earnings_update
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        investment = self.get_object()
        if investment.status != 'ACTIVE':
            return Response(
                {'error': 'Only active investments can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        investment.status = 'CANCELLED'
        investment.save()
        return Response({'status': 'Investment cancelled'})

    @action(detail=False, methods=['post'], url_path='withdraw')
    def withdraw(self, request):
        """
        Retrait des bénéfices d'un investissement actif
        """
        serializer = WithdrawSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Récupérer l'investissement actif de l'utilisateur
        try:
            investment = Investment.objects.get(
                user=request.user,
                status='ACTIVE'
            )
        except Investment.DoesNotExist:
            return Response(
                {'error': 'Aucun investissement actif trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

        amount = serializer.validated_data['amount']
        wallet_address = serializer.validated_data['wallet_address']

        # Vérifier si le retrait est possible
        can_withdraw, message = investment.can_withdraw(amount)
        if not can_withdraw:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )

        blockchain_client = BlockchainClient()

        # Transaction atomique pour le retrait
        with transaction.atomic():
            try:
                # Effectuer le transfert USDT
                tx_hash = blockchain_client.send_usdt(
                    wallet_address,
                    amount
                )

                # Créer la transaction USDT
                withdrawal = USDTTransaction.objects.create(
                    wallet=investment.user.usdtwallet,
                    transaction_type='WITHDRAWAL',
                    amount=amount,
                    tx_hash=tx_hash,
                    status='COMPLETED'
                )

                # Mettre à jour le montant total retiré
                investment.total_withdrawn += amount
                investment.save()

                return Response({
                    'message': f'Retrait de {amount} USDT effectué avec succès',
                    'transaction_hash': tx_hash,
                    'status': 'COMPLETED'
                })

            except Exception as e:
                return Response(
                    {'error': f'Erreur lors du retrait: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

class UserProfileViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReferralProfileSerializer

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def referrals(self, request):
        """
        Obtenir les informations de parrainage de l'utilisateur connecté
        """
        try:
            profile = request.user.profile
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profil utilisateur non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def referral_code(self, request):
        """
        Obtenir uniquement le code de parrainage de l'utilisateur
        """
        try:
            profile = request.user.profile
            return Response({
                'referral_code': profile.referral_code
            })
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profil utilisateur non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')
    
    if email is None or password is None:
        return Response({
            'error': 'Veuillez fournir email et mot de passe'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=email, password=password)
    
    if user is not None:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })
    else:
        return Response({
            'error': 'Email ou mot de passe incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Inscription réussie',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail_view(request):
    """
    Retourne toutes les informations détaillées de l'utilisateur connecté
    """
    serializer = UserDetailSerializer(request.user)
    return Response(serializer.data)
