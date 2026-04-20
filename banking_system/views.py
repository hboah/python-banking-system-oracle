# banking_system/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm  
from .forms import CustomerForm   
from .models import Customers, Accounts, Transactions     
from banking_system.forms import CustomerForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from . import utils
from django.db import DatabaseError
from .utils import format_currency
import oracledb as cx_Oracle


# ==============================
# SHARED ERROR HANDLER
# ==============================
import re
from django.contrib import messages

def handle_oracle_error(request, e, action_description="perform this action"):
    """
    Handles Oracle DatabaseError gracefully and shows user-friendly messages.
    """
    error_message = str(e)

    if "ORA-20001" in error_message and "Access Denied" in error_message:
        messages.error(request, f"❌ Access Denied: You do not have permission to {action_description}.")
    elif "ORA-" in error_message:
        readable = re.sub(r"ORA-\d+:", "", error_message).strip()
        messages.error(request, f"⚠️ Oracle Error: {readable}")
    else:
        messages.error(request, f"⚠️ Unexpected database error: {error_message}")


# ----------------- MAIN DASHBOARD VIEW
@login_required(login_url="login")
def dashboard_view(request):
    customers_count = Customers.objects.count()
    accounts_count = Accounts.objects.count() 
    transactions_count = Transactions.objects.count() 

    context = {
        "customers_count": customers_count,
        "accounts_count": accounts_count,
        "transactions_count": transactions_count,
    }
    return render(request, "customers/dashboard.html", context)

def login_view(request):
    # If the user is already authenticated, skip login form
    if request.user.is_authenticated:
        # Route based on role
        if request.user.is_superuser:
            return redirect('admin:index')  # Django admin
        elif request.user.is_staff:
            return redirect('dashboard')    # Staff dashboard
        else:
            return redirect('dashboard')    # Normal user dashboard

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                # Setting Oracle session for CBAC
                utils.set_cbac_session(request) #get the current(logged in) user's id for permission checkS

                # Redirect based on role
                if user.is_superuser:
                    return redirect("admin:index")
                elif user.is_staff:
                    return redirect("dashboard")
                else:
                    return redirect("dashboard")
            else:
                messages.error(request, "Invalid username or password")
    else:
        form = LoginForm()

    return render(request, "registration/login.html", {"form": form})


from django.contrib.auth import logout
def logout_confirm(request):
    # Show the confirmation page
    return render(request, "registration/logout_confirm.html")

from django.http import HttpResponseNotAllowed

@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        username = request.user.username
        with connection.cursor() as cursor:
            try:
                cursor.callproc("cbac_user_mgmt_pkg.logout_user", [username])
            except Exception as e:
                messages.warning(request, f"Warning: Oracle logout logging failed: {e}")

    logout(request)  # Django logout
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")


# ======================================================================================

# ------------------------------CUSTOMER VIEWS------------------------------------------

# ======================================================================================

# ================================REGISTER A CUSTOMER===================================
@login_required(login_url="login")
def register_customer(request):
    utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            with connection.cursor() as cursor:
                cursor.callproc("customer_mgmt_pkg.register_customer", [
                    cd["first_name"],
                    cd["last_name"],
                    cd["gender"],
                    cd["date_of_birth"],
                    cd["id_type"],
                    cd["id_number"],
                    cd["email"],
                    cd["phone_number"],
                    cd["address"],
                    cd["role_id"],   # from hidden field
                    cd["status"]     # from hidden field
                ])
            messages.success(request, "✅ Customer registered successfully!")
            return redirect("register_customer")  # refresh page or redirect elsewhere
    else:
        form = CustomerForm()
    return render(request, "customers/register.html", {"form": form})

# -----------------CUSTOMER DASHBOARD
@login_required(login_url="login")
def customer_dashboard(request):
    return render(request, "customers/dashboard.html")

# ================================LIST ALL CUSTOMER===================================
from django.core.paginator import Paginator
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from . import utils

