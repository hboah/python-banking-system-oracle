from django.contrib import admin 
from . import utils
from django.contrib.auth.admin import UserAdmin
from .inlines import LogEntryInline
from django.contrib.admin.models import LogEntry
from decimal import Decimal
from django.utils.html import format_html
from django.urls import reverse
from .models import CbacUser
from .forms import CbacUserChangeForm
from .models import CbacUser
from .utils import format_currency
from .models import (
    Customers, Accounts, Branches, Employees, Transactions,
    Loans, LoanRepayments, LoanDisbursementLog, CustomerPhotos,
    CbacUser, Roles, Permissions, UserRole,
    DmlAuditLog, ErrorLogs, LoanActivityLogs, LoginLogs,
    PasswordHistory, RoleAssignmentAudit,
    Salaries, SalaryStructureHistory, RolePermissions, SalaryStructures,
    TransactionStatusAudit
)

class LogEntryHistoryMixin:
    def history_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        logs = LogEntry.objects.filter(
            object_id=object_id,
            content_type__app_label=self.model._meta.app_label,
            content_type__model=self.model._meta.model_name,
        ).select_related("user").order_by("-action_time")

        extra_context = extra_context or {}
        extra_context["custom_logs"] = logs
        return super().history_view(request, object_id, extra_context=extra_context)

    def custom_log_display(self, log):
        return format_html(
            "{} by {} on {} <br><small>{}</small>",
            {1: "Added", 2: "Changed", 3: "Deleted"}.get(log.action_flag, log.action_flag),
            log.user,
            log.action_time.strftime("%Y-%m-%d %H:%M"),
            log.change_message or "-",
        )
# --- ------------------------------------------INLINES ---
class AccountInline(admin.TabularInline):
    model = Accounts
    extra = 0
    can_delete = False
    fields = ("account_number", "account_type", "formatted_amount", "status")
    readonly_fields = ("account_number", "formatted_amount", "status", "account_type")

    def formatted_amount(self, obj):
        return format_currency(obj.balance)
    formatted_amount.short_description = "Balance"

class CustomerInline(admin.TabularInline):
    model = Customers
    extra = 0
    can_delete = False
    fields = ("customer_id", "first_name", "last_name", "email", "phone_number", "address")
    readonly_fields = ("customer_id", "first_name", "last_name", "email", "phone_number", "address")

class LoanInline(admin.TabularInline):
    model = Loans
    extra = 0
    can_delete = False
    fields = ("formatted_amount", "interest_rate", "status", "start_date", "end_date")
    readonly_fields = ("formatted_amount", "interest_rate", "status", "start_date", "end_date")

    def formatted_amount(self, obj):
        return format_currency(obj.loan_amount)
    formatted_amount.short_description = "Loan Amount"

class TransactionInline(admin.TabularInline):
    model = Transactions
    extra = 0
    can_delete = False
    show_change_link = False

    # Explicitly only show these fields (all readonly)
    fields = ("transaction_type", "formatted_amount", "source_account", "destination_account", "transaction_date", "status")
    readonly_fields = ("transaction_type", "formatted_amount", "source_account", "destination_account", "transaction_date", "status")

    def formatted_amount(self, obj):
        print("✔ TransactionInline is active") 
        if obj.amount is not None:
            return format_currency(obj.amount)
        return "-"
    formatted_amount.short_description = "Amount"


class SalaryStructureInline(admin.TabularInline):
    model = SalaryStructures
    extra = 0
    can_delete = False
    fields = ("base_pay", "allowance", "deduction", "currency", "effective_date", "is_active")
    readonly_fields = ("base_pay", "allowance", "deduction", "currency", "effective_date", "is_active")

class RolePermissionsInline(admin.TabularInline):
    model = RolePermissions
    extra = 0
    fields = ("permission",)   # only show permission name
    readonly_fields = ("permission",)  # make it read-only in inline
    can_delete = False  # optional: prevent removing via inline

    def has_add_permission(self, request, obj=None):
        return False  # add via PL/SQL grant procedure, not inline

class RolesWithPermissionInline(admin.TabularInline):
    model = RolePermissions
    fk_name = "permission"   # this side of the relation
    extra = 0
    fields = ("role",)
    readonly_fields = ("role",)
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False  # don't add from here (use PL/SQL grant procedure instead)

