from django.urls import path

from ..views.wallet import wallet
app_name = 'wallet'
urlpatterns = [
    #---------------------------------------------------------------------
    path('',wallet.index,name='index'),
    path('currency/',wallet.currency,name='currency'),
    path('transaction/<int:ttype>/',wallet.transaction,name='add_transaction'),
    path('transactions/<int:wallet_id>/', wallet.transaction_list, name='transaction_list'),
    path('archive/<int:wallet_id>/', wallet.archive_wallet, name='archive_wallet'),
    path('payoff/',wallet.payoff,name='payoff'),
    path('report/',wallet.report,name='report'),
    path('receipt/add/', wallet.add_receipt,name='add_receipt'),
    path('receipt/remove/<int:receipt_id>/', wallet.remove_receipt,name='remove_receipt'),
    path('payoff/<int:wallet_id>/<int:payoff_final>/',wallet.payoff_save,name='payoff_save'),
    path('payoff/<int:payoff_id>/zip/',wallet.download_payoff_zip,name='payoff_zip'),
    path('payoff/<int:payoff_id>/xlsx/',wallet.download_payoff_excell,name='payoff_xlsx'),
]