@login_required(login_url="login")
def customer_list(request):
    utils.set_cbac_session(request)  # get the current(logged in) user's id for permission check

    per_page = int(request.GET.get("per_page", 50))
    page_number = request.GET.get("page", 1)
    search_query = request.GET.get("search", "").strip()

    with connection.cursor() as cur:
        base_query = """
            SELECT 
                c.customer_id,
                c.first_name,
                c.last_name,
                c.email,
                c.phone_number,
                CASE 
                    WHEN customer_mgmt_pkg.is_customer_active_raw(c.customer_id) = 1 THEN 'Active'
                    ELSE 'Inactive'
                END AS status
            FROM customers c
        """

        params = {}
        if search_query:
            base_query += """
                WHERE LOWER(c.first_name || ' ' || c.last_name) LIKE LOWER(:search)
                   OR LOWER(c.phone_number) LIKE LOWER(:search)
                   OR LOWER(c.email) LIKE LOWER(:search)
            """
            params["search"] = f"%{search_query}%"

        base_query += " ORDER BY c.customer_id"

        cur.execute(base_query, params)
        rows = cur.fetchall()

        customers = [
            {
                "customer_id": r[0],
                "first_name": r[1],
                "last_name": r[2],
                "email": r[3],
                "phone_number": r[4],
                "status": r[5],
            }
            for r in rows
        ]

    paginator = Paginator(customers, per_page)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "customers/customer_list.html",
        {
            "customers": page_obj,
            "page_obj": page_obj,
            "per_page": per_page,
            "per_page_options": [5, 10, 25, 50, 100],
            "search_query": search_query,  # <-- ensure search text persists
        },
    )

# ================================UPDATE/EDIT CUSTOMER===================================
@login_required(login_url="login")
def update_customer(request, customer_id):
    cursor = connection.cursor()
    utils.set_cbac_session(request) #get the current(logged in) user's id for permission checkS
    # Fetch current customer details for initial form load
    cursor.execute("""
        SELECT customer_id, first_name, last_name, gender, date_of_birth,
               id_type, id_number, email, phone_number, address, role_id, status
        FROM customers WHERE customer_id = :id
    """, {"id": customer_id})
    row = cursor.fetchone()

    if not row:
        connection.close()
        messages.error(request, "Customer not found.")
        return redirect("update_customer", customer_id=customer_id)

    customer_data = {
        "first_name": row[1],
        "last_name": row[2],
        "gender": row[3],
        "date_of_birth": row[4],
        "id_type": row[5],
        "id_number": row[6],
        "email": row[7],
        "phone_number": row[8],
        "address": row[9],
        "role_id": row[10],
        "status": row[11],
    }

    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                # Call the Oracle procedure
                cursor.callproc(
                    "customer_mgmt_pkg.update_customer",
                    [
                        customer_id,
                        data["first_name"],
                        data["last_name"],
                        data["gender"],
                        data["date_of_birth"],
                        data["id_type"],
                        data["id_number"],
                        data["email"],
                        data["phone_number"],
                        data["address"],
                        data["role_id"],
                        data["status"],
                    ]
                )
                connection.commit()
                messages.success(request, "Customer updated successfully.")
                return redirect("customer_list")
            except DatabaseError as e:   # Using Django’s DatabaseError here
                messages.error(request, f"Database error: {e}")
    else:
        form = CustomerForm(initial=customer_data)

    connection.close()
    return render(request, "customers/update_customer.html", {"form": form, "customer_id": customer_id})

# ================================ACTIVATE A CUSTOMER===================================
@login_required(login_url="login")
def activate_customer(request, customer_id):
    utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
    cursor = connection.cursor()
    try:
        cursor.callproc("customer_mgmt_pkg.activate_customer", [customer_id])
        connection.commit()
        messages.success(request, "✅ Customer reactivated successfully.")
    except DatabaseError as e:
        handle_oracle_error(request, e, "activate customers")
    finally:
        request.session.modified = True
    return redirect("customer_list")


# ================================DEACTIVATE A CUSTOMER===================================
@login_required(login_url="login")
def deactivate_customer(request, customer_id):
    utils.set_cbac_session(request) #get the current(logged in) user's id for permission checkS
    try:
        with connection.cursor() as cur:
            cur.callproc("customer_mgmt_pkg.deactivate_customer", [customer_id])
        messages.info(request, "⚠️ Customer deactivated.")
    except DatabaseError as e:
        handle_oracle_error(request, e, "deactivate customers")
    finally:
        request.session.modified = True
    return redirect("customer_list")


# ======================================================================================