# --- CUSTOM ADMINS WITH INLINES ---
@admin.register(Customers)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_id", "first_name", "last_name", "email", "phone_number", "status", "id_type", "role", "gender")
    search_fields = ("first_name", "last_name", "email", "phone_number", "id_number")
    list_filter = ("status", "gender", "id_type", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        try:
            return qs.select_related("role")
        except Exception:
        # fallback if some rows have invalid/missing roles
            return qs

    
    fieldsets = (
        ("Personal Information", {
            "fields": ("first_name", "last_name", "date_of_birth", "gender", "id_type", "id_number", "role")
        }),
        ("Contact Information", {
            "fields": ("email", "phone_number", "address")
        }),
        ("System Information", {
            "fields": ("status", "created_at")
        }),
    )

    inlines = [AccountInline, LoanInline]

@admin.register(Accounts)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "account_id",
        "account_number",
        "customer",
        "account_type",
        "branch",
        "formatted_amount",
        "status",
        "created_at",
    )
    search_fields = (
        "account_number",
        "customer__first_name",
        "customer__last_name",
        "branch__branch_name",  # fixed
    )
    list_filter = ("status", "account_type", "created_at", "branch")
    ordering = ("-created_at",)

    inlines = [TransactionInline]

    # This way, Django fetches customers and branches in one SQL join instead of 300+ queries
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("customer", "branch")  # Prefetch FK

    def formatted_amount(self, obj):
        return format_currency(obj.balance)
    formatted_amount.short_description = "Balance"

    #def get_queryset(self, request):
        #qs = super().get_queryset(request)
        #return qs.select_related("branch")

@admin.register(Employees)
class EmployeeAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Personal Information", {
            "fields": ("first_name", "last_name", "job_title", "role", "gender", "date_of_birth", "address"	)
        }),
        ("Contact Information", {
            "fields": ("email", "phone_number")
        }),
        ("Employment Details", {
            "fields": ("branch", "hire_date", "status")
        }),
        ("Termination Details", {
            "fields": ("terminated_on", "termination_reason")
        }),
    )

    list_display = (
        "employee_id",
        "first_name",
        "last_name",
        "job_title",
        "branch",
        "status",
        "role",
        "gender", 
        "date_of_birth", 
        "address",
    )

    search_fields = ("first_name", "last_name", "email", "phone_number")
    list_filter = ("status", "job_title", "branch", "role")
    ordering = ("first_name",)

    def get_queryset(self, request):
        # Optimize queries by joining related objects
        qs = super().get_queryset(request)
        return qs.select_related("branch", "role")  # eager load both FKs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "role":
            kwargs["queryset"] = Roles.objects.filter(role_name__in=["Admin", "Teller", "IT Support"])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    inlines = [SalaryStructureInline]
    #inlines = [LogEntryInline]


@admin.register(Transactions)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "account", "transaction_type", "formatted_amount", "transaction_date", "status")
    search_fields = ("transaction_id", "account__account_number")
    list_filter = ("transaction_type", "status", "transaction_date")
    ordering = ("-transaction_date",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "account",              # join account
            "account__customer",    # join customer via account
            "account__branch",      # join branch via account
        )

    # Helper method to display customer name directly
    def customer_name(self, obj):
        return f"{obj.account.customer.first_name} {obj.account.customer.last_name}"
    customer_name.short_description = "Customer"

    # Helper method to display branch name directly
    def branch(self, obj):
        return obj.account.branch.branch_name
    branch.short_description = "Branch"

    def formatted_amount(self, obj):
        return format_currency(obj.amount)
    formatted_amount.short_description = "Amount"

@admin.register(LoanRepayments)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = (
        "repayment_id",
        "loan_display",
        "due_date",
        "formatted_amount_due",
        "formatted_amount_paid",
        "payment_status",
        "penalty_applied",
    )
    search_fields = (
        "repayment_id",
        "loan__loan_id",
        "loan__customer__first_name",
        "loan__customer__last_name",
    )
    list_filter = ("due_date", "payment_status")
    ordering = ("-due_date",)

    def loan_display(self, obj):
        # Just show the loan's ID (or str(obj.loan) if your Loan model __str__ handles it well)
        return str(obj.loan)
    loan_display.short_description = "Loan"

    def formatted_amount_due(self, obj):
        return format_currency(obj.amount_due)
    formatted_amount_due.short_description = "Amount Due"

    def formatted_amount_paid(self, obj):
        return format_currency(obj.amount_paid)
    formatted_amount_paid.short_description = "Amount Paid"
    
