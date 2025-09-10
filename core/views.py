import json
from django.shortcuts import get_object_or_404,render
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from rest_framework.response import Response
from rest_framework import status

from .models import Identity
from .serializers import IdentitySerializer,ProfileSerializer

# ---------------------------
# API: Identity ViewSet
# ---------------------------

class IdentityViewSet(viewsets.ModelViewSet):
    queryset = Identity.objects.all()
    serializer_class = IdentitySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Identity.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return Identity.objects.none()

        try:
            role = user.profile.role
        except AttributeError:
            role = 'user'  # fallback

        return Identity.objects.all() if role == 'admin' else Identity.objects.filter(user=user)

# ---------------------------
# API: Auth & Profile
# ---------------------------

@csrf_exempt
def register_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)

        User.objects.create_user(username=username, email=email, password=password)
        return JsonResponse({'message': 'User registered successfully'}, status=201)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    user = request.user
    profile = getattr(user, 'profile', None)

    return JsonResponse({
        'username': user.username,
        'role': profile.role if profile else 'unknown'
    })

# ---------------------------
# API: Individual Profile Page
# ---------------------------

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser,JSONParser])
def my_profile(request):
    prof = request.user.profile
    if request.method in ['PUT','PATCH']:
        serializer = ProfileSerializer(prof, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=200)
        return JsonResponse(serializer.errors, status=400)
    serializer = ProfileSerializer(prof, context={'request': request})
    return JsonResponse(serializer.data, status=200)

@api_view(['GET'])
@permission_classes([AllowAny])
def public_profile(request, username):
    user = get_object_or_404(User, username=username)
    serializer = ProfileSerializer(user.profile, context={'request': request})
    return JsonResponse(serializer.data, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    q = (request.GET.get('q') or '').strip().lower()
    qs = User.objects.select_related('profile').all()
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(profile__display_label__icontains=q))

    data = [{
        'username': u.username,
        'display_label': getattr(u.profile, 'display_label', '') or ''
    } for u in qs[:20]]
    return JsonResponse({'results': data}, status=200)

def _parse_accept_language(header_value: str):
    if not header_value:
        return []
    langs = []
    for part in header_value.split(","):
        item = part.strip()
        if not item:
            continue
        if ";q=" in item:
            lang, q = item.split(";q=", 1)
            try:
                qv = float(q)
            except ValueError:
                qv = 1.0
        else:
            lang, qv = item, 1.0
        langs.append((lang.strip().lower(), qv))
    langs.sort(key=lambda x: x[1], reverse=True)
    return langs

def _primary(lang: str):
    return (lang or "").split("-", 1)[0].lower()

def _score_identity(identity, want_ctx: str, accept_langs):
    score = 0.0
    if want_ctx and identity.context and identity.context.lower() == want_ctx.lower():
        score += 100
    if accept_langs:
        id_lang = (identity.language or "").lower()
        id_primary = _primary(id_lang)
        for idx, (al, q) in enumerate(accept_langs):
            weight = max(q, 0.1)
            if id_lang and id_lang == al:
                score += 20 * weight / (1 + idx*0.1)
                break
            if id_primary and id_primary == _primary(al):
                score += 8 * weight / (1 + idx*0.1)
    try:
        score += (identity.updated_at.timestamp() % 1)
    except Exception:
        pass
    return score

