from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from .models import Task_Level,Task_Type,Task,Employee,Task_Type_Property,Organization_Group,PublicTask,\
    ResourcePropertyNum,ResourcePropertyText, ResourcePropertyDate,ResourcePropertyFile,ResourcePropertyBool,\
        Resource,ResourceType,ResourceTypeProperty,ResourceTypeRelation, Task_Type_Auto_Request, \
            Task_Type_Verification , QualityParameter, SystemPublicSetting,ResourceTypeCreationLimit, \
                DailyPerformanceReport, MonthlyPerformanceReport, AutoEvaluationCriteria , EvaluationCriteriaGroup, \
                    EvaluationCriteria , EvaluationNote, EvaluationConsquenseType, EvaluationCriteriaGroupWeight,\
                        ActivePluginSetting, Currency, Wallet, Transaction, FeedbackType, Regulation, \
                            SyntheticEvaluationCriteria, PayOff, OPArea, OPProject, ConsumingResource, Task_Type_State

admin.site.register(Task_Level)

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('UserInfo', 'personelnumber','PreMonthQuility','QuilityCreated','QuilityUpdated',)

admin.site.register(Employee,EmployeeAdmin)
admin.site.register(Organization_Group)
admin.site.register(SystemPublicSetting)
#admin.site.register(PublicTask)

class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug')

admin.site.register(ResourceType, ResourceTypeAdmin)

class ResourceTypeCreationLimitAdmin(admin.ModelAdmin):
    list_display = ('resource_type', 'user')

admin.site.register(ResourceTypeCreationLimit, ResourceTypeCreationLimitAdmin)

class ResourceTypePropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'resource_type', 'order', 'value_type', 'slug')

admin.site.register(ResourceTypeProperty, ResourceTypePropertyAdmin)

class ResourceTypeRelationAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'source_resource_type', 'destinaton_resource_type', 'slug')

admin.site.register(ResourceTypeRelation, ResourceTypeRelationAdmin)

class Task_Type_Admin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'public', 'deleted', 'auto_request', 'froce_assign_request', 'needs_verfication')

admin.site.register(Task_Type, Task_Type_Admin)

class Task_Type_Property_Admin(admin.ModelAdmin):
    list_display = ('task_type', 'name','slug', 'value_type', 'order', 'deleted')

admin.site.register(Task_Type_Property,Task_Type_Property_Admin)

class Task_Type_Auto_Request_Admin(admin.ModelAdmin):
    list_display = ('task_type','request_target')

admin.site.register(Task_Type_Auto_Request, Task_Type_Auto_Request_Admin)

class Task_Type_Verification_Admin(admin.ModelAdmin):
    list_display = ('task_type','order','verification_type','verify_by_locumtenens','verification_user')

admin.site.register(Task_Type_Verification, Task_Type_Verification_Admin)


class QualityParameterAdmin(admin.ModelAdmin):
    list_display = ('name','group','weight','description')
    
admin.site.register(QualityParameter, QualityParameterAdmin)

class DailyPerformanceReportAdmin(admin.ModelAdmin):
    list_display = ('solar_date','entry1', 'status', 'user', 'g_date')

    list_filter = ('user','g_date')

    def get_urls(self):
        urls = super().get_urls()
        new_urls = [path('upload-xls/', self.upload_xls),]  
        return new_urls + urls

    def upload_xls(self, request):
        return render(request, "admin/xls_upload.html")     

admin.site.register(DailyPerformanceReport, DailyPerformanceReportAdmin)

class MonthlyPerformanceReportAdmin(admin.ModelAdmin):
    list_display = ('solar_month','solar_year', 'entry_sum_duration', 'presence_duration','performance_duration','leave_hours_duration',\
        'delay_hours_duration','rush_hours_duration','lowtime_duration','overtime_duration','holiday_overtime_duration','month_days','month_holidays', 'user')   

admin.site.register(MonthlyPerformanceReport, MonthlyPerformanceReportAdmin)


class AutoEvaluationCriteriaAdmin(admin.ModelAdmin):
    list_display = ('name','value_type', 'criteria', 'manager_criteria',)   

admin.site.register(AutoEvaluationCriteria, AutoEvaluationCriteriaAdmin)

class EvaluationCriteriaGroupAdmin(admin.ModelAdmin):
    list_display = ('name','managers_special')   

admin.site.register(EvaluationCriteriaGroup, EvaluationCriteriaGroupAdmin)

class EvaluationCriteriaAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'group', 'weight',
     'evaluated_by_headmaster', 'evaluation_by_headmaster_weight', 'evaluation_by_headmaster_nullable',
     'evaluated_by_manager', 'evaluation_by_manager_weight', 'evaluation_by_manager_nullable',
     'evaluated_by_siblings', 'evaluation_by_siblings_weight', 'evaluation_by_siblings_nullable',
     'evaluated_by_subaltern', 'evaluation_by_subaltern_weight', 'evaluation_by_subaltern_nullable',
     'evaluated_by_staff', 'evaluation_by_staff_weight', 'evaluation_by_staff_nullable',
     'evaluated_by_all', 'evaluation_by_all_weight', 'evaluation_by_all_nullable')   

admin.site.register(EvaluationCriteria, EvaluationCriteriaAdmin)

# class EvaluationNoteAdmin(admin.ModelAdmin):
#     list_display = ('note','evaluator', 'evaluatee', 'criteria','month','year','consequence_type','consequence_amount')   

# admin.site.register(EvaluationNote, EvaluationNoteAdmin)

class EvaluationConsquenseTypeAdmin(admin.ModelAdmin):
    list_display = ('name','color_code', 'unimportant')

admin.site.register(EvaluationConsquenseType, EvaluationConsquenseTypeAdmin)

class EvaluationCriteriaGroupWeightAdmin(admin.ModelAdmin):
    list_display = ('criteria_group','org_group', 'weight')

admin.site.register(EvaluationCriteriaGroupWeight, EvaluationCriteriaGroupWeightAdmin)

class ActivePluginSettingAdmin(admin.ModelAdmin):
    list_display = ('pk', 'internet_usage','infrastructure','wallet_manage','task_group','human_capitals','automation','resume')

admin.site.register(ActivePluginSetting, ActivePluginSettingAdmin)

admin.site.register(Currency)

admin.site.register(Wallet)

admin.site.register(PayOff)

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'amount', 'incordec', 'time', 'wallet', 'wallet_balance_after_d', 'live_ratio', 'fee', 'receipt_file', 'dest_resource', 'source_transaction', 'comment','creator',)

admin.site.register(Transaction, TransactionAdmin)

admin.site.register(FeedbackType)

admin.site.register(Regulation)

admin.site.register(SyntheticEvaluationCriteria)

admin.site.register(OPArea)

admin.site.register(OPProject)

admin.site.register(Task_Type_State)