from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(label="Nom", max_length=100)
    email = forms.EmailField(label="Email")
    subject = forms.CharField(label="Sujet", max_length=150)
    message = forms.CharField(
        label="Message", max_length=4000, widget=forms.Textarea(attrs={"rows": 6})
    )
    website = forms.CharField(
        required=False,
        label="Ne pas remplir",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )

    def is_spam(self) -> bool:
        return bool(self.cleaned_data.get("website"))
