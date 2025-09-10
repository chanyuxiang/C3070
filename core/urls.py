from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    IdentityViewSet,
    login_page,
    home_page,
    add_identity_page,
    view_identity_page,
    register_user,
    register_page,
    user_info,
    my_profile, public_profile, search_users,
    # add these page views:
    me_profile_page, public_profile_page,
    public_identity_lookup,
    public_identity_lookup_page,
    export_identities,
    import_identities,
)

router = DefaultRouter()
router.register(r'identities', IdentityViewSet, basename='identity')

urlpatterns = [

    path('identities/export/', export_identities, name='identities_export'),
    path('identities/import/', import_identities, name='identities_import'),

    path('', include(router.urls)),

    # auth (JWT) to match main.js POST /api/token/
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # HTML page views
    path('login/', login_page, name='login'),
    path('register-page/', register_page, name='register_page'),
    path('register/', register_user, name='register_user'),
    path('home/', home_page, name='home'),
    path('add-identity/', add_identity_page, name='add_identity'),
    path('view-identity/', view_identity_page, name='view_identity'),

    # JSON APIs
    path('user-info/', user_info, name='user_info'),
    path('me/profile/', my_profile, name='my_profile'),
    path('profile/<str:username>/', public_profile, name='public_profile'),
    path('users/search/', search_users, name='search_users'),

    # PAGE routes for profiles
    path('my-profile-page/', me_profile_page, name='my_profile_page'),
    path('profile-page/<str:username>/', public_profile_page, name='public_profile_page'),
    path('public/lookup/<str:username>/', public_identity_lookup, name='public_identity_lookup'),
    path('public/lookup-page/<str:username>/', public_identity_lookup_page, name='public_identity_lookup_page'),

    
]
