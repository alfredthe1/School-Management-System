from django.contrib import admin
from .models import FeeStructure, Payment, Expenditure, MobileMoneyTransaction

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'academic_year', 'class_room')
    list_filter = ('academic_year', 'class_room')
    search_fields = ('name',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount_paid', 'date_paid', 'receipt_number', 'payment_method')
    list_filter = ('payment_method', 'date_paid')
    search_fields = ('student__first_name', 'student__last_name', 'receipt_number')
    readonly_fields = ('receipt_number',)

@admin.register(Expenditure)
class ExpenditureAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'date', 'category', 'recorded_by')
    list_filter = ('category', 'date')
    search_fields = ('description',)


@admin.register(MobileMoneyTransaction)
class MobileMoneyTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'parent', 'provider', 'amount', 'status',
        'phone_number', 'transaction_reference', 'created_at',
    )
    list_filter = ('status', 'provider', 'created_at')
    search_fields = ('student__student_id', 'transaction_reference', 'reference_id')
    readonly_fields = (
        'reference_id', 'external_id', 'transaction_reference',
        'created_at', 'updated_at',
    )