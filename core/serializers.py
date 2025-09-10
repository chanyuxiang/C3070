
import re
from rest_framework import serializers
from .models import Identity, Profile

class IdentitySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    role = serializers.CharField(source='user.profile.role', read_only=True)

    class Meta:
        model = Identity
        fields = ['id','display_name','context','language','username','role','created_at','updated_at']
        read_only_fields = ['username','role','created_at','updated_at']

class ProfileSerializer(serializers.ModelSerializer):
    username   = serializers.SerializerMethodField(read_only=True)
    avatar_url = serializers.SerializerMethodField(read_only=True)

    preferred_identity = serializers.PrimaryKeyRelatedField(
        queryset=Identity.objects.all(), required=False, allow_null=True
    )
    preferred_identity_name = serializers.SerializerMethodField(read_only=True)

    preferred_identity_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            'username','display_label','bio','avatar','avatar_url','role',
            'gender_identity','pronouns',
            'website','github','twitter','linkedin','preferred_identity','preferred_identity_name','preferred_identity_data',
        ]
        read_only_fields = ['username','avatar_url','role']

    def to_internal_value(self, data):
        data = data.copy()
        for key in ('website', 'linkedin'):
            v = data.get(key)
            if isinstance(v, str):
                v = v.strip()
                if v and not re.match(r'^https?://', v, flags=re.I):
                    v = 'https://' + v
                data[key] = v
        return super().to_internal_value(data)

    def get_username(self, obj): 
        return obj.user.username

    def get_avatar_url(self, obj):
        req = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            return req.build_absolute_uri(obj.avatar.url) if req else obj.avatar.url
        return None
    
    def get_preferred_identity_name(self, obj):
        pi = getattr(obj, 'preferred_identity', None)
        return getattr(pi, 'display_name', None) if pi else None

    def validate_preferred_identity(self, value):
        if value is None:
            return value
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Not allowed.")
        if value.user_id != request.user.id:
            raise serializers.ValidationError("You can only select your own identity.")
        return value
    
    def get_preferred_identity_data(self, obj):
        pi = getattr(obj, 'preferred_identity', None)
        if not pi:
            return None
        return {
            "id": pi.id,
            "display_name": pi.display_name,
            "context": pi.context,
            "language": pi.language,
            "updated_at": pi.updated_at,
            "created_at": pi.created_at,
        }