# ------------------------------ACCOUNT VIEWS------------------------------------------

# ======================================================================================

# ================================ LIST ALL ACCOUNTS ================================
# Tuesday, 7th OCTOBER, 2025
from django.core.paginator import Paginator

def formatted_amount(self, obj):
        return format_currency(obj.balance)
formatted_amount.short_description = "Balance"

from django.core.paginator import Paginator
from django.db import connection
from django.contrib.auth.decorators import login_required
from . import utils

@login_required(login_url="login")
def account_list(request):
    utils.set_cbac_session(request)
    per_page = int(request.GET.get("per_page", 50))
    page_number = request.GET.get("page", 1)
    search_query = request.GET.get("search", "").strip().lower()

    with connection.cursor() as cur:
        query = """
            SELECT 
                a.account_id,
                a.account_number,
                a.account_type,
                a.balance,
                a.status,
                c.first_name || ' ' || c.last_name AS customer_name,
                b.branch_name
            FROM accounts a
            JOIN customers c ON a.customer_id = c.customer_id
            JOIN branches b ON a.branch_id = b.branch_id
        """
        params = []
        if search_query:
            query += """
                WHERE LOWER(a.account_number) LIKE %s
                   OR LOWER(c.first_name || ' ' || c.last_name) LIKE %s
                   OR LOWER(b.branch_name) LIKE %s
            """
            like_pattern = f"%{search_query}%"
            params = [like_pattern, like_pattern, like_pattern]
        else:
            query += " ORDER BY a.account_id"
            cur.execute(query, params)

        rows = cur.fetchall()

        accounts = [
            {
                "account_id": r[0],
                "account_number": r[1],
                "account_type": r[2],
                "formatted_balance": format_currency(r[3]),
                "status": r[4],
                "customer_name": r[5],
                "branch_name": r[6],
            }
            for r in rows
        ]

    paginator = Paginator(accounts, per_page)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "accounts/account_list.html",
        {
            "accounts": page_obj,
            "page_obj": page_obj,
            "per_page": per_page,
            "per_page_options": [5, 10, 25, 50, 100],
            "search_query": search_query,
        },
    )


# ================================ CREATE ACCOUNT ================================
@login_required(login_url="login")
def create_account(request):
    utils.set_cbac_session(request)
    if request.method == "POST":
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        gender = request.POST["gender"]
        dob = request.POST["date_of_birth"]
        id_type = request.POST["id_type"]
        id_number = request.POST["id_number"]
        email = request.POST["email"]
        phone = request.POST["phone_number"]
        address = request.POST["address"]
        branch_id = request.POST["branch_id"]
        account_type = request.POST["account_type"]
        opening_balance = request.POST.get("opening_balance", 0)

        with connection.cursor() as cur:
            cur.callproc(
                "account_mgmt_pkg.open_account",
                [
                    first_name, last_name, gender, dob,
                    id_type, id_number, email, phone,
                    address, branch_id, account_type,
                    opening_balance,
                ],
            )
        messages.success(request, f"Account for {first_name} {last_name} created successfully.")
        return redirect("account_list")

    # Populate dropdowns (branches, account types etc.)
    with connection.cursor() as cur:
        cur.execute("SELECT branch_id, branch_name FROM branches")
        branches = cur.fetchall()

    return render(request, "accounts/create_account.html", {"branches": branches})


# ================================ UPDATE ACCOUNT ================================
@login_required(login_url="login")
def update_account(request, account_number):
    utils.set_cbac_session(request)
    if request.method == "POST":
        new_type = request.POST["account_type"]
        branch_id = request.POST["branch_id"]

        with connection.cursor() as cur:
            cur.callproc("account_mgmt_pkg.update_customer_account", [account_number, new_type, branch_id])

        messages.success(request, f"Account {account_number} updated successfully.")
        return redirect("account_list")

    # Load account + branches for form
    with connection.cursor() as cur:
        cur.execute("""
            SELECT a.account_number, a.account_type, b.branch_id, b.branch_name
            FROM accounts a
            JOIN branches b ON a.branch_id = b.branch_id
            WHERE a.account_number = :acc
        """, {"acc": account_number})
        account = cur.fetchone()

        cur.execute("SELECT branch_id, branch_name FROM branches")
        branches = cur.fetchall()

    return render(request, "accounts/update_account.html", {"account": account, "branches": branches})