@admin.register(Loans)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "loan_id",
        "customer",  # already shows nicely using Customers.__str__
        "formatted_loan_amount",
        "interest_rate",
        "status",
        "start_date",
        "end_date",
        "account",   # show related account
        "branch",    # custom branch column
    )
    search_fields = ("loan_id", "customer__first_name", "customer__last_name")
    list_filter = ("status", "start_date", "end_date")
    ordering = ("-start_date",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "customer",
            "account__branch",  # optimized join for branch
        )

    def formatted_loan_amount(self, obj):
        return format_currency(obj.loan_amount)
    formatted_loan_amount.short_description = "Loan Amount"

    def branch(self, obj):
        if obj.account and obj.account.branch:
            return obj.account.branch.branch_name
        return "-"
    branch.short_description = "Branch"

@admin.register(Branches)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("branch_id", "branch_name", "address", "phone", "location")
    search_fields = ("branch_name", "location")
    list_filter = ("location",)
    ordering = ("branch_name",)
    #inlines = [LogEntryInline]

#============================================CBAC USER=======================================
# banking_system/admin.py
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db import connection, DatabaseError
from .models import CbacUser, Roles
from .forms import CbacUserCreationForm, CbacUserChangeForm
from . import utils
import csv
from django.http import HttpResponse
from openpyxl import Workbook

