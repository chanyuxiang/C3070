from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class Identity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='identities')
    display_name = models.CharField(max_length=100)
    context = models.CharField(max_length=40) 
    language = models.CharField(max_length=20, default='en')  
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)      

    def __str__(self):
        return f"{self.display_name} ({self.context}, {self.language})"


class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')

    display_label = models.CharField(max_length=100, blank=True)   # e.g. “Jon Tan”
    bio = models.TextField(blank=True)                              # short description
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    gender_identity = models.CharField(max_length=50, blank=True)  
    pronouns = models.CharField(max_length=50, blank=True) 

    website = models.URLField(blank=True)
    github = models.CharField(max_length=100, blank=True)
    twitter = models.CharField(max_length=100, blank=True)
    linkedin = models.URLField(blank=True)

    preferred_identity = models.ForeignKey(
        'Identity', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='preferred_by'
    )


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = 'admin' if instance.is_superuser else 'user'
        Profile.objects.create(user=instance, role=role)
    else:
        instance.profile.save()