# ===================CHECK ACCOUNT STATEMENT=================================
from django.shortcuts import render
from django.db import connection
from . import utils

def account_statement(request, account_number):
    """
    Fetch transaction history + running balance from account_statement_pkg.
    """
    utils.set_cbac_session(request)
    per_page = int(request.GET.get("per_page", 50))
    page_number = request.GET.get("page", 1)

    transactions = []

    with connection.cursor() as cursor:
        out_cursor = cursor.connection.cursor()
        cursor.callproc("account_statement_pkg.get_account_statement", [account_number, out_cursor])

        for row in out_cursor:
            txn_id = row[0]
            txn_date = row[1]
            txn_type = row[2]
            amount = float(row[3]) if row[3] is not None else 0.0
            source_account = row[4]
            destination_account = row[5]
            description = row[6]
            reversal_of = row[7]
            status = row[8]
            balance_after = float(row[9]) if row[9] is not None else 0.0

            transactions.append({
                "txn_id": txn_id,
                "date": txn_date,
                "type": txn_type,
                "amount": f"{amount:,.2f}",
                "source_account": source_account or "-",
                "destination_account": destination_account or "-",
                "description": description or "-",
                "reversal_of": reversal_of or "-",
                "status": status or "-",
                "balance": f"{balance_after:,.2f}",
            })

    if not transactions:
            messages.warning(request, "No transactions found for this account.")

    paginator = Paginator(transactions, per_page)
    page_obj = paginator.get_page(page_number)

    return render(request, "accounts/account_statement.html", {
        "account_number": account_number,
        "transactions": transactions,
        "transactions": page_obj,
        "page_obj": page_obj,
        "per_page": per_page,
        "per_page_options": [5, 10, 25, 50, 100],
    })

# ========================ACCOUNT STATEMENT PDF===========================
# WITH CUSTOMER DETAILS, BANK LOG AT THE TOP LEFT
# ========================ACCOUNT STATEMENT PDF===========================
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    Table, TableStyle, SimpleDocTemplate,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
from django.db import connection
from . import utils
import datetime
import os