@admin.register(CbacUser)
class CbacUserAdmin(admin.ModelAdmin):
    form = CbacUserChangeForm
    add_form = CbacUserCreationForm

    list_display = ("user_id", "username", "email", "user_type", "status",
                    "is_active", "is_staff", "is_superuser", "last_login", "created_at", "admin_actions")
    list_filter = ("is_active", "is_staff", "is_superuser", "user_type", "status")
    search_fields = ("username", "email", "user_type", "status")
    ordering = ("user_id",)
    readonly_fields = ("last_login", "created_at")

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("CBAC Info", {"fields": ("user_type", "reference_id", "status")}),
        ("Flags", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "user_type", "status", "password", "is_active", "is_staff", "is_superuser", "phone_number"),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            defaults = {"form": self.add_form}
        else:
            defaults = {"form": self.form}
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def admin_actions(self, obj):
        """Render action links on each row"""
        reset_url = reverse('admin:cbacuser-reset-password', args=[obj.user_id])
        assign_url = reverse('admin:cbacuser-assign-role', args=[obj.user_id])
        revoke_url = reverse('admin:cbacuser-revoke-role', args=[obj.user_id])
        logs_url = reverse('admin:cbacuser-view-logs', args=[obj.user_id])
        perms_url = reverse('admin:cbacuser-view-perms', args=[obj.user_id])
        delete_url = reverse('admin:cbacuser-delete-user', args=[obj.user_id])
        diagnostics_url = reverse('admin:cbacuser-session-diagnostics')

        return format_html(
        '<div class="admin-action-buttons">'
        '<a class="button" href="{}">Reset PW</a>'
        '<a class="button" href="{}">Assign Role</a>'
        '<a class="button" href="{}">Revoke Role</a>'
        '<a class="button" href="{}">Logs</a>'
        '<a class="button" href="{}">Perms</a>'
        '<a class="button deletelink" href="{}">Delete</a>'
        '<a class="button" href="{}">Diagnostics</a>'
        '</div>',
        reset_url, assign_url, revoke_url, logs_url, perms_url, delete_url, diagnostics_url
    )

    admin_actions.short_description = "Admin actions"
    admin_actions.allow_tags = True

    # custom URLs for per-user admin actions
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:user_id>/reset-password/', self.admin_site.admin_view(self.reset_password_view), name='cbacuser-reset-password'),
            path('<int:user_id>/assign-role/', self.admin_site.admin_view(self.assign_role_view), name='cbacuser-assign-role'),
            path('<int:user_id>/revoke-role/', self.admin_site.admin_view(self.revoke_role_view), name='cbacuser-revoke-role'),
            path('<int:user_id>/view-logs/', self.admin_site.admin_view(self.view_logs_view), name='cbacuser-view-logs'),
            path('<int:user_id>/view-perms/', self.admin_site.admin_view(self.view_perms_view), name='cbacuser-view-perms'),
            path('<int:user_id>/delete-user/', self.admin_site.admin_view(self.delete_user_view), name='cbacuser-delete-user'),
            path("session-diagnostics/", self.admin_site.admin_view(self.session_diagnostics_view), name="cbacuser-session-diagnostics",),
            path("<int:user_id>/export-perms-csv/", self.admin_site.admin_view(self.export_perms_csv), name="banking_system_cbacuser_export_perms_csv",),
            path("<int:user_id>/export-perms-xlsx/", self.admin_site.admin_view(self.export_perms_xlsx), name="banking_system_cbacuser_export_perms_xlsx",),
        ]
        return custom + urls

    # ---------- save_model: create via package when adding ----------
    def save_model(self, request, obj, form, change):
        # if creating a new user: call cbac_user_mgmt_pkg.create_user(username, password, phone)
        utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
        if not change:
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password")
            phone = form.cleaned_data.get("phone_number") or None

            try:
                with connection.cursor() as cur:
                    # call procedure: create_user(p_username, p_password, p_phone_number)
                    cur.callproc("cbac_user_mgmt_pkg.create_user", [username, raw_password, phone])
                self.message_user(request, f"Created user '{username}' via cbac_user_mgmt_pkg.create_user", level=messages.SUCCESS)
            except DatabaseError as e:
                # show DB error message
                self.message_user(request, f"Database error creating user: {e}", level=messages.ERROR)
                raise
        else:
            # updating existing -> attempt to call update_user if package has it; otherwise fallback to ORM save
            try:
                with connection.cursor() as cur:
                    # try to call package update_user
                    # we need to prepare all params in the same order as the PL/SQL update_user we added earlier
                    cur.callproc("cbac_user_mgmt_pkg.update_user", [
                        obj.user_id,
                        obj.username,
                        obj.email,
                        obj.user_type,
                        obj.reference_id,
                        obj.status or 'ACTIVE',
                        1 if obj.is_active else 0,
                        1 if obj.is_staff else 0,
                        1 if obj.is_superuser else 0,
                    ])
                self.message_user(request, f"Updated user '{obj.username}' via cbac_user_mgmt_pkg.update_user", level=messages.SUCCESS)
            except DatabaseError:
                # fallback: save via Django ORM (useful while package change isn't installed)
                super().save_model(request, obj, form, change)
                self.message_user(request, "Update saved locally (package update_user call failed)", level=messages.WARNING)

    # ---------- Admin view handlers ----------
    def reset_password_view(self, request, user_id):
        user = get_object_or_404(CbacUser, pk=user_id)
        utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
        if request.method == "POST":
            new_pw = request.POST.get("new_password")
            if not new_pw or len(new_pw) < 8:
                self.message_user(request, "Password must be at least 8 characters", level=messages.ERROR)
            else:
                try:
                    with connection.cursor() as cur:
                        cur.callproc("cbac_user_mgmt_pkg.reset_user_password", [user.username, new_pw])
                    self.message_user(request, f"Password reset for {user.username}", level=messages.SUCCESS)
                    return redirect(reverse('admin:banking_system_cbacuser_changelist'))
                except DatabaseError as e:
                    self.message_user(request, f"DB error: {e}", level=messages.ERROR)
        # GET => render form
        context = dict(
            self.admin_site.each_context(request),
            user=user,
        )
        return render(request, "admin/cbacuser/reset_password.html", context)

    def assign_role_view(self, request, user_id):
        user = get_object_or_404(CbacUser, pk=user_id)
        utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
        # load roles from DB table Roles (Django model)
        roles = Roles.objects.all()
        if request.method == "POST":
            role_id = request.POST.get("role_id")
            print("DEBUG: assigning role", role_id, "to user", user.username)

            try:
                with connection.cursor() as cur:
                    cur.callproc("cbac_user_mgmt_pkg.assign_role_to_user", [user.username.strip().lower(), int(role_id)])
                self.message_user(request, f"Assigned role id {role_id} to {user.username}", level=messages.SUCCESS)
                return redirect(reverse('admin:banking_system_cbacuser_changelist'))
            except DatabaseError as e:
                self.message_user(request, f"DB error: {e}", level=messages.ERROR)
        context = dict(self.admin_site.each_context(request), user=user, roles=roles)
        return render(request, "admin/cbacuser/assign_role.html", context)

    def revoke_role_view(self, request, user_id):
        user = get_object_or_404(CbacUser, pk=user_id)
        utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
        roles = Roles.objects.all()
        if request.method == "POST":
            role_id = int(request.POST.get("role_id"))
            try:
                with connection.cursor() as cur:
                    cur.callproc("cbac_user_mgmt_pkg.revoke_role_from_user", [user.user_id, role_id])
                self.message_user(request, f"Revoked role {role_id} from {user.username}", level=messages.SUCCESS)
                return redirect(reverse('admin:banking_system_cbacuser_changelist'))
            except DatabaseError as e:
                self.message_user(request, f"DB error: {e}", level=messages.ERROR)
        context = dict(self.admin_site.each_context(request), user=user, roles=roles)
        return render(request, "admin/cbacuser/revoke_role.html", context)

    def view_logs_view(self, request, user_id):
        user = get_object_or_404(CbacUser, pk=user_id)
        try:
            utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
            cols, rows = utils.call_proc_with_one_out_refcursor("cbac_user_mgmt_pkg.view_user_login_logs", [user.username])
        except Exception as e:
            self.message_user(request, f"Error fetching logs: {e}", level=messages.ERROR)
            cols, rows = [], []
        context = dict(self.admin_site.each_context(request), user=user, cols=cols, rows=rows)
        return render(request, "admin/cbacuser/view_logs.html", context)

    def view_perms_view(self, request, user_id):
        user = get_object_or_404(CbacUser, pk=user_id)

        cols, rows = [], []
        error_message = None

        try:
            utils.set_cbac_session(request) #get the current(logged in) user's id for permission check

            cols, rows = utils.call_proc_with_one_out_refcursor(
                    "cbac_user_mgmt_pkg.view_user_all_permissions",
                    [user.username]
                )
        except Exception as e:
            error_message = str(e)
            self.message_user(
                request,
                f"Error fetching permissions: {error_message}",
                level=messages.ERROR
            )

        context = dict(
            self.admin_site.each_context(request),
            user=user,
            user_id=user_id,   # 👈 add this line
            cols=cols,
            oracle_perms=rows,
            error=error_message
        )

        return render(request, "admin/cbacuser/view_permissions.html", context)

    def export_perms_csv(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(CbacUser, pk=user_id)
        utils.set_cbac_session(request) #get the current(logged in) user's id for permission check

        try:
            cols, rows = utils.call_proc_with_one_out_refcursor(
                "cbac_user_mgmt_pkg.view_user_all_permissions",
                [user.username]
            )
        except Exception as e:
            self.message_user(request, f"Error exporting permissions: {e}", level=messages.ERROR)
            return HttpResponse("Export failed.", status=500)

        # Create response with CSV header
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{user.username}_permissions.csv"'

        writer = csv.writer(response)
        writer.writerow(cols)  # header
        for row in rows:
            writer.writerow(row)

        return response

    def export_perms_xlsx(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(CbacUser, pk=user_id)
        utils.set_cbac_session(request) #get the current(logged in) user's id for permission check

        try:
            cols, rows = utils.call_proc_with_one_out_refcursor(
                "cbac_user_mgmt_pkg.view_user_all_permissions",
                [user.username]
            )
        except Exception as e:
            self.message_user(request, f"Error exporting permissions: {e}", level=messages.ERROR)
            return HttpResponse("Export failed.", status=500)

        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Permissions"

        # Header row
        ws.append(cols)

        # Data rows
        for row in rows:
            ws.append(row)

        # Prepare HTTP response
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{user.username}_permissions.xlsx"'

        wb.save(response)
        return response

    def delete_user_view(self, request, user_id):
        user = get_object_or_404(CbacUser, pk=user_id)
        utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
        if request.method == "POST":
            try:
                with connection.cursor() as cur:
                    cur.callproc("cbac_user_mgmt_pkg.delete_user", [user.username])
                self.message_user(request, f"Deleted user {user.username} via package", level=messages.SUCCESS)
                return redirect(reverse('admin:banking_system_cbacuser_changelist'))
            except DatabaseError as e:
                self.message_user(request, f"DB error: {e}", level=messages.ERROR)
        context = dict(self.admin_site.each_context(request), user=user)
        return render(request, "admin/cbacuser/delete_user_confirm.html", context)

    def session_diagnostics_view(self, request):
        diagnostics = {}
        cols, rows = [], []
        error = None
        utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
        if request.method == "POST":
            try:
                with connection.cursor() as cursor:
                    cursor.callproc("cbac_user_mgmt_pkg.session_diagnostics")

                    cursor.execute("""
                        SELECT
                            sys_context('USERENV','SESSION_USER')       AS session_user,
                            sys_context('USERENV','CURRENT_USER')       AS current_user,
                            sys_context('USERENV','OS_USER')            AS os_user,
                            sys_context('USERENV','IP_ADDRESS')         AS ip_address,
                            sys_context('USERENV','MODULE')             AS module,
                            sys_context('USERENV','CLIENT_IDENTIFIER')  AS client_id
                        FROM dual
                    """)
                    rows = cursor.fetchall()
                    cols = [col[0] for col in cursor.description]

                    if rows:
                        diagnostics = dict(zip(cols, rows[0]))

                self.message_user(request, "Session diagnostics executed successfully!")
            except Exception as e:
                error = str(e)
                self.message_user(request, f"Error: {error}", level="error")

        context = dict(
            self.admin_site.each_context(request),
            diagnostics=diagnostics,
            cols=cols,
            rows=rows,
            error=error,
        )
        return render(request, "admin/cbacuser/session_diagnostics.html", context)

# ------------------------------------------------------------------------------------------
# Roles & Permissions
# ------------------------------------------------------------------------------------------
from django.http import JsonResponse
from django.db.models import Q

class AutocompleteMixin:
    def get_autocomplete(self, request, model, field):
        if not request.user.is_authenticated:
            return JsonResponse([], safe=False)

        term = request.GET.get("term", "")
        qs = model.objects.all()
        if term:
            qs = qs.filter(Q(**{f"{field}__icontains": term}))

        results = [
            {"id": obj.pk, "text": getattr(obj, field)}
            for obj in qs[:20]  # limit results
        ]
        return JsonResponse({"results": results})


# admin.py (relevant parts)
from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.db.models import Q
from django.db import connection, DatabaseError

# IMPORT your models
from .models import Roles, Permissions, RolePermissions

# ROLE admin: expose permission-autocomplete endpoint
@admin.register(Roles)
class RolesAdmin(admin.ModelAdmin):
    list_display = ("role_id", "role_name", "grant_permission_button")
    search_fields = ("role_name",)
    ordering = ("role_name",)
    inlines = [RolePermissionsInline]  # keep your inline

    def grant_permission_button(self, obj):
        url = reverse("admin:grant_permission_to_role", args=[obj.pk])
        return format_html('<a class="button" href="{}">Grant Permission</a>', url)
    grant_permission_button.short_description = "Grant Permission"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:role_id>/grant-permission/",
                self.admin_site.admin_view(self.grant_permission_view),
                name="grant_permission_to_role",
            ),
            # ✅ autocomplete returning permissions
            path(
                "permissions-autocomplete/",
                self.admin_site.admin_view(self.permissions_autocomplete),
                name="banking_system_permissions_autocomplete",
            ),
        ]
        return custom_urls + urls

    def permissions_autocomplete(self, request):
        term = request.GET.get("term", "")
        qs = Permissions.objects.all()
        if term:
            qs = qs.filter(permission_name__icontains=term)
        results = [{"id": p.pk, "text": p.permission_name} for p in qs[:50]]
        return JsonResponse({"results": results})


    def grant_permission_view(self, request, role_id):
        utils.set_cbac_session(request)
        role = Roles.objects.get(pk=role_id)

        if request.method == "POST":
            permission_id = request.POST.get("permission_id")
            permission = Permissions.objects.get(pk=permission_id)
            try:
                with connection.cursor() as cur:
                    cur.callproc("cbac_utils_pkg.grant_permission_to_role", [
                        role.role_name.strip().lower(),
                        permission.permission_name.strip().lower()
                    ])
                self.message_user(
                    request,
                    f"Granted '{permission.permission_name}' to role '{role.role_name}'",
                    level=messages.SUCCESS
                )
                return redirect(f"../../{role_id}/change/")
            except DatabaseError as e:
                self.message_user(request, f"DB error: {e}", level=messages.ERROR)

        # ✅ preload permissions for the dropdown
        permissions = Permissions.objects.all()
        context = dict(self.admin_site.each_context(request), role=role, permissions=permissions)
        return render(request, "admin/roles/grant_permission.html", context)

