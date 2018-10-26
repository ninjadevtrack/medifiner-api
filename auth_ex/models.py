from django.db import models
from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.core.mail import send_mail

from medications.models import State, Organization


class UserManager(BaseUserManager):
    """Manager for User."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a normal User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Abstract User with unique email and no username."""
    NATIONAL_LEVEL = 'nl'
    STATE_LEVEL = 'sl'
    LEVEL_CHOICES = (
        (NATIONAL_LEVEL, _('National level permission')),
        (STATE_LEVEL, _('State level permission')),
    )
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _("A user with that email already exists."),
        },
    )
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this'
                    ' admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    organization = models.ForeignKey(
        Organization,
        related_name='users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    role = models.CharField(
        _('role in organization'),
        max_length=250,
        blank=True,
        help_text=_('Role this user has in the related organization.'),
    )

    permission_level = models.CharField(
        _('permission level'),
        max_length=2,
        choices=LEVEL_CHOICES,
        default=STATE_LEVEL,
    )
    invitation_mail_sent = models.BooleanField(
        _('invitation mail sent'),
        default=False,
        help_text=_(
            'Designates whether the invitation mail for this user '
            ' has been sent'),
    )
    used_invitation_code = models.CharField(
        _('used invitation code'),
        max_length=32,
        blank=True,
    )

    state = models.ForeignKey(
        State,
        related_name='users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this User."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        return super().save(*args, **kwargs)
