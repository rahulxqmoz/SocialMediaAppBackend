from django.db import models
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager,PermissionsMixin

# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, username, password, **extra_fields)

class User(AbstractBaseUser,PermissionsMixin):
    username=models.CharField(max_length=100,unique=True)
    first_name=models.CharField(max_length=100)
    email=models.EmailField(unique=True)
    bio=models.TextField(blank=True,null=True)
    dob=models.DateField(blank=True,null=True)
    mobile = models.CharField(max_length=15, unique=True, null=True, blank=True)
    profile_pic=models.ImageField(upload_to='profile_pics',null=True,blank=True)
    cover_pic=models.ImageField(upload_to='cover_pics',null=True,blank=True)
    is_active=models.BooleanField(default=False)
    is_staff=models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_suspended = models.BooleanField(default=False, help_text="Designates whether this user is suspended or not.")
    is_googleauth= models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)

    objects=UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name']

    def __str__(self):
        return self.email