# PERMISSION admin: expose roles-autocomplete endpoint
@admin.register(Permissions)
class PermissionsAdmin(admin.ModelAdmin):
    list_display = ("permission_id", "permission_name", "grant_to_role_button")
    search_fields = ("permission_name",)
    ordering = ("permission_name",)
    inlines = [RolesWithPermissionInline]  # your inline here

    def grant_to_role_button(self, obj):
        url = reverse("admin:grant_permission_from_permission", args=[obj.pk])
        return format_html('<a class="button" href="{}">Grant to Role</a>', url)
    grant_to_role_button.short_description = "Grant to Role"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:permission_id>/grant-to-role/",
                self.admin_site.admin_view(self.grant_to_role_view),
                name="grant_permission_from_permission",
            ),
            # autocomplete returning roles (for Grant to Role page)
            path(
                "roles-autocomplete/",
                self.admin_site.admin_view(self.roles_autocomplete),
                name="banking_system_roles_autocomplete",
            ),
        ]
        return custom_urls + urls

    def roles_autocomplete(self, request):
        term = request.GET.get("term", "")
        qs = Roles.objects.all()
        if term:
            qs = qs.filter(role_name__icontains=term)
        results = [{"id": r.pk, "text": r.role_name} for r in qs[:50]]
        return JsonResponse({"results": results})

    def grant_to_role_view(self, request, permission_id):
        utils.set_cbac_session(request)
        permission = Permissions.objects.get(pk=permission_id)
        if request.method == "POST":
            role_id = request.POST.get("role_id")
            role = Roles.objects.get(pk=role_id)
            try:
                with connection.cursor() as cur:
                    cur.callproc("cbac_utils_pkg.grant_permission_to_role", [
                        role.role_name.strip().lower(),
                        permission.permission_name.strip().lower()
                    ])
                self.message_user(request, f"Granted '{permission.permission_name}' to role '{role.role_name}'", level=messages.SUCCESS)
                return redirect("../")
            except DatabaseError as e:
                self.message_user(request, f"DB error: {e}", level=messages.ERROR)

        context = dict(self.admin_site.each_context(request), permission=permission)
        return render(request, "admin/permissions/grant_to_role.html", context)


