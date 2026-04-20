from django.urls import path
from django.contrib import admin
from django.contrib.auth import views as auth_views
from banking_system import views
from banking_system.views import account_list, close_account, suspend_account, reactivate_account, freeze_account

urlpatterns = [
    # --------------------
    # Authentication
    # --------------------
    path("login/", views.login_view, name="login"),

    # Logout confirmation page (GET)
    path("logout/", views.logout_confirm, name="logout_confirm"),

    # Actual logout action (POST)
    path("logout/confirm/", views.logout_view, name="logout"),

    # --------------------
    # Dashboard
    # --------------------
    path("customers/dashboard/", views.dashboard_view, name="dashboard"),

    # --------------------
    # Customers
    # --------------------
    path("customers/register/", views.register_customer, name="register_customer"),
    path("customers/list/", views.customer_list, name="customer_list"),
    path("customers/update/<int:customer_id>/", views.update_customer, name="update_customer"),
    path("customers/activate/<int:customer_id>/", views.activate_customer, name="activate_customer"),
    path("customers/deactivate/<int:customer_id>/", views.deactivate_customer, name="deactivate_customer"),

    # --------------------
    # Accounts
    # --------------------
    path("accounts/", account_list, name="account_list"),
    path("accounts/close/<str:account_number>/", close_account, name="close_account"),
    path("accounts/suspend/<str:account_number>/", suspend_account, name="suspend_account"),
    path("accounts/reactivate/<str:account_number>/", reactivate_account, name="reactivate_account"),
    path("accounts/freeze/<str:account_number>/", freeze_account, name="freeze_account"),
    path("accounts/create/", views.create_account, name="create_account"),
    path("accounts/update/<str:account_number>/", views.update_account, name="update_account"),
    path("accounts/<str:account_number>/statement/", views.account_statement, name="account_statement"),
    path("accounts/<str:account_number>/statement/pdf/", views.account_statement_pdf, name="account_statement_pdf"),
    path("deposit/", views.deposit_money, name="deposit_money"),
    path("withdraw/", views.withdraw_money, name="withdraw_money"),
    path("transfer/", views.transfer_money, name="transfer_money"),
    path("reverse/", views.reverse_transaction, name="reverse_transaction"),
    path("history/", views.transaction_history, name="transaction_history"),
    path("transactions/pdf/<str:account_number>/", views.transactions_pdf, name="transactions_pdf"),

]