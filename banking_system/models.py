# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from banking_system.utils import format_currency
from django.core.exceptions import ValidationError
import re


class Accounts(models.Model):
    account_id = models.IntegerField(primary_key=True)
    customer = models.ForeignKey('Customers', models.DO_NOTHING)
    branch = models.ForeignKey('Branches', models.DO_NOTHING)
    account_type = models.CharField(max_length=30)
    balance = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateField(blank=True, null=True)
    account_number = models.CharField(unique=True, max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'accounts'
        verbose_name = "Accounts"  
        verbose_name_plural = "Accounts"

    def __str__(self):
        customer_name = str(self.customer) if self.customer_id else "No Customer"
        return f"Acc {self.account_id} ({customer_name})"

class Branches(models.Model):
    branch_id = models.AutoField(primary_key=True)
    branch_name = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'branches'
        verbose_name = "Branches"  
        verbose_name_plural = "Branches"

    def __str__(self):
        name = self.branch_name or "Unknown Branch"
        location = self.location or "No location"
        return f"{name} - {location}"

class CustomerPhotos(models.Model):
    photo_id = models.FloatField(primary_key=True)
    customer = models.ForeignKey('Customers', models.DO_NOTHING)
    photo = models.BinaryField(blank=True, null=True)
    uploaded_at = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'customer_photos'
        verbose_name = "Customer Photos"  
        verbose_name_plural = "Customer Photos"

    def __str__(self):
        return self.username


import re
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError, transaction


class Customers(models.Model):
    customer_id = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    email = models.CharField(unique=True, max_length=100)
    phone_number = models.CharField(unique=True, max_length=15)
    address = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateField(blank=True, null=True)

    ID_TYPE_CHOICES = [
        ("National ID", "National ID"),
        ("Voter ID", "Voter ID"),
        ("Passport", "Passport"),
    ]
    id_type = models.CharField(
        max_length=20,
        choices=ID_TYPE_CHOICES,
        default="National ID"
    )

    id_number = models.CharField(unique=True, max_length=50)

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
    )

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
      
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True, default="Active")

    role = models.ForeignKey(
        "Roles",
        on_delete=models.PROTECT,
        db_column="role_id",
        blank=True,
        null=True,
        limit_choices_to={"role_name": "Customer User"},
    )

    class Meta:
        managed = False
        db_table = "customers"
        verbose_name = "Customers"
        verbose_name_plural = "Customers"

    def __str__(self):
        fname = self.first_name or ""
        lname = self.last_name or ""
        return f"{fname} {lname}".strip() or f"Customer {self.customer_id}"

    def clean(self):
        """
        Custom validation for id_number based on Ghana ID formats.
        """
        if self.id_type == "National ID":
            if not re.fullmatch(r"GHA-\d{9}-\d", self.id_number or ""):
                raise ValidationError({
                    "id_number": "National ID must be in the format GHA-123456789-2."
                })

        elif self.id_type == "Voter ID":
            if not re.fullmatch(r"\d{10}", self.id_number or ""):
                raise ValidationError({
                    "id_number": "Voter ID must be exactly 10 digits."
                })

        elif self.id_type == "Passport":
            if not re.fullmatch(r"GHA-[A-Z]{2}-\d{6}", self.id_number or ""):
                raise ValidationError({
                    "id_number": "Passport must be in the format GHA-XX-###### (e.g., GHA-AO-123456)."
                })

    def save(self, *args, **kwargs):
        """
        Catch Oracle constraint violations and translate them into
        Django field errors instead of generic messages.
        """
        try:
            with transaction.atomic():
                super().save(*args, **kwargs)
        except IntegrityError as e:
            error_message = str(e).upper()
            if "CHK_ID_TYPE" in error_message:
                raise ValidationError({"id_type": "Invalid ID type. Must be National ID, Voter ID, or Passport."})
            elif "GENDER" in error_message:
                raise ValidationError({"gender": "Invalid gender. Must be M (Male) or F (Female)."})
            elif "ID_NUMBER" in error_message:
                raise ValidationError({"id_number": "ID number cannot be NULL or must be unique."})
            else:
                raise

