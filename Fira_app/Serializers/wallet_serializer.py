from rest_framework import serializers
from ..models import Resource, Wallet, Currency, Transaction, Employee, TransactionAdditionalReceipt
from .resource_serializer import UserSerializer,TaskSerializer, ResourceSerializer

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'title',]

class WalletSerializer(serializers.ModelSerializer):
    currency = CurrencySerializer(required=True)
    class Meta:
        model = Wallet
        fields = ['id', 'currency', 'name', ]

class ShortTransactionSerializer(serializers.ModelSerializer):
    wallet = WalletSerializer(required=True)
    class Meta:
        model = Transaction
        fields = ['id','amount', 'wallet',]

class TransactionAdditionalReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionAdditionalReceipt
        fields = ['id', 'receipt_file',]

class TransactionSerializer(serializers.ModelSerializer):
    creator = UserSerializer(required=True)
    wallet = WalletSerializer(required=True)
    dest_resource = ResourceSerializer()
    source_transaction = ShortTransactionSerializer()
    dest_transaction = ShortTransactionSerializer()
    payoff_wallet = WalletSerializer(required=True)
    additional_receipts = TransactionAdditionalReceiptSerializer(many= True)
    class Meta:
        model = Transaction
        fields = ['id','amount','amount_dollar','time', 'incordec', 'wallet', 'wallet_balance_after', 'fee','fee_dollar','receipt_file','dest_resource','source_transaction','dest_transaction','comment','creator','created', 'updated','title','payoff_wallet','additional_receipts',]
