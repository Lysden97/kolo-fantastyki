from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField(max_length=254)
    phone = forms.RegexField(r"^[0-9+() -]{0,30}$", required=False, max_length=30)
    subject = forms.CharField(max_length=5000, widget=forms.Textarea)

    def clean_name(self):
        name = self.cleaned_data["name"]
        if "\n" in name or "\r" in name:
            raise forms.ValidationError("Imię nie może zawierać znaków nowej linii.")
        return name
