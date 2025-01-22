from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InvestmentPlanViewSet,
    InvestmentViewSet,
    USDTWalletViewSet,
    USDTTransactionViewSet,
    UserProfileViewSet,
    login_view,
    register_view,
    user_detail_view
)

router = DefaultRouter()
router.register(r'plans', InvestmentPlanViewSet)
router.register(r'my-investments', InvestmentViewSet, basename='investment')
router.register(r'transactions', USDTTransactionViewSet, basename='transaction')
router.register(r'profile', UserProfileViewSet, basename='profile')

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('me/', user_detail_view, name='user-detail'),
    path('', include(router.urls)),
]