from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.db import connection, DatabaseError
from .models import Roles, Permissions, RolePermissions
from django.urls import path
from .models import RolePermissions
from django.urls import reverse
from django.utils.html import format_html

@admin.register(RolePermissions)
class RolePermissionsAdmin(admin.ModelAdmin):
    list_display = ("role", "permission", "view_link")
    list_filter = ("role", "permission")
    search_fields = ("role__role_name", "permission__permission_name")
    autocomplete_fields = ["role", "permission"]

    def get_queryset(self, request):
        # Don’t let Django expect "id"
        return super().get_queryset(request).select_related("role", "permission")

    def view_link(self, obj):
        """Custom link column so list_display doesn't try to use 'id'."""
        url = reverse(
            "admin:banking_system_rolepermissions_change",
            args=[obj.pk],
        )
        return format_html('<a href="{}">Edit</a>', url)

    view_link.short_description = "Edit"

# admin.py
from django.urls import path
from django.shortcuts import redirect, render
from django.contrib import messages
from django import forms
from .models import Roles, Permissions, RolePermissions

class GrantPermissionForm(forms.Form):
    permission = forms.ModelChoiceField(
        queryset=Permissions.objects.all(),
        label="Select Permission"
    )


# -------------------------
# UserRole (mapping table)
# -------------------------
@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user_role_id", "user", "role", "assigned_at")
    search_fields = ("user", "role")
    list_filter = ("user", "role", "assigned_at",)
    ordering = ("-assigned_at",)
    #inlines = [LogEntryInline]