@api_view(['GET'])
@permission_classes([AllowAny])
def public_identity_lookup(request, username):

    user = get_object_or_404(User.objects.only('id', 'username'), username=username)
    identities = Identity.objects.filter(user=user).order_by('-updated_at', '-created_at')

    if not identities.exists():
        return Response({'username': username, 'identity': None, 'results': [], 'note': 'No identities found'},
                        status=status.HTTP_200_OK)

    mode = (request.GET.get('mode') or 'best').lower().strip()
    want_ctx = (request.headers.get('X-Use-Context') or request.GET.get('context') or '').strip()

    # Optional demo override for language preference
    al_override = (request.GET.get('al') or request.headers.get('X-Accept-Language') or '').strip()
    accept_lang_header = al_override or (request.headers.get('Accept-Language') or '')
    accept_langs = _parse_accept_language(accept_lang_header)

    def lang_matches(id_lang: str) -> bool:
        """True if id_lang equals any accepted tag or shares the same primary subtag."""
        if not accept_langs:
            return True  # no language preference -> accept all
        id_lang = (id_lang or '').lower()
        id_primary = _primary(id_lang)
        for al, _q in accept_langs:
            if id_lang == al:
                return True
            if id_primary and id_primary == _primary(al):
                return True
        return False

    # Filter by context first (for both modes, if provided)
    if want_ctx:
        identities = [i for i in identities if (i.context or '').lower() == want_ctx.lower()]
    else:
        identities = list(identities)

    if mode == 'list':
        # filter by language (exact or primary) if Accept-Language present
        lang_filtered = [i for i in identities if lang_matches(i.language)]
        results = lang_filtered if lang_filtered else identities  # fallback: context-only

        # order by score (so "best" is first), but return ALL
        scored = sorted(
            results,
            key=lambda i: _score_identity(i, want_ctx, accept_langs),
            reverse=True
        )
        payload = [{
            'id': i.id,
            'display_name': i.display_name,
            'context': i.context,
            'language': i.language,
            'created_at': i.created_at,
            'updated_at': i.updated_at,
        } for i in scored]

        return Response({
            'username': user.username,
            'used_context': want_ctx or None,
            'accept_language': [al for al, _ in accept_langs] or None,
            'results': payload,
        }, status=status.HTTP_200_OK)

    # mode=best (default) – keep old behavior
    best, best_score = None, float('-inf')
    for ident in identities if identities else Identity.objects.filter(user=user):
        s = _score_identity(ident, want_ctx, accept_langs)
        if s > best_score:
            best, best_score = ident, s

    data = {
        'username': user.username,
        'used_context': want_ctx or None,
        'accept_language': [al for al, _ in accept_langs] or None,
        'identity': None if not best else {
            'id': best.id,
            'display_name': best.display_name,
            'context': best.context,
            'language': best.language,
            'created_at': best.created_at,
            'updated_at': best.updated_at,
        },
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_identities(request):
    """
    Download the current user's identities as JSON.
    """
    qs = Identity.objects.filter(user=request.user).order_by('id')
    # Full records (handy for backup)
    data = IdentitySerializer(qs, many=True, context={'request': request}).data
    payload = {"items": data}

    resp = JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})
    resp["Content-Disposition"] = 'attachment; filename="identities-export.json"'
    return resp


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_identities(request):

    # ---- parse body or uploaded file ----
    try:
        if "file" in request.FILES:
            raw = request.FILES["file"].read().decode("utf-8", errors="ignore")
            body = json.loads(raw or "{}")
        else:
            if isinstance(request.data, (dict, list)):
                body = request.data
            else:
                body = json.loads(request.body or "{}")
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    # ---- normalise to a list of items ----
    items = None
    if isinstance(body, list):
        items = body
    elif isinstance(body, dict):
        if isinstance(body.get("items"), list):
            items = body["items"]
        elif isinstance(body.get("results"), list):
            items = body["results"]

    if not isinstance(items, list):
        return HttpResponseBadRequest(
            'Expected an array or {"items": [...]}.'
        )

    created = 0
    errors = []

    # ---- import loop ----
    for idx, rec in enumerate(items, start=1):
        if not isinstance(rec, dict):
            errors.append(f"Item {idx}: not an object")
            continue

        dn = (rec.get("display_name") or rec.get("name") or rec.get("displayName") or "").strip()
        ctx = (rec.get("context") or rec.get("use_context") or "").strip()
        lng = (rec.get("language") or rec.get("lang") or "").strip()

        if not dn:
            errors.append(f"Item {idx}: 'display_name' / 'name' is required")
            continue

        Identity.objects.create(
            user=request.user,
            display_name=dn,
            context=ctx,
            language=lng,
        )
        created += 1

    # 201 = all good, 207 = partial, 400 = none
    status_code = 201 if created and not errors else (207 if created and errors else 400)
    return JsonResponse(
        {
            "created_count": created,
            "errors": errors,
            "total_received": len(items),
        },
        status=status_code
    )

# ---------------------------
# HTML Page Views
# ---------------------------

def login_page(request):
    return render(request, 'core/login.html')

def register_page(request):
    return render(request, 'core/register.html')

def home_page(request):
    return render(request, 'core/home.html')

def add_identity_page(request):
    return render(request, 'core/add_identity.html')

def view_identity_page(request):
    return render(request, 'core/view_identity.html')

def profile_page(request):
    # owner-editable page
    return render(request, 'core/profile.html')

def public_profile_page(request, username):
    return render(request, 'core/public_profile.html')

def me_profile_page(request):

    return render(request, 'core/profile.html')

def public_identity_lookup_page(request, username):
    return render(request, 'core/public_lookup.html', {'username': username})