class DmlAuditLog(models.Model):
    log_id = models.FloatField(primary_key=True)
    table_name = models.CharField(max_length=50, blank=True, null=True)
    operation = models.CharField(max_length=50, blank=True, null=True)
    primary_key_value = models.CharField(max_length=100, blank=True, null=True)
    column_name = models.CharField(max_length=50, blank=True, null=True)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    changed_by = models.CharField(max_length=50, blank=True, null=True)
    changed_on = models.DateTimeField(blank=True, null=True)
    action_description = models.CharField(max_length=4000, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'dml_audit_log'
        verbose_name = "Dml Audit Log"  
        verbose_name_plural = "Dml Audit Log"

    def __str__(self):
        return f"Log {self.log_id} on {self.table_name} ({self.operation})"


class Employees(models.Model):

    employee_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    JOB_TITLES = [
        ("Admin", "Admin"),
        ("Teller", "Teller"),
        ("Customer_Service_Rep", "Customer Service Rep"),
        ("Branch_Manager", "Branch Manager"),
        ("Loan_Officer", "Loan Officer"),
        ("Relationship_Manager", "Relationship Manager"),
        ("IT_Support", "IT Support"),
        ("Compliance_Officer", "Compliance Officer"),
        ("Audit_Officer", "Audit Officer"),
        ("Operations_Manager", "Operations Manager"),
    ]

    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Inactive", "Inactive"),
        ("Terminated", "Terminated"),
    ]

    ROLE_CHOICES = [
        ("Admin", "Admin"),
        ("Teller", "Teller"),
        ("IT Support", "IT Support"),
    ]

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]

    job_title = models.CharField(max_length=30, choices=JOB_TITLES, blank=True, null=True)
    branch = models.ForeignKey('Branches', on_delete=models.DO_NOTHING)
    email = models.CharField(unique=True, max_length=100, blank=True, null=True)
    phone_number = models.CharField(unique=True, max_length=15, blank=True, null=True)
    hire_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    role = models.ForeignKey('Roles', on_delete=models.DO_NOTHING, db_column="role_id", blank=True, null=True)
    terminated_on = models.DateField(blank=True, null=True)
    termination_reason = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'employees'
        verbose_name = "Employees"  
        verbose_name_plural = "Employees"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.job_title})"

    
class ErrorLogs(models.Model):
    log_id = models.FloatField(primary_key=True)
    error_code = models.FloatField(blank=True, null=True)
    error_message = models.CharField(max_length=4000, blank=True, null=True)
    module_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    triggered_by = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'error_logs'
        verbose_name = "Error Logs"  
        verbose_name_plural = "Error Logs"

    def __str__(self):
        return f"Error {self.error_code}: {self.error_message[:30] if self.error_message else 'No message'}"


class LoanActivityLogs(models.Model):
    log_id = models.FloatField(primary_key=True)
    loan_id = models.FloatField()
    action_type = models.CharField(max_length=50)
    description = models.CharField(max_length=4000, blank=True, null=True)
    performed_by = models.FloatField(blank=True, null=True)
    performed_at = models.DateTimeField(blank=True, null=True)
    module = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'loan_activity_logs'
        verbose_name = "Loan Activity Logs"  
        verbose_name_plural = "Loan Activity Logs"

    def __str__(self):
        return f"LoanLog {self.log_id} - {self.action_type}"