# -------------------------
# Audit & Logs
# -------------------------
@admin.register(DmlAuditLog)
class DmlAuditLogAdmin(admin.ModelAdmin):
    list_display = ("log_id", "table_name", "operation", "primary_key_value", "column_name", "old_value", "new_value", "changed_by", "changed_on", "action_description")
    search_fields = ("table_name", "changed_by" , "operation")
    list_filter = ("operation", "changed_on", "table_name",)
    ordering = ("-changed_on",)
    #inlines = [LogEntryInline]

@admin.register(ErrorLogs)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ("log_id", "error_code", "error_message", "module_name", "created_at", "triggered_by")
    search_fields = ("error_code", "error_message",)
    list_filter = ("created_at",)
    ordering = ("-created_at",)
    #inlines = [LogEntryInline]

@admin.register(LoanActivityLogs)
class LoanActivityLogAdmin(admin.ModelAdmin):
    list_display = ("log_id", "loan_id", "action_type", "description", "performed_by", "performed_at", "module")
    search_fields = ("loan__loan_id",)
    list_filter = ("action_type", "performed_at",)
    ordering = ("-performed_at",)
    #inlines = [LogEntryInline]

@admin.register(LoginLogs)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ("log_id", "user_id", "login_time", "logout_time", "session_duration", "last_activity")
    search_fields = ("user__username",)
    list_filter = ("user_id", "login_time",)
    ordering = ("-login_time",)
    #inlines = [LogEntryInline]

@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    list_display = ("history_id", "user_id", "old_password_hash", "new_hash", "changed_by", "changed_at")
    search_fields = ("user__username", "user_id",)
    list_filter = ("changed_at", "user_id",)
    ordering = ("-changed_at",)
    #inlines = [LogEntryInline]

@admin.register(RoleAssignmentAudit)
class RoleAssignmentAuditAdmin(admin.ModelAdmin):
    list_display = ("audit_id", "admin_user_id", "target_user_id", "role", "assigned_at")
    search_fields = ("user__username", "role__name", "assigned_by")
    list_filter = ("assigned_at",)
    ordering = ("-assigned_at",)
    #inlines = [LogEntryInline]

