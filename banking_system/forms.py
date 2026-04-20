from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter username",
            "required": True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter password",
            "required": True,
            "id": "id_password"
        })
    )

# ======================================CUSTOMER FORMS=======================================
from django import forms

class CustomerForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'})
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'})
    )
    gender = forms.ChoiceField(
        choices=[("M", "Male"), ("F", "Female")],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control datepicker', 'placeholder': 'Select date of birth'})
    )
    id_type = forms.ChoiceField(
        choices=[
            ('National ID', 'National ID'),
            ('Voter ID', 'Voter ID'),
            ('Passport', 'Passport')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    id_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter ID number'})
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'})
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'})
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter address'})
    )

    role_id = forms.CharField(
        initial="Customer User",  # display role name instead of numeric ID
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

    status = forms.ChoiceField(
        choices=[
            ('ACTIVE', 'Active'),
            ('INACTIVE', 'Inactive')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # -------------------------
    # VALIDATION METHODS
    # -------------------------
    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        if len(phone) < 10:
            raise forms.ValidationError("Phone number must be at least 10 digits.")
        return phone

    def clean_id_number(self):
        id_number = self.cleaned_data.get("id_number")
        if len(id_number) < 6:
            raise forms.ValidationError("ID Number must be at least 6 characters long.")
        return id_number

# ======================================USERS FORMS=====================================
#from django.contrib.auth.forms import ReadOnlyPasswordHashField, AdminPasswordChangeForm
# banking_system/forms.py (append or update the existing CbacUser forms)
from django import forms
from django.db import connection
from .models import CbacUser

class CbacUserCreationForm(forms.ModelForm):
    # single password field
    password = forms.CharField(label="Password", widget=forms.PasswordInput, required=True, help_text="Enter a strong password (min 8 chars).")
    phone_number = forms.CharField(required=False, help_text="Phone number used by the package to link to employee/customer")

class Meta:
    model = CbacUser
    fields = ("username", "email", "user_type", "status", "password", "phone_number")

    def clean_password(self):
        pw = self.cleaned_data.get("password")
        if not pw or len(pw) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        # Optionally call DB package is_password_strong (if you want DB-side validation).
        # We'll keep validation here to avoid calling DB unnecessarily.
        return pw

    def save(self, commit=True):
        # Don’t hash here; let Oracle package do it
        user = super().save(commit=False)
        if commit:
            user.save()
        return user


class CbacUserChangeForm(forms.ModelForm):
    # optional password change via admin UI
    password = forms.CharField(label="New password (leave blank to keep current)", widget=forms.PasswordInput, required=False)

    class Meta:
        model = CbacUser
        fields = ("username", "email", "password", "user_type", "reference_id", "status", "is_active", "is_superuser", "is_staff")

    def save(self, commit=True):
        user = super().save(commit=False)
        # do not call set_password here; admin.save_model will either call DB proc or handle hashing
        return user

# ======================================TRANSACTIONS FORMS=======================================

class DepositForm(forms.Form):
    account_number = forms.CharField(
        label="Account Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter account number'})
    )
    amount = forms.DecimalField(
        label="Amount",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount'})
    )
    description = forms.CharField(
        label="Description",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class WithdrawForm(forms.Form):
    account_number = forms.CharField(
        label="Account Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter account number'})
    )
    amount = forms.DecimalField(
        label="Amount",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount'})
    )
    description = forms.CharField(
        label="Description",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class TransferForm(forms.Form):
    sender_account_number = forms.CharField(
        label="Sender Account Number",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    receiver_account_number = forms.CharField(
        label="Receiver Account Number",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    amount = forms.DecimalField(
        label="Amount",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    description = forms.CharField(
        label="Description",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class ReverseTransactionForm(forms.Form):
    transaction_id = forms.IntegerField(
        label="Transaction ID",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    description = forms.CharField(
        label="Reason for Reversal",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class TransactionHistoryForm(forms.Form):
    account_number = forms.CharField(
        label="Account Number",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    transaction_type = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('Credit', 'Credit'),
            ('Debit', 'Debit')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('PENDING', 'Pending'),
            ('REVERSED', 'Reversed')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