from django.conf import settings
class LoanDisbursementLog(models.Model):
    log_id = models.FloatField(primary_key=True)
    loan = models.ForeignKey('Loans', models.DO_NOTHING)
    disbursed_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    disbursed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    disbursed_on = models.DateField(blank=True, null=True)
    reversed_on = models.DateField(blank=True, null=True)
    reversal = models.CharField(max_length=1, blank=True, null=True)
    action_type = models.CharField(max_length=20, blank=True, null=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    reversal_reason = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'loan_disbursement_log'
        verbose_name = "Loan Disbursement Log"  
        verbose_name_plural = "Loan Disbursement Log"

    def __str__(self):
        return f"Disbursement {self.log_id} for Loan {self.loan_id}"


class LoanRepayments(models.Model):
    repayment_id = models.FloatField(primary_key=True)
    loan = models.ForeignKey('Loans', models.DO_NOTHING)
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    payment_status = models.CharField(max_length=20, blank=True, null=True)
    penalty_applied = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'loan_repayments'
        verbose_name = "Loan Repayments"  
        verbose_name_plural = "Loan Repayments"

    def __str__(self):
        return f"Repayment {self.repayment_id} - {self.payment_status or 'Pending'}"


class Loans(models.Model):
    loan_id = models.IntegerField(primary_key=True)
    customer = models.ForeignKey(Customers, models.DO_NOTHING)
    account = models.ForeignKey(Accounts, models.DO_NOTHING, blank=True, null=True)
    loan_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    disbursed = models.CharField(max_length=1, blank=True, null=True)
    disbursement_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'loans'
        verbose_name = "Loans"  
        verbose_name_plural = "Loans"

    def __str__(self):
        return f"Loan {self.loan_id} - {self.status or 'No status'}"


class LoginLogs(models.Model):
    log_id = models.FloatField(primary_key=True)
    user_id = models.FloatField(blank=True, null=True)
    login_time = models.DateTimeField(blank=True, null=True)
    logout_time = models.DateTimeField(blank=True, null=True)
    session_duration = models.DurationField(blank=True, null=True)
    last_activity = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'login_logs'
        verbose_name = "Login Logs"  
        verbose_name_plural = "Login Logs"

    def __str__(self):
        return f"LoginLog {self.log_id} (User {self.user_id})"


class PasswordHistory(models.Model):
    history_id = models.FloatField(primary_key=True)
    user_id = models.FloatField(blank=True, null=True)
    old_password_hash = models.CharField(max_length=100)
    new_hash = models.CharField(max_length=100, blank=True, null=True)
    changed_by = models.FloatField()
    changed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'password_history'
        verbose_name = "Password History"  
        verbose_name_plural = "Password History"

    def __str__(self):
        return f"PasswordHistory {self.history_id} (User {self.user_id})"


class Permissions(models.Model):
    permission_id = models.FloatField(primary_key=True)
    permission_name = models.CharField(max_length=100)
    module = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'permissions'
        verbose_name = "Permissions"  
        verbose_name_plural = "Permissions"

    def __str__(self):
        return self.permission_name


class RoleAssignmentAudit(models.Model):
    audit_id = models.FloatField(primary_key=True)
    admin_user_id = models.FloatField()
    target_user_id = models.FloatField()
    role = models.ForeignKey('Roles', models.DO_NOTHING)
    assigned_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'role_assignment_audit'
        verbose_name = "Role Assignment Audit"  
        verbose_name_plural = "Role Assignment Audit"

    def __str__(self):
        return f"RoleAssignment {self.audit_id} -> {self.role}"


class Roles(models.Model):
    role_id = models.IntegerField(primary_key=True)
    role_name = models.CharField(max_length=50, unique=True)

    class Meta:
        managed = False
        db_table = 'roles'
        verbose_name = "Roles"  
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.role_name or f"Role {self.role_id}"


class Salaries(models.Model):
    salary_id = models.FloatField(primary_key=True)
    employee_id = models.FloatField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateField(blank=True, null=True)
    paid_for_month = models.DateField()
    payment_month = models.CharField(max_length=20, blank=True, null=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    payment_status = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'salaries'
        verbose_name = "Salaries"  
        verbose_name_plural = "Salaries"

    def __str__(self):
        return f"Salary {self.salary_id} ({self.amount})"


class SalaryStructureHistory(models.Model):
    structure_id = models.IntegerField(primary_key=True)
    employee_id = models.FloatField()
    base_pay = models.DecimalField(max_digits=10, decimal_places=2)
    allowance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    deduction = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    effective_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'salary_structure_history'
        verbose_name = "Salary Structure History"  
        verbose_name_plural = "Salary Structure History"

    def __str__(self):
        return f"SalaryStructureHistory {self.structure_id}"


class SalaryStructures(models.Model):
    structure_id = models.FloatField(primary_key=True)
    employee = models.ForeignKey(Employees, models.DO_NOTHING)
    base_pay = models.DecimalField(max_digits=10, decimal_places=2)
    allowance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    deduction = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    effective_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'salary_structures'
        verbose_name = "Salary Structures"
        verbose_name_plural = "Salary Structures"

    def __str__(self):
        return f"SalaryStructure {self.structure_id} for {self.employee}"

class TransactionStatusAudit(models.Model):
    audit_id = models.FloatField(primary_key=True)
    transaction_id = models.FloatField(blank=True, null=True)
    old_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20, blank=True, null=True)
    changed_at = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'transaction_status_audit'
        verbose_name = "Transaction Status Audit" 
        verbose_name_plural = "Transaction Status Audit" 

    def __str__(self):
        return f"TxnAudit {self.audit_id} - {self.old_status} → {self.new_status}"


class Transactions(models.Model):
    transaction_id = models.IntegerField(primary_key=True)
    account = models.ForeignKey(Accounts, models.DO_NOTHING)
    transaction_type = models.CharField(max_length=10, blank=True, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    source_account = models.CharField(max_length=20, blank=True, null=True)
    destination_account = models.CharField(max_length=20, blank=True, null=True)
    reversal_of = models.FloatField(blank=True, null=True)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'transactions'
        verbose_name = "Transactions" 
        verbose_name_plural = "Transactions" 

    def __str__(self):
        return f"{self.transaction_type} of {format_currency(self.amount)} on {self.transaction_date} (Acc: {self.account_id})"


class UserRole(models.Model):
    user_role_id = models.FloatField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey('Roles', models.DO_NOTHING, blank=True, null=True)
    assigned_at = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_role'
        verbose_name = "User Role" 
        verbose_name_plural = "User Roles"

    def __str__(self):
        return f"{self.user} - {self.role}"


# ====================================USERS MODEL.PY==============================

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models, connection
from django.utils import timezone
from django.contrib.auth.hashers import check_password as django_check_password

class CbacUserManager(BaseUserManager):
    use_in_migrations = True

    def _call_oracle_hash(self, raw_password):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT CBAC_UTILS_PKG.hash_password(:pwd) FROM dual",
                {"pwd": raw_password}
            )
            hashed, = cursor.fetchone()
        return hashed

    def create_user(self, username, email, password=None, user_type="EMPLOYEE", **extra_fields):
        if not username:
            raise ValueError("The Username must be set")
        if not email:
            raise ValueError("The Email must be set")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, user_type=user_type, **extra_fields)

        if not password:
            raise ValueError("Password must be set")

        # Hash via Oracle
        hashed = self._call_oracle_hash(password)
        user.password = hashed

        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not password:
            raise ValueError("Superuser must have a password")
        user_type = extra_fields.pop("user_type", "EMPLOYEE")
        return self.create_user(username, email, password, user_type=user_type, **extra_fields)