def account_statement_pdf(request, account_number):
    utils.set_cbac_session(request)

    # --- Register Unicode font for ₵ symbol ---
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
    pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))

    styles = getSampleStyleSheet()
    for s in ["Normal", "Title", "Heading3", "Italic"]:
        styles[s].fontName = "DejaVuSans"

    # --- Fetch account details ---
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.first_name || ' ' || c.last_name AS customer_name,
                   a.account_number, a.account_type, b.branch_name, a.balance
            FROM accounts a
            JOIN customers c ON a.customer_id = c.customer_id
            JOIN branches b ON a.branch_id = b.branch_id
            WHERE a.account_number = :acc_number
        """, {"acc_number": account_number})
        acc_info = cursor.fetchone()

    if not acc_info:
        return HttpResponse("Account not found", status=404)

    customer_name, acc_number, acc_type, branch_name, balance = acc_info

    # --- Fetch transactions ---
    transactions = []
    running_balance = 0.0

    with connection.cursor() as cursor:
        out_cursor = cursor.connection.cursor()
        cursor.callproc("account_statement_pkg.get_account_statement", [account_number, out_cursor])

        for row in out_cursor:
            txn_id = row[0]
            txn_date = row[1].strftime("%Y-%m-%d %H:%M") if row[1] else ""
            txn_type = row[2]
            amount = float(row[3]) if row[3] else 0.0
            source_account = row[4]
            destination_account = row[5]
            description = row[6]
            reversal_of = row[7]
            status = row[8]
            balance_after = float(row[9]) if row[9] is not None else 0.0


            if txn_type.lower() == "credit":
                running_balance += amount
                amount_color = colors.green
            elif txn_type.lower() == "debit":
                running_balance -= amount
                amount_color = colors.red
            else:
                amount_color = colors.black

            transactions.append([
                txn_id,
                txn_date,
                txn_type,
                f"₵{amount:,.2f}",
                source_account or "-",
                destination_account or "-",
                description or "-",
                reversal_of or "-",
                status or "-",
                f"₵{balance_after:,.2f}",
                amount_color  # store the color for styling
            ])

    # --- PDF setup ---
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="account_{account_number}_statement.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=40 * mm,
        bottomMargin=20 * mm
    )

    elements = []

    # --- Account Info Section ---
    elements.append(Paragraph("<b>Account Holder Details</b>", styles["Heading3"]))
    info = [
        ["Customer Name:", customer_name],
        ["Account Number:", acc_number],
        ["Account Type:", acc_type],
        ["Branch:", branch_name],
        ["Current Balance:", f"₵{float(balance):,.2f}"],
    ]
    info_table = Table(info, colWidths=[110, 630])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    # --- Transactions Table ---
    headers = [
        "Txn ID", "Date", "Type", "Amount",
        "Source Acc", "Dest Acc", "Description",
        "Reversal Of", "Status", "Balance After"
    ]
    data = [headers] + [t[:-1] for t in transactions]  # exclude color column

    txn_table = Table(data, colWidths=[35, 80, 45, 60, 70, 70, 130, 55, 55, 70])
    txn_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.teal),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    # --- Apply red/green coloring dynamically ---
    for i, txn in enumerate(transactions, start=1):
        amount_color = txn[-1]
        if amount_color in [colors.green, colors.red]:
            txn_style.append(("TEXTCOLOR", (3, i), (3, i), amount_color))  # Amount column
            txn_style.append(("TEXTCOLOR", (-1, i), (-1, i), amount_color))  # Balance After column

    txn_table.setStyle(TableStyle(txn_style))

    elements.append(Paragraph("<b>Transaction History</b>", styles["Heading3"]))
    elements.append(txn_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(
        "This is a system-generated statement. Contact support@bcbank.com for assistance.",
        styles["Italic"]
    ))

    doc.build(elements, onFirstPage=lambda c, d: _on_page(c, d, account_number),
              onLaterPages=lambda c, d: _on_page(c, d, account_number))
    return response


def _on_page(canvas, doc, account_number):
    """
    Adds a repeating teal header, footer, and faint watermark to each page.
    """
    canvas.saveState()
    teal = colors.Color(0, 0.5, 0.5)  # Teal RGB color

    # --- Header background ---
    canvas.setFillColor(teal)
    canvas.rect(0, 195 * mm, 297 * mm, 25 * mm, fill=1, stroke=0)

    # --- Logo (absolute path) ---
    logo_path = os.path.join(settings.BASE_DIR, "banking_system", "static", "images", "bank_logo.png")
    if os.path.exists(logo_path):
        canvas.drawImage(logo_path, 15 * mm, 187 * mm, width=25 * mm, height=25 * mm, mask='auto')

    # --- Header text ---
    canvas.setFillColor(colors.white)
    canvas.setFont("DejaVuSans", 11)
    canvas.drawString(45 * mm, 210 * mm, "BC BANK SYSTEM")
    canvas.setFont("DejaVuSans", 8)
    canvas.drawString(45 * mm, 204 * mm, "123 Finance Street, Accra, Ghana")
    canvas.drawString(45 * mm, 198 * mm, f"Statement for Account: {account_number}")
    canvas.drawRightString(285 * mm, 198 * mm, f"Date: {datetime.datetime.now():%Y-%m-%d %H:%M}")

    # --- Watermark ---
    canvas.saveState()
    canvas.setFont("DejaVuSans", 70)
    canvas.setFillColorRGB(0.8, 0.8, 0.8, alpha=0.2)
    canvas.translate(150 * mm, 100 * mm)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "BC BANK SYSTEM")
    canvas.restoreState()

    # --- Footer ---
    canvas.setFillColor(colors.black)
    canvas.setFont("DejaVuSans", 8)
    canvas.line(15 * mm, 15 * mm, 285 * mm, 15 * mm)
    canvas.drawString(15 * mm, 10 * mm, "Confidential — For account holder use only.")
    canvas.drawRightString(285 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")

    canvas.restoreState()


# ================================ ACCOUNT ACTIONS ================================
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.db import connection
from . import utils

@login_required(login_url="login")
def close_account(request, account_number):
    utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
    try:
        with connection.cursor() as cur:
            cur.callproc("account_mgmt_pkg.close_account", [account_number])
        messages.success(request, f"✅Account {account_number} closed successfully.", extra_tags="account")
    except DatabaseError as e:
        handle_oracle_error(request, e, "close accounts")
    finally:
        request.session.modified = True
    return redirect("account_list")


@login_required(login_url="login")
def suspend_account(request, account_number):
    utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
    try:
        with connection.cursor() as cur:
            cur.callproc("account_mgmt_pkg.suspend_account", [account_number])
        messages.warning(request, f"⚠️Account {account_number} suspended.", extra_tags="account")
    except DatabaseError as e:
        handle_oracle_error(request, e, "suspend accounts")
    finally:
        request.session.modified = True
    return redirect("account_list")


@login_required(login_url="login")
def reactivate_account(request, account_number):
    utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
    try:
        with connection.cursor() as cur:
            cur.callproc("account_mgmt_pkg.reactivate_account", [account_number])
        messages.success(request, f"✅Account {account_number} reactivated.", extra_tags="account")
    except DatabaseError as e:
        handle_oracle_error(request, e, "reactivate accounts")
    finally:
        request.session.modified = True
    return redirect("account_list")


@login_required(login_url="login")
def freeze_account(request, account_number):
    utils.set_cbac_session(request) #get the current(logged in) user's id for permission check
    try:
        with connection.cursor() as cur:
            cur.callproc("account_mgmt_pkg.freeze_customer_account", [account_number])
        messages.warning(request, f"⚠️Account {account_number} frozen.", extra_tags="account")
    except DatabaseError as e:
        handle_oracle_error(request, e, "freeze accounts")
    finally:
        request.session.modified = True
    return redirect("account_list")


# ======================================================================================
# ------------------------------TRANSACTIONS VIEWS--------------------------------------
# ======================================================================================

from .forms import DepositForm, WithdrawForm, TransferForm, ReverseTransactionForm, TransactionHistoryForm
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import DatabaseError
from . import utils


# ============================== DEPOSIT MONEY ==============================
@login_required(login_url="login")
def deposit_money(request):
    utils.set_cbac_session(request)
    form = DepositForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            with connection.cursor() as cursor:
                cursor.callproc("transactions_mgmt_pkg.deposit_money", [
                    data["account_number"],
                    data["amount"],
                    data["description"]
                ])
            messages.success(request, f"✅ Deposit successful for account {data['account_number']}")
            return redirect("transaction_history")

        except DatabaseError as e:
            messages.error(request, f"⚠️ Database Error: {e}")

    return render(request, "transactions/deposit_money.html", {"form": form})


# ============================== WITHDRAW MONEY ==============================
@login_required(login_url="login")
def withdraw_money(request):
    utils.set_cbac_session(request)
    form = WithdrawForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            with connection.cursor() as cursor:
                cursor.callproc("transactions_mgmt_pkg.withdraw_money", [
                    data["account_number"],
                    data["amount"],
                    data["description"]
                ])
            messages.success(request, "💸 Withdrawal successful.")
            return redirect("transaction_history")

        except DatabaseError as e:
            messages.error(request, f"⚠️ Database Error: {e}")

    return render(request, "transactions/withdraw_money.html", {"form": form})


# ============================== TRANSFER MONEY ==============================
@login_required(login_url="login")
def transfer_money(request):
    utils.set_cbac_session(request)
    form = TransferForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            with connection.cursor() as cursor:
                cursor.callproc("transactions_mgmt_pkg.transfer_money", [
                    data["sender_account_number"],
                    data["receiver_account_number"],
                    data["amount"],
                    data["description"]
                ])
            messages.success(request, "🔁 Transfer successful.")
            return redirect("transaction_history")

        except DatabaseError as e:
            messages.error(request, f"⚠️ Database Error: {e}")

    return render(request, "transactions/transfer_money.html", {"form": form})


# ============================== REVERSE TRANSACTION ==============================
@login_required(login_url="login")
def reverse_transaction(request):
    utils.set_cbac_session(request)
    form = ReverseTransactionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            with connection.cursor() as cursor:
                cursor.callproc("transactions_mgmt_pkg.reverse_transaction", [
                    data["transaction_id"],
                    data["description"]
                ])
            messages.success(request, "🔄 Transaction reversed successfully.")
            return redirect("transaction_history")

        except DatabaseError as e:
            messages.error(request, f"⚠️ Database Error: {e}")

    return render(request, "transactions/reverse_transaction.html", {"form": form})


# ============================== VIEW TRANSACTION HISTORY ==============================
from django.core.paginator import Paginator
from django.db import connection, DatabaseError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.dateformat import format
from django.shortcuts import render
from . import utils
from .forms import TransactionHistoryForm


def format_currency(value):
    try:
        value = float(value)
        return f"₵{value:,.2f}"
    except (ValueError, TypeError):
        return value

import json
@login_required(login_url="login")
def transaction_history(request):
    utils.set_cbac_session(request)
    per_page = int(request.GET.get("per_page", 50))
    page_number = request.GET.get("page", 1)
    form = TransactionHistoryForm(request.GET or None)
    transactions = []
    columns = []

    if form.is_valid():
        data = form.cleaned_data
        try:
            conn = connection.connection
            if conn is None:
                connection.ensure_connection()
                conn = connection.connection

            cursor = conn.cursor()
            out_cursor = conn.cursor()

            cursor.callproc(
                "transactions_mgmt_pkg.view_transaction_history",
                [
                    data["account_number"],
                    data.get("start_date"),
                    data.get("end_date"),
                    data.get("transaction_type"),
                    data.get("status"),
                    out_cursor,
                ],
            )
            
            transactions = out_cursor.fetchall()
            columns = [col[0] for col in out_cursor.description]

            transactions = [
                {
                    **{
                        col: (
                            format_currency(val)
                            if col.lower() == "amount"
                            else (
                                format(val, "M d, Y, g:i a")
                                if hasattr(val, "strftime")
                                else val
                            )
                        )
                        for col, val in zip(columns, row)
                    },
                }
                for row in transactions
            ]

        except DatabaseError as e:
            messages.error(request, f"⚠️ Database Error: {e}")
        finally:
            try:
                cursor.close()
                out_cursor.close()
            except Exception:
                pass

    paginator = Paginator(transactions, per_page)
    page_obj = paginator.get_page(page_number)
    
    chart_data = []

    for row in transactions:
        try:
            date = row.get("TRANSACTION_DATE")
            balance_raw = row.get("BALANCE_AFTER")
            account = row.get("ACCOUNT_NUMBER")

            if date and balance_raw is not None and account:
                if hasattr(date, "strftime"):
                    date = date.strftime("%Y-%m-%d")

                chart_data.append({
                    "date": date,
                    "balance": float(balance_raw),
                    "account": account
                })
        except Exception as e:
            print("Chart data error:", e)

    chart_data_json = json.dumps(chart_data)

    return render(
        request,
        "transactions/transaction_history.html",
        {
            "form": form,
            "transactions": page_obj,
            "columns": columns,
            "page_obj": page_obj,
            "per_page": per_page,
            "per_page_options": [5, 10, 25, 50, 100],
            "chart_data_json": chart_data_json,

        },
    )
    

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io

@login_required(login_url='login')
def transactions_pdf(request, account_number):
    """Generate transaction history as a downloadable PDF."""
    with connection.cursor() as cursor:
        out_cursor = cursor.connection.cursor()
        cursor.callproc("account_statement_pkg.get_account_statement", [account_number, out_cursor])

        # Header
        data = [("Txn ID", "Date", "Type", "Amount", "Description", "Status")]

        for row in out_cursor:
            # Convert row to list (flexible for unknown column count)
            row = list(row)
            # Safely extract known columns by index
            txn_id = row[0]
            txn_date = row[1]
            txn_type = row[2]
            amount = row[3]
            description = row[7] if len(row) > 7 else "-"
            status = row[-1]  # last column, usually status

            # Add to table
            data.append((
                txn_id,
                txn_date.strftime("%Y-%m-%d %H:%M") if txn_date else "",
                txn_type,
                f"₵{amount:,.2f}" if amount else "₵0.00",
                description or "-",
                status or "-"
            ))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>Transaction Statement</b>", styles['Heading2']))
    elements.append(Paragraph(f"Account Number: {account_number}", styles['Normal']))
    elements.append(Spacer(1, 12))

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#22758e")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BACKGROUND", (0,1), (-1,-1), colors.beige),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey])
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf")