@admin.register(TransactionStatusAudit)
class TransactionStatusAuditAdmin(admin.ModelAdmin):
    list_display = ("audit_id", "transaction_id", "old_status", "new_status", "changed_at")
    search_fields = ("transaction_id", "transaction_id",)
    list_filter = ("changed_at",)
    ordering = ("-changed_at",)
    #inlines = [LogEntryInline]

@admin.register(LoanDisbursementLog)
class LoanDisbursementLogAdmin(admin.ModelAdmin):
    list_display = ("log_id", "loan", "formatted_disbursed_amount", "disbursed_by", "disbursed_on", "reversed_on", "action_type")
    search_fields = ("log_id", "loan__loan_id", "disbursed_by__username")
    list_filter = ("action_type", "disbursed_on", "reversed_on")
    ordering = ("-disbursed_on",)
    #inlines = [LogEntryInline]

    def formatted_disbursed_amount(self, obj):
        return format_currency(obj.disbursed_amount)
    formatted_disbursed_amount.short_description = "Disbursed Amount"

# -------------------------
# Salary Tables
# -------------------------
@admin.register(Salaries)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ("salary_id", "employee_id", "formatted_amount", "date_paid", "paid_for_month", "payment_month", "remarks", "payment_status")
    search_fields = ("employee__first_name", "employee__last_name", "paid_for_month",)
    list_filter = ("paid_for_month", )
    ordering = ("-paid_for_month",)
    #inlines = [LogEntryInline]

    def formatted_amount(self, obj):
        return format_currency(obj.amount)
    formatted_amount.short_description = "Amount"

@admin.register(SalaryStructures)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ("structure_id", "employee", "formatted_base_pay", "formatted_allowance", "formatted_deduction", "currency", "effective_date", "created_at", "created_by", "is_active")
    search_fields = ("employee",)
    list_filter = ("employee", "created_at",)
    ordering = ("-created_at",)
    #inlines = [LogEntryInline]

    def formatted_base_pay(self, obj):
        return format_currency(obj.base_pay)
    formatted_base_pay.short_description = "Base Pay"

    def formatted_allowance(self, obj):
        return format_currency(obj.allowance)
    formatted_allowance.short_description = "Allowance"

    def formatted_deduction(self, obj):
        return format_currency(obj.deduction)
    formatted_deduction.short_description = "Deduction"

@admin.register(SalaryStructureHistory)
class SalaryStructureHistoryAdmin(admin.ModelAdmin):
    list_display = ("structure_id", "employee_id", "formatted_base_pay", "formatted_allowance", "formatted_deduction", "currency", "effective_date", "created_at", "created_by")
    search_fields = ("employee_id", "structure__name",)
    list_filter = ("employee_id", "created_at",)
    ordering = ("-created_at",)
    #inlines = [LogEntryInline]

    def formatted_base_pay(self, obj):
        return format_currency(obj.base_pay)
    formatted_base_pay.short_description = "Base Pay"

    def formatted_allowance(self, obj):
        return format_currency(obj.allowance)
    formatted_allowance.short_description = "Allowance"

    def formatted_deduction(self, obj):
        return format_currency(obj.deduction)
    formatted_deduction.short_description = "Deduction"

# --------------------------------------------------------------------------
# DJANGO ADMIN LOG
# --------------------------------------------------------------------------
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action_time",
        "user",
        "content_type",
        "object_link",
        "action_flag_label",
        "change_message_pretty",
    )
    list_filter = ("action_flag", "action_time", "user", "content_type")
    search_fields = ("object_repr", "change_message")
    ordering = ("-action_time",)

    def action_flag_label(self, obj):
        flag_map = {1: "Add", 2: "Change", 3: "Delete"}
        return flag_map.get(obj.action_flag, obj.action_flag)
    action_flag_label.short_description = _("Action")

    def object_link(self, obj):
        """
        Return a link to the admin page of the object if it still exists.
        """
        if obj.content_type and obj.object_id:
            try:
                url = reverse(
                    f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                    args=[obj.object_id],
                )
                return format_html('<a href="{}">{}</a>', url, obj.object_repr)
            except Exception:
                # In case the object was deleted or URL reversing fails
                return obj.object_repr
        return obj.object_repr
    object_link.short_description = _("Object")

    def change_message_pretty(self, obj):
        return format_html("<pre>{}</pre>", obj.change_message)
    change_message_pretty.short_description = _("Change Message")

# NOTE: RolePermissions skipped due to composite PK incompatibility.

