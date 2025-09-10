import json
from django.shortcuts import get_object_or_404,render
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.db.models.functions import Lower

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

# def _parse_accept_language(header_value: str):
#     if not header_value:
#         return []
#     langs = []
#     for part in header_value.split(","):
#         item = part.strip()
#         if not item:
#             continue
#         if ";q=" in item:
#             lang, q = item.split(";q=", 1)
#             try:
#                 qv = float(q)
#             except ValueError:
#                 qv = 1.0
#         else:
#             lang, qv = item, 1.0
#         langs.append((lang.strip().lower(), qv))
#     langs.sort(key=lambda x: x[1], reverse=True)
#     return langs

# def _primary(lang: str):
#     return (lang or "").split("-", 1)[0].lower()

# def _score_identity(identity, want_ctx: str, accept_langs):
#     score = 0.0
#     if want_ctx and identity.context and identity.context.lower() == want_ctx.lower():
#         score += 100
#     if accept_langs:
#         id_lang = (identity.language or "").lower()
#         id_primary = _primary(id_lang)
#         for idx, (al, q) in enumerate(accept_langs):
#             weight = max(q, 0.1)
#             if id_lang and id_lang == al:
#                 score += 20 * weight / (1 + idx*0.1)
#                 break
#             if id_primary and id_primary == _primary(al):
#                 score += 8 * weight / (1 + idx*0.1)
#     try:
#         score += (identity.updated_at.timestamp() % 1)
#     except Exception:
#         pass
#     return score

@api_view(['GET'])
@permission_classes([AllowAny])
def public_identity_lookup(request, username):
    user = get_object_or_404(User, username=username)
    qs = Identity.objects.filter(user=user)

    # --- Context: fuzzy, case-insensitive ---
    ctx = (request.GET.get('context') or '').strip()
    if ctx:
        qs = qs.filter(context__icontains=ctx)

    # --- Language: strict gate (Option B) with normalisation & aliases ---
    raw_lang = (
        (request.GET.get('accept_language') or '').strip()
        or (request.GET.get('al') or '').strip()
    )

    def norm_lang(s: str) -> str:
        """
        Normalise to primary BCP-47 code when possible.
        Accepts words like 'english', 'chinese' and tags like 'en-GB', 'zh-CN'.
        Returns primary code ('en','zh',...) or '' if unknown.
        """
        if not s:
            return ''
        s = s.strip().lower()

        # Common word aliases
        word_alias = {
            'english': 'en',
            'chinese': 'zh',
            'mandarin': 'zh',
            'malay': 'ms',
            'tamil': 'ta',
        }
        if s in word_alias:
            return word_alias[s]

        # If looks like a tag, reduce to primary (en, zh, ms, ta...)
        if '-' in s:
            s = s.split('-', 1)[0]

        # if they typed 'en' / 'zh' already, keep it
        if len(s) in (2, 3):  # crude but fine for our set
            return s
        return ''

    # Parse a comma-separated list (or Accept-Language-esque)
    requested_langs = [p.split(';', 1)[0].strip() for p in raw_lang.split(',') if p.strip()]
    requested_primary = [norm_lang(p) for p in requested_langs]
    requested_primary = [p for p in requested_primary if p]  # drop unknowns

    items = list(qs)

    if requested_primary:
        def lang_matches(code: str) -> bool:
            """
            Strict gate: record must match one of the requested primaries.
            We normalise the record language too (so 'Chinese'/'zh-CN'/'zh' all → 'zh').
            """
            c = norm_lang(code or '')
            return bool(c) and (c in requested_primary)

        items = [i for i in items if lang_matches(i.language)]

    # Sort: newest first (stable)
    def ts(x):
        return (x.updated_at or x.created_at)
    items.sort(key=ts, reverse=True)

    # Mode handling (always return results array)
    mode = (request.GET.get('mode') or 'best').strip().lower()
    if mode == 'best':
        items = items[:1]  # single best
        mode_out = 'best'
    else:
        mode_out = 'list'

    data = IdentitySerializer(items, many=True, context={'request': request}).data
    return JsonResponse({
        "username": user.username,
        "applied_context": ctx or None,
        "accept_language": requested_langs,   # original tokens user typed
        "mode": mode_out,
        "count": len(data),
        "results": data,
    }, status=200)


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
