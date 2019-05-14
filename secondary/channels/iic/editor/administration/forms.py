from django import forms
from primary.core.administration.models import Role


# Create the form class.

class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ['name', 'access_level', 'session_expiry']
