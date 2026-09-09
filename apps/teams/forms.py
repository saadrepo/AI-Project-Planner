from django import forms

from .models import Team


class TeamCreateForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "app-field"}),
            "description": forms.Textarea(attrs={"class": "app-field", "rows": 3}),
        }

    def clean_name(self):
        return (self.cleaned_data.get("name") or "").strip()
