from django import forms

from .models import Firmware


class FirmwarePushForm(forms.Form):
    """Allow admins to pick which firmware build to push in bulk."""

    firmware = forms.ModelChoiceField(
        queryset=Firmware.objects.none(),
        label='Firmware build',
        help_text='Only active firmware files are available for rollout.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['firmware'].queryset = Firmware.objects.filter(is_active=True).order_by('-uploaded_at')