class CbacUser(AbstractBaseUser):
    user_id = models.BigAutoField(primary_key=True, db_column="user_id")
    username = models.CharField(max_length=150, unique=True, db_column="username")
    email = models.EmailField(unique=True, null=True, blank=True, db_column="email")

    # we keep the field name `password` but map to your actual column name
    password = models.CharField(max_length=255, db_column="password_hash")

    user_type = models.CharField(max_length=50, choices=[("EMPLOYEE", "Employee"), ("CUSTOMER", "Customer")])
    reference_id = models.IntegerField(null=True, blank=True, db_column="reference_id")
    status = models.CharField(max_length=20, blank=True, null=True, db_column="status")
    created_at = models.DateTimeField(default=timezone.now, db_column="created_at")
    last_login = models.DateTimeField(blank=True, null=True, db_column="last_login")

    # required boolean flags (ensure corresponding column exists in DB)
    is_active = models.BooleanField(default=True, db_column="is_active")
    is_staff = models.BooleanField(default=False, db_column="is_staff")
    is_superuser = models.BooleanField(default=False, db_column="is_superuser")  # << IMPORTANT

    # =============== TEMPORARY PERMISSIONS FOR IS_SUPERUSER=====================
    def has_perm(self, perm, obj=None):
        return self.is_superuser  # quick way: superuser can do anything

    def has_module_perms(self, app_label):
        return self.is_superuser


    # ==============================================================================
    
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "user_type"]

    objects = CbacUserManager()

    class Meta:
        db_table = "users"
        managed = False
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username

    def set_password(self, raw_password):
        """Hash password with Oracle's package and store in `password` field."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT CBAC_UTILS_PKG.hash_password(:pw) FROM dual", {"pw": raw_password})
            hashed, = cursor.fetchone()
        self.password = hashed

    def check_password(self, raw_password):
        """Try Oracle hash check first, then fallback to Django pbkdf2 (if legacy)."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT CBAC_UTILS_PKG.hash_password(:pw) FROM dual", {"pw": raw_password})
            oracle_hashed, = cursor.fetchone()

        # Compare against stored column `password`
        if self.password == oracle_hashed:
            return True

        return django_check_password(raw_password, self.password)

    @property
    def date_joined(self):
        return self.created_at

from django.db import models

class RolePermissions(models.Model):
    role_permission_id = models.BigAutoField(db_column="role_permission_id", primary_key=True)
    role = models.ForeignKey(Roles, db_column="role_id", on_delete=models.CASCADE)
    permission = models.ForeignKey(Permissions, db_column="permission_id", on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = "role_permissions"
        unique_together = (("role", "permission"),)  # still enforce composite uniqueness
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"

    def __str__(self):
        return f"{self.role.role_name} ↔ {self.permission.permission_name}"
