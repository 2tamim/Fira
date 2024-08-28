from django.db.models import Q, Sum
from django.db import models,transaction
from django.contrib.auth.models import User, Permission
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from .fields import OrderField
from ckeditor_uploader.fields import RichTextUploadingField
from .utilities.date_tools import ConvertToSolarDate,GetSolarDateNow, ConvertTimeDeltaToStringTime
from .utilities.functions import cube
from datetime import datetime
import datetime,hashlib
from taggit.managers import TaggableManager
from pytz import timezone
from jdatetime import datetime as jdt
from math import ceil

#---------------------Methods--------------------#
def user_directory_path(instance, filename):
    _datetime=str(datetime.datetime.now())
    _filename=hashlib.sha256(_datetime.encode()).hexdigest()
    # file will be uploaded to MEDIA_ROOT / user_<id>/<filename>
    return 'users/images/user_{0}/{1}'.format(instance.user.id, _filename)

def user_file_directory_path(instance, filename):
    _datetime=str(datetime.datetime.now())
    _filename=hashlib.sha256(_datetime.encode()).hexdigest()
    # file will be uploaded to MEDIA_ROOT / user_<id>/<filename>
    return 'users/files/user_{0}/{1}'.format(instance.user.id, _filename)

def user_receipt_directory_path(instance, filename):
    _datetime=str(datetime.datetime.now())
    _filename=hashlib.sha256(_datetime.encode()).hexdigest()
    # file will be uploaded to MEDIA_ROOT / user_<id>/<filename>
    return 'users/receipts/user_{0}/{1}'.format(instance.creator.id, _filename)

def task_property_file_directory_path(instance, filename):
    _datetime=str(datetime.datetime.now())
    _filename=hashlib.sha256(_datetime.encode()).hexdigest()
    # file will be uploaded to MEDIA_ROOT / user_<id>/<filename>
    return 'users/files/property/{0}'.format(_filename)
#-----------------End-Methods--------------------#

#---------------------Classes--------------------#
class ActivePluginSetting(models.Model):
    internet_usage = models.BooleanField(default = True, null= False, blank= False, verbose_name = u'اینترنت مصرفی')
    infrastructure = models.BooleanField(default = True, null = False, blank = False, verbose_name = u'زیرساخت')
    wallet_manage = models.BooleanField(default = True, null = False, blank = False, verbose_name = u'کارت و کیف پول')
    task_group = models.BooleanField(default = True, null = False, blank = False, verbose_name = u'کار گروه')
    human_capitals = models.BooleanField(default = True, null = False, blank = False, verbose_name = u'عملکرد حرفه ای')
    automation = models.BooleanField(default = True, null = False, blank = False, verbose_name = u'درخواست ها')
    resume = models.BooleanField(default = True, null = False, blank = False, verbose_name = u'رزومه')
    regulation = models.BooleanField(default = True, null = False, blank = False, verbose_name = u'آیین نامه ها')
    month_report = models.BooleanField(default = True, null = False, blank = False, verbose_name = u'گزارش جامع')
    

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='active_plugin_settings'
        verbose_name = u'بخش های فعال سامانه'
        verbose_name_plural = u'تنظیم بخش های فعال سامانه'

    def __str__(self):
        return str(self.pk)


class DashboardCategory(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    column = models.SmallIntegerField(null=True,default=1)
    order = OrderField(null=True,blank=True, for_fields=['user','column',])
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        db_table='dashboard_category'


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        (1, _('Message')),
        (2, _('Event')),
        (3, _('Mention')),
        (4, _('Global')),
    ]
    user=models.ForeignKey(User,related_name='notifications',on_delete=models.CASCADE)
    title=models.CharField(max_length=100,null=True)
    link = models.TextField(blank = True)
    messages = models.TextField(blank = True)
    closed = models.BooleanField(default=False)
    displaytime = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    notif_type = models.PositiveSmallIntegerField(choices = NOTIFICATION_TYPES, default = 2)
    seen = models.BooleanField(default=0)
    class Meta:
        ordering = ('displaytime',)
        db_table='notification'



class SystemSetting(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE, related_name='setting')
    notification_for_report=models.BooleanField(default=False)
    notification_for_confirm_report=models.BooleanField(default=False)
    notification_for_task_times=models.BooleanField(default=False)
    theme_color = models.SmallIntegerField(default=0, blank= False , null= False)
    dark_mode = models.BooleanField(default= False, blank= False, null= False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        db_table='system_setting'
    

class SystemPublicSetting(models.Model):
    writing_reports_limit_days = models.IntegerField(default=3,verbose_name=u'مهلت ثبت گزارش عادی(روز)')
    writing_telework_reports_limit_days = models.IntegerField(default=14,verbose_name=u'مهلت ثبت گزارش دورکاری(روز)')
    accepting_reports_limit_days = models.IntegerField(default=3,verbose_name=u'مهلت تایید گزارش توسط مدیر(روز)')
    no_locumtenens_accepting_reports_limit_days = models.IntegerField(default=10,verbose_name=u'مهلت تایید گزارش توسط مدیر فاقد جانشین')
    class Meta:
        db_table = 'system_public_setting'
        verbose_name = u'تنظیمات همگانی سیستم'
        verbose_name_plural = u'تنظیمات همگانی سیستم'

#########################################                 Task                ###########################################
class Task_Level(models.Model):
    name=models.CharField(max_length=100,db_index=True, unique=True)
    index = models.SmallIntegerField(null=True)
    description = models.TextField(blank = True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('index',)
        db_table='task_level'
        verbose_name = u"سطح کار"
        verbose_name_plural = u"سطوح کار"
    def __str__(self):
        return self.name

    @cached_property
    def levelColor(self):
        try:
            color ='0'
            if self.index:
                color = str(int(self.index*60/100)+170)
            return "hsl(" + color +",100%,40%)"
        except :
            return "hsl(100,100%,40%)"


class ResourceType(models.Model):
    name=models.CharField(null=True,max_length=100, verbose_name=u'نام')
    description = models.TextField(blank = True, verbose_name=u'توضیحات')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    creation_limits = models.ManyToManyField(User,through='ResourceTypeCreationLimit',symmetrical=False,through_fields=('resource_type','user'),related_name='creatable_res_types')
    ###############################################
    _consuming=1
    _hardware=2
    _software=3
    value_choices=(
        (_consuming,'مصرفی'),
        (_hardware,'سخت افزار'),
        (_software,'نرم افزار'),
    )
    category=models.SmallIntegerField(choices=value_choices,null=True, verbose_name=u'دسته')
    # 1-consuming resource
    # 2-hardware Resource
    # 3 software resource

    slug = models.SlugField(null=True)

    @cached_property
    def color(self):
        return "hsla("+str(int(hashlib.sha1(self.name.encode('utf8')).hexdigest()[:6] , 16)%300)+",40%,45%,1)"


    class Meta:
        ordering = ('name',)
        db_table='resource_type'
        verbose_name = u"نوع منبع"
        verbose_name_plural = u"انواع منبع"
    def __str__(self):
        return str(self.name)


class Task_Type(models.Model):
    name=models.CharField(max_length=100,db_index=True, unique=True, verbose_name=u'عنوان')
    creator=models.ForeignKey(User,blank  = True,null=True,related_name='task_types_created',on_delete=models.PROTECT, verbose_name=u'ایجاد کننده')
    public = models.BooleanField(default=True, verbose_name=u'عمومی یا اختصاصی')
    deleted = models.BooleanField(default=False)
    description = models.TextField(blank = True, verbose_name=u'توضیحات')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    is_request = models.BooleanField(default=False,verbose_name=u'درخواست')
    auto_request = models.BooleanField(default=False,verbose_name=u'فعال کردن ارسال خودکار درخواست')
    froce_assign_request = models.BooleanField(default=False,verbose_name=u'پذیرش خودکار درخواست توسط شخص مورد درخواست')
    needs_verfication = models.BooleanField(default=False,verbose_name='نیازمند تایید قبل از نمایش درخواست')
    resource_type=models.ForeignKey(ResourceType,blank  = True,null=True,related_name='task_resource_type',on_delete=models.PROTECT, verbose_name=u'نوع منبع')
    class Meta:
        ordering = ('name',)
        db_table='task_type'
        verbose_name = u"نوع کار"
        verbose_name_plural = u"انواع کار"
    def __str__(self):
        return self.name


class Task_Type_Auto_Request(models.Model):
    task_type = models.ForeignKey(Task_Type,blank=False,null=False,related_name='auto_requests',on_delete=models.CASCADE, verbose_name=u'نوع کار')
    request_target = models.ForeignKey(User, blank = False, null = False, related_name = 'comming_auto_requests', on_delete=models.CASCADE, verbose_name=u'کاربر مورد درخواست')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('task_type',)
        db_table='task_type_auto_request'
        verbose_name = u"درخواست خودکار نوع کار"
        verbose_name_plural = u"درخواست های خودکار انواع کار"
    def __str__(self):
        return str(self.task_type)+str(self.request_target)


class Task_Type_Verification(models.Model):
    task_type = models.ForeignKey(Task_Type,blank=False,null=False,related_name='verifications',on_delete=models.CASCADE, verbose_name=u'نوع کار')
    order = OrderField(null = True, blank = True,  for_fields=['task_type',],verbose_name=u'ترتیب تایید')
    verification_type_values = (
        (1,'مدیر گروه شخص درخواست دهنده'),
        (2,'مدیر کل'),
        (3,'کاربر خاص'),
    )
    verification_type = models.SmallIntegerField(choices=verification_type_values,null=True, verbose_name=u'نوع تایید')
    verify_by_locumtenens = models.BooleanField(default= True, verbose_name=u'قابل تایید توسط جانشین')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    verification_user = models.ForeignKey(User, blank = True, null = True, related_name = 'task_type_verification', on_delete=models.CASCADE,verbose_name=u'کاربر تایید کننده(در صورت انتخاب نوع تایید کاربر خاص)')
    class Meta:
        ordering=('task_type',)
        db_table = 'task_type_verification'
        verbose_name = u"تعریف تاییدیه نوع کار"
        verbose_name_plural = u"تعریف تاییدیه های انواع کار"
    def __str__(self):
        return str(self.task_type)+str(self.order)


class Task_Type_State(models.Model):
    task_type = models.ForeignKey(Task_Type, on_delete=models.CASCADE, related_name="states" , verbose_name=u"نوع کار")
    name = models.CharField(max_length=60, verbose_name=u"عنوان وضعیت")
    initial = models.BooleanField(default=False, verbose_name="وضعیت آغازین")
    possible_previous_states = models.ManyToManyField('self', blank=True, related_name="possible_next_states", verbose_name=u"حالت های پیشین ممکن")

    class Meta:
        ordering = ('name',)
        db_table='task_type_state'
        verbose_name = u"وضعیت نوع کار"
        verbose_name_plural = u"وضعیت های انواع کار"
    def __str__(self):
        return self.name


class Organization_Group(models.Model):
    name=models.CharField(max_length=100,db_index=True, unique=True, verbose_name=u'نام')
    group_parent=models.ForeignKey('self',blank  = True, null=True,on_delete=models.PROTECT, verbose_name=u'گروه مافوق')
    manager=models.ForeignKey(User,blank  = True,null=True,related_name='managing_organization_groups',on_delete=models.SET_NULL, verbose_name=u'مدیر')
    locumtenens=models.ForeignKey(User,blank  = True,null=True,related_name='locumtenens_organization_groups',on_delete=models.SET_NULL, verbose_name=u'جانشین گروه')
    locumtenens_active = models.BooleanField(default = False, verbose_name=u'فعال بودن دسترسی های جانشنین')
    description = models.TextField(blank = True,null=True, verbose_name=u'توضیحات')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('name',)
        db_table='organization_group'
        verbose_name = u"گروه سازمانی"
        verbose_name_plural = u"چارت سازمانی"
    def __str__(self):
        return self.name

    @cached_property
    def GetGroupMembersId(self):
        user_list=[]
        #_children=Employee.objects.filter(organization_group=self).exclude(user=self.manager)
        _children=Employee.objects.filter(organization_group=self)
        for u in _children:
            user_list.append(u.user.id)

        _sub_manager=Organization_Group.objects.filter(group_parent=self)
        for u in _sub_manager:
            user_list.append(u.manager.id)
        return user_list


class Task_Group(models.Model):
    name=models.CharField(max_length=100,db_index=True, unique=True)
    creator=models.ForeignKey(User,blank  = True,null=True,related_name='task_groups_creator',on_delete=models.PROTECT)
    head=models.ForeignKey(User,blank  = True,null=True,related_name='task_groups_head',on_delete=models.SET_NULL)
    head_notification=models.ForeignKey(Notification,blank  = True,null=True,related_name='head_task_group_notification',on_delete=models.SET_NULL)
    cancelled = models.BooleanField(default=False)
    autocancel = models.BooleanField(default=False)
    public = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    members =models.ManyToManyField(User,through='Task_Group_Member',through_fields=('group','user'),related_name='task_groups',)
    class Meta:
        ordering = ('name',)
        db_table='task_group'
    def __str__(self):
        return self.name
    @property
    def head_name(self):
        return self.head.first_name+" "+self.head.last_name
    @property
    def creator_name(self):
        return self.creator.first_name+" "+self.creator.last_name


class Task_Group_Member(models.Model):
    user = models.ForeignKey(User,blank  = True,null=True,on_delete=models.CASCADE)
    group = models.ForeignKey(Task_Group,blank  = True,null=True,on_delete=models.CASCADE)
    member_notification=models.ForeignKey(Notification,blank  = True,null=True,related_name='member_task_group_notification',on_delete=models.SET_NULL)
    class Meta:
        ordering = ('user__last_name',)
        db_table='task_group_member'
        unique_together = ('user', 'group',)


class QualityParameter(models.Model):
    name = models.CharField(max_length=100,db_index=True, verbose_name=u'عنوان')
    group = models.ForeignKey(Organization_Group,blank  = True,null=True,related_name='quality_parameter_created',on_delete=models.PROTECT, verbose_name=u'گروه')
    weight = models.SmallIntegerField(null=True,default=1 , verbose_name=u'وزن' )
    description = models.TextField(blank = True, verbose_name=u'توضیحات')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('name',)
        db_table='quality_parameter'
        verbose_name = u"پارامتر کیفیت"
        verbose_name_plural = u"پارامترهای کیفیت"
    def __str__(self):
        return self.name


class QualityOfEmployee(models.Model):
    user = models.ForeignKey(User,blank  = True,null=True,on_delete=models.CASCADE)
    parameter = models.ForeignKey(QualityParameter,blank  = True,null=True,on_delete=models.CASCADE )
    value = models.SmallIntegerField(null=True,default=0)
    month = models.SmallIntegerField(null=True)
    year = models.SmallIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        db_table='quality_of_employee'
        ordering = ('year','month',)
        verbose_name = u'حق کیفیت کارمندان'
        verbose_name_plural =u'حق کیفیت کارمندان'
    def __str__(self):
        return self.user 


class Employee(models.Model):
    # last_login = models.DateTimeField(auto_now=True)
    avatar = models.FileField(upload_to = user_directory_path,blank=True, verbose_name=u"تصویر کاربری")
    user = models.OneToOneField(User, on_delete=models.PROTECT, verbose_name=u"حساب کاربری")
    work_title = models.CharField(blank=True,null=True,max_length=100, verbose_name=u"عنوان شغلی")
    personelnumber = models.CharField(blank=True,null=True,max_length=10, verbose_name=u"شماره پرسنلی قدیم")
    new_personelnumber = models.CharField(blank=True,null=True,max_length=15, verbose_name=u"شماره پرسنلی جدید")
    organization_group = models.ForeignKey(Organization_Group,blank  = True,null=True,related_name='employees',on_delete=models.SET_NULL, verbose_name=u"تیم")
    # org_parent int
    #org_roll smallint
    #passrecovery_link varchar
    employee_type = models.SmallIntegerField(blank=True,null=True)
    ####report_type:
    # 1 = official  
    # 2 = contractual
    # 3 = soldier
    live_status = models.SmallIntegerField(blank=True,null=True)
    current_location = models.CharField(blank=True,null=True,max_length=100)
    current_location_public = models.BooleanField(blank=True,default=False)
    #managing_org_group int
    panel = models.SmallIntegerField(blank=True,null=True)
    # for human resource management
    in_staff_group = models.BooleanField(default=False , null = True, verbose_name=u"دسترسی ستاد")
    max_cache_reward = models.IntegerField(blank=True,null=True)
    has_change_in_human_capitals = models.BooleanField(default=False , null = False)
    created = models.DateTimeField(blank=True,null=True,auto_now_add=True)
    updated = models.DateTimeField(blank=True,null=True,auto_now=True)
    class Meta:
        ordering = ('user__last_name',)
        db_table ='employee'
    def __str__(self):
        return self.user.first_name +' , '+self.user.last_name + ' - ' +self.user.username

    @cached_property
    def parent(self):
        try:
            if (self.organization_group.manager.id == self.user.id) and not (self.organization_group.group_parent is None):
                return self.organization_group.group_parent.manager
            else:
                if self.organization_group.manager.id !=self.user.id:
                    return self.organization_group.manager
                else:
                    return None
        except:
            return None

    @cached_property
    def parents(self):
        parent_set=set()
        try:
            if (self.organization_group==None):
                return parent_set
            group=self.organization_group
            if (group.manager==None):
                return parent_set

            while(group.manager):
                parent_set.add(group.manager.id)
                if group.group_parent:
                    group=Organization_Group.objects.get(pk=group.group_parent.id)
                else:
                    break
            return parent_set
        except:
            return parent_set

    @cached_property
    def direct_children_user_id(self):
        children_user_id_set=set()
        if (self.organization_group.manager.id != self.user.id):
            return children_user_id_set
        for _organization_group in Organization_Group.objects.filter(group_parent=self.organization_group):
            children_user_id_set.add(_organization_group.manager.id)

        for employee in Employee.objects.filter(organization_group=self.organization_group).exclude(pk=self.pk).order_by("user__last_name"):
            children_user_id_set.add(employee.user.id)
        return children_user_id_set

    @cached_property
    def all_children_user_id(self):
        children_user_id_set=set()
        if (self.organization_group.manager.id != self.user.id):
            return children_user_id_set
        temp_organization_group_set=set()
        for _organization_group in Organization_Group.objects.filter(group_parent=self.organization_group):
            temp_organization_group_set.add(_organization_group.id)

        for employee in Employee.objects.filter(organization_group=self.organization_group).exclude(pk=self.pk).order_by("user__last_name"):
            children_user_id_set.add(employee.user.id)
        
        try:
            while(len(temp_organization_group_set)>0):
                item=temp_organization_group_set.pop()
                for _organization_group in Organization_Group.objects.filter(group_parent__id=item):
                    temp_organization_group_set.add(_organization_group.id)
                for employee in Employee.objects.filter(organization_group__id=item).exclude(pk=self.pk).order_by("user__last_name"):
                    children_user_id_set.add(employee.user.id)
        except:
            pass 
        return children_user_id_set

    @cached_property
    def is_manager(self):
        if (self.organization_group.manager.id == self.user.id):
            return True
        else:
            return False

    @cached_property
    def global_notification_permission(self):
        has_access = False
        if Permission.objects.filter(codename = 'add_notification').count() > 0:
            notif_perm_users = Permission.objects.filter(codename = 'add_notification')[0].user_set.all().values_list('pk', flat = True)
            for user_pk in notif_perm_users:
                if user_pk == self.user.pk:
                    has_access = True
                    break
        
        return has_access

    @property
    def UserInfo(self):
        return self.user.first_name +' , '+self.user.last_name + ' - ' +self.user.username

    @property
    def PreMonthQuility(self):
        year=int(GetSolarDateNow().split('/')[0])
        month=int(GetSolarDateNow().split('/')[1])-1
        if month<1:
            month=12
            year=year-1
        sumvalue=0
        sumweight=0
        q=0
        quility=QualityOfEmployee.objects.filter(user=self.user,year=year,month=month)
        for qoe in quility:
            sumvalue+=qoe.value*qoe.parameter.weight
            sumweight+=qoe.parameter.weight
        if sumvalue>0 and sumweight>0:
            q=ceil(sumvalue/sumweight)
        return q
    @property
    def QuilityCreated(self):
        year=int(GetSolarDateNow().split('/')[0])
        month=int(GetSolarDateNow().split('/')[1])-1
        if month<1:
            month=12
            year=year-1
        
        quility=QualityOfEmployee.objects.filter(user=self.user,year=year,month=month).order_by('-created').first()
        if quility and quility.created:
            return quility.created
        else:
            return ''
    @property
    def QuilityUpdated(self):
        year=int(GetSolarDateNow().split('/')[0])
        month=int(GetSolarDateNow().split('/')[1])-1
        if month<1:
            month=12
            year=year-1
        
        quility=QualityOfEmployee.objects.filter(user=self.user,year=year,month=month).order_by('updated').first()
        if quility and quility.updated:
            return quility.updated
        else:
            return ''

    @property
    def UserInfo(self):
        return self.user.first_name +' , '+self.user.last_name + ' - ' +self.user.username
    @property
    def FullName(self):
        return self.user.first_name +' '+self.user.last_name
    @property
    def UserName(self):
        return self.user.username
    @property
    def First_Name(self):
        return self.user.first_name
    @property
    def Last_Name(self):
        return self.user.last_name
    @property
    def Is_Active(self):
        return self.user.is_active
    @property
    def get_absolute_url(self):
        if self.avatar:
            return settings.MEDIA_URL+str(self.avatar)
        else:
            return ""


    #defined here to have access to ActivePluginSetting in Django templates
    @cached_property
    def ActivePlugins(self):
        if ActivePluginSetting.objects.count() > 0:
            return ActivePluginSetting.objects.first()
        else:
            return None

    @cached_property
    def WalletPageAccess(self):
        has_access = False
        if Permission.objects.filter(codename = 'add_transaction').count() > 0:
            transaction_perm_users = Permission.objects.filter(codename = 'add_transaction')[0].user_set.all().values_list('pk', flat = True)
            for user_pk in transaction_perm_users:
                if user_pk == self.user.pk or user_pk in self.GetAllChildrenUserId :
                    has_access = True
        
        return has_access

    @cached_property
    def GetEmployeeParent(self):
        try:
            if (self.organization_group.manager.id == self.user.id) and not (self.organization_group.group_parent is None):
                return self.organization_group.group_parent.manager.id
            else:
                if self.organization_group.manager.id !=self.user.id:
                    return self.organization_group.manager.id
                else:
                    return None
        except:
            return None
    
    @cached_property
    def GetEmployeeParentSet(self):
        parent_set=set()
        try:
            if (self.organization_group==None):
                return parent_set
            group=self.organization_group
            if (group.manager==None):
                return parent_set

            while(group.manager):
                parent_set.add(group.manager.id)
                if group.group_parent:
                    group=Organization_Group.objects.get(pk=group.group_parent.id)
                else:
                    break
            return parent_set
        except:
            return parent_set

    @cached_property
    def GetEmployeeTopParent(self):
        try:
            if (self.organization_group==None):
                return self.user
            group=self.organization_group
            if (group.manager==None):
                return self.user

            while(group.manager):
                if group.group_parent:
                    group=Organization_Group.objects.get(pk=group.group_parent.id)
                else:
                    return group.manager
        except:
            return self.user

    @cached_property
    def GetEmployeeParentLocumtenensSet(self):
        parent_set=set()
        try:
            if (self.organization_group==None):
                return parent_set
            group=self.organization_group
            if (group.manager==None):
                return parent_set

            while(group.manager):
                if group.locumtenens and group.locumtenens_active and self != group.manager:
                    parent_set.add(group.locumtenens.id)
                if group.group_parent:
                    group=Organization_Group.objects.get(pk=group.group_parent.id)
                else:
                    break
            return parent_set
        except:
            return parent_set
    
    @cached_property
    def GetAllChildrenUserId(self):
        children_user_id_set=set()
        if (self.organization_group.manager.id != self.user.id):
            return children_user_id_set
        temp_organization_group_set=set()
        for _organization_group in Organization_Group.objects.filter(group_parent=self.organization_group):
            temp_organization_group_set.add(_organization_group.id)

        for employee in Employee.objects.filter(organization_group=self.organization_group).exclude(pk=self.pk).order_by("user__last_name"):
            children_user_id_set.add(employee.user.id)
        
        try:
            while(len(temp_organization_group_set)>0):
                item=temp_organization_group_set.pop()
                for _organization_group in Organization_Group.objects.filter(group_parent__id=item):
                    temp_organization_group_set.add(_organization_group.id)
                for employee in Employee.objects.filter(organization_group__id=item).exclude(pk=self.pk).order_by("user__last_name"):
                    children_user_id_set.add(employee.user.id)
        except:
            pass 
        return children_user_id_set

    @cached_property
    def GetDirectChildrenUserId(self):
        children_user_id_set=set()
        if (self.organization_group.manager.id != self.user.id):
            return children_user_id_set
        for _organization_group in Organization_Group.objects.filter(group_parent=self.organization_group):
            if _organization_group.manager != None :
                children_user_id_set.add(_organization_group.manager.id)

        for employee in Employee.objects.filter(organization_group=self.organization_group).exclude(pk=self.pk).order_by("user__last_name"):
            children_user_id_set.add(employee.user.id)
        return children_user_id_set

    @cached_property
    def GetDirectChildrenForLocumtenenseUserId(self):
        children_user_id_set=set()
        
        try:
            locum_org_group = Organization_Group.objects.get(locumtenens__employee=self)
        except:
            return children_user_id_set
        for _organization_group in Organization_Group.objects.filter(group_parent=locum_org_group):
            children_user_id_set.add(_organization_group.manager.id)

        for employee in Employee.objects.filter(organization_group=locum_org_group).order_by("user__last_name"):
            children_user_id_set.add(employee.user.id)
        return children_user_id_set

    @property
    def IsManager(self):
        if (self.organization_group.manager.id == self.user.id):
            return True
        else:
            return False

    # return a set of task ids employee has access to task groups containing them
    @cached_property
    def UnderTaskGroupTasks(self):
        containing_tasks = set()
        group_tasks = Task.objects.filter(group_assignee__head=self.user)
        for gt in group_tasks:
            containing_tasks.add(gt.id)
        children_tasks = Task.objects.filter(task_parent__in=group_tasks)
        while(len(children_tasks)>0):
            for ct in children_tasks:
                containing_tasks.add(ct.id)
            children_tasks = Task.objects.filter(task_parent__in=children_tasks)
        return containing_tasks

    @cached_property
    def CopyFromAccessTasks(self):
        copy_tasks_set = set()
        copy_tasks = Task.objects.filter(user_assignee=self.user).exclude(copy_from=None)
        for ct in copy_tasks:
            copy_tasks_set.add(ct.copy_from.id)
        copy_from_tasks = Task.objects.filter(id__in=copy_tasks_set).exclude(copy_from=None)
        while(len(copy_from_tasks)>0):
            for ct in copy_from_tasks:
                copy_tasks_set.add(ct.copy_from.id)
            copy_from_tasks = Task.objects.filter(id__in=copy_tasks_set).exclude(copy_from=None).exclude(copy_from__id__in=copy_tasks_set)
        return copy_tasks_set

    @cached_property
    def TaskAssignedResources(self):
        resources = Resource.objects.filter(Q(pk__in=ResourceTaskAssignment.objects.filter(Q(task__user_assignee__employee=self)|Q(task__user_assignee__pk__in=self.GetAllChildrenUserId)\
            |Q(task__group_assignee__head__employee=self)).values_list('resource__id', flat=True))).values_list('id', flat=True)

        return resources

    @cached_property
    def CreatableResTypes(self):
        creatable_res_types = self.user.creatable_res_types.all().values('pk')
        return creatable_res_types


class Tasks_No_Assign_Manager(models.Manager):
    def get_queryset(self):
        return super(Tasks_No_Assign_Manager, self).get_queryset().filter(user_assignee=None,group_assignee=None,cancelled=False)


class Task_No_Start_Manager(models.Manager):
    def get_queryset(self):
        return super(Task_No_Start_Manager, self).get_queryset().filter(Q(progress =0,confirmed=False,cancelled=False,user_assignee__isnull =False)|Q(progress =0,confirmed=False,cancelled=False,group_assignee__isnull=False))


class Task_Started_Manager(models.Manager):
    def get_queryset(self):
        return super(Task_Started_Manager, self).get_queryset().filter(Q(progress__gt =0,progress__lt=100,confirmed=False,cancelled=False,user_assignee__isnull =False)|Q(progress__gt =0,progress__lt=100,confirmed=False,cancelled=False,group_assignee__isnull =False))


class Task_No_Confirmed_Manager(models.Manager):
    def get_queryset(self):
        return super(Task_No_Confirmed_Manager, self).get_queryset().filter(Q(progress =100,confirmed=False,cancelled=False,user_assignee__isnull =False)|Q(progress =100,confirmed=False,cancelled=False,group_assignee__isnull =False))


class Task_Confirmed_Manager(models.Manager):
    def get_queryset(self):
        return super(Task_Confirmed_Manager, self).get_queryset().filter(Q(confirmed=True,cancelled=False,user_assignee__isnull =False)|Q(confirmed=True,cancelled=False,group_assignee__isnull =False))


class Task(models.Model):
    name=models.CharField(null=True,max_length=100)
    description = models.TextField(blank = True,null=True)
    last_result = models.TextField(blank = True,null=True)
    task_parent=models.ForeignKey('self',blank  = True, null=True,related_name="children",on_delete=models.PROTECT)
    #######################################################################
    prerequisite_type= models.SmallIntegerField(null=True)
    # prerequisite_type value:
    # null ===>no prerequisite
    # 1    ===>require all
    # 2    ===> require one 
    #######################################################################
    task_level=models.ForeignKey(Task_Level,blank  = True,related_name='task_level_tasks',null=True,on_delete=models.SET_NULL)
    task_type=models.ForeignKey(Task_Type,blank  = True,null=True,related_name='task_type_tasks',on_delete=models.SET_NULL)
    creator = models.ForeignKey(User,related_name='creator_tasks',on_delete=models.PROTECT)
    task_group = models.BooleanField(default=False)
    user_assignee=models.ForeignKey(User,blank  = True,null=True,related_name="tasks_user_assignee",on_delete=models.SET_NULL)
    group_assignee=models.ForeignKey(Task_Group,blank  = True,null=True,related_name="task_group_assignee",on_delete=models.SET_NULL)
    #######################################################################
    assign_status=models.SmallIntegerField(null=True)
    # assign value :
    # null ====> not assigned
    # 1    ====> employee assigned
    # 2    ====> Task_Group assigned
    # 3    ====> assign requested 
    # 4    ====> request accepted
    # 5    ====> all request rejected
    #######################################################################
    budget=models.IntegerField(null=True)
    progress =models.SmallIntegerField(null=True,default=0)
    progress_autocomplete=models.BooleanField(default=False)
    progress_complete_date=models.DateTimeField(null=True)
    confirmed_date=models.DateTimeField(null=True)
    task_portion_in_parent=models.SmallIntegerField(null=True,default=0)
    #task_workflow_template INT(10)
    score=models.SmallIntegerField(null=True)
    cancelled=models.BooleanField(default=False)
    startdate = models.DateField(null=True)
    startdate_notification=models.ForeignKey(Notification,blank  = True,null=True,related_name='startdate_task_notification',on_delete=models.SET_NULL)
    confirmed=models.BooleanField(default=False)
    task_priority=models.SmallIntegerField(default=1)
    ######################################################################
    enddate = models.DateField(null=True)
    enddate_notification=models.ForeignKey(Notification,blank  = True,null=True,related_name='enddate_task_notification',on_delete=models.SET_NULL)
    current = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    public = models.BooleanField(default=False)
    copy_from = models.ForeignKey('self', null = True, blank=True, related_name='copies',on_delete=models.SET_NULL)
    children_copied = models.BooleanField(default=False,null=False,blank=True)
    investigative = models.BooleanField(default=False,null=False,blank=True)
    educational = models.BooleanField(default=False,null=False,blank=True)
    difficulty = models.PositiveSmallIntegerField(default=1)
    approved = models.BooleanField(default=True)
    state = models.ForeignKey(Task_Type_State, on_delete=models.SET_NULL, blank=True, null=True, related_name='tasks')
    verifier_seen = models.BooleanField(default=False)
    executor = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='executing_tasks')
    wait = models.BooleanField(default=False)

    prerequisites = models.ManyToManyField("self",through='Task_Prerequisite',symmetrical=False,through_fields=('task','prerequisite'))

    class Meta:
        ordering = ('-task_priority','enddate','updated')
        unique_together = ('name', 'task_parent_id',)
        db_table='task'
    def __str__(self):
        return str(self.name)
    @property
    def PersianEndDate(self):
        return ConvertToSolarDate(self.enddate)
    @property
    def PersianStartDate(self):
        return ConvertToSolarDate(self.startdate)
    @property
    def PersianCreationDate(self):
        return ConvertToSolarDate(self.created)

    @cached_property
    def full_duration(self):
        all_task_ids = self.GetAllTaskChildrenId
        all_task_ids.add(self.id)                     # add current task to task children
        task_times = TaskTime.objects.filter(task__pk__in=all_task_ids).exclude(start=None, end=None)
        users_task_time = {}            # user task times without weight
        users_task_time_score_multiply = {}    # user task times with weight
        task_all_time = 0
        task_all_score = 0
        
        
        for item in task_times:
            if item.user.get_full_name() in users_task_time:       #calculated times for existed user in list 
                days,seconds=item.Duration.days , item.Duration.seconds
                duration=days * 24 * 60 * 60 + seconds 
                users_task_time[item.user.get_full_name()][0] +=duration
                try:
                    users_task_time_score_multiply[item.user.get_full_name()] += duration * item.task.score
                except:
                    users_task_time_score_multiply[item.user.get_full_name()] += duration * 5
            else:
                days,seconds=item.Duration.days , item.Duration.seconds
                duration=days * 24 * 60 * 60 + seconds
                users_task_time[item.user.get_full_name()]=[0,0,0,""]         # create an item for non existed user contains [user times , user times percent , user times percent with weight]
                users_task_time[item.user.get_full_name()][0] = duration
                try:
                    users_task_time_score_multiply[item.user.get_full_name()] = duration * item.task.score 
                except:
                    users_task_time_score_multiply[item.user.get_full_name()] = duration * 5
        
        #all times spent for task and its children
        for u in users_task_time:
            task_all_time += users_task_time[u][0]

        #all times spent for task and its children with score(or weight)
        for u in users_task_time_score_multiply:
            task_all_score += users_task_time_score_multiply[u]    

        #calculate user times percentage in all times and convert timedelta to time string format
        for u in users_task_time:
            users_task_time[u][1] = int(round((users_task_time[u][0] / task_all_time) * 100, 0))
            users_task_time[u][0] =ConvertTimeDeltaToStringTime( datetime.timedelta(seconds=users_task_time[u][0]))

        #calculate user times percentage in all times with score
        for u in users_task_time_score_multiply:
            users_task_time[u][2] = int(round((users_task_time_score_multiply[u] / task_all_score) *100, 0))

        return users_task_time

    @cached_property
    def tag(self):
        if self.educational :
            return "edu"
        elif self.task_type and self.task_type.is_request :
            return "req"
        else :
            return "mis"

    @cached_property
    def deadline_status(self):
        if self.enddate:
            if datetime.date.today() > self.enddate:
                return "expired"
            elif ( self.enddate - datetime.date.today()).days < 2:
                return "expiring"
            else:
                return "ok"
        return "ok"

    # 1 - not start
    # 2 - cancelled
    # 3 - Delay
    # 4 - Doing 
    # 5 - finished
    @cached_property
    def task_status(self):
        if self.progress == 0 :
            return 1
        if self.cancelled == True:
            return 2
        if self.progress > 0 and self.progress < 100 :
            if self.enddate and datetime.date.today() > self.enddate:
                return 3
            return 4
        if self.progress == 100 :
            return 5 
        
            
        
    #   Task request status values
    #   0:  Not a Request
    #   1:  Not seen yet
    #   2:  Not accepted yet
    #   3:  Rejected
    #   4:  Doing
    #   5:  Done
    @cached_property
    def request_status(self):
        print(self.id)
        if self.task_type and self.task_type.is_request:
            if self.progress >= 100:
                return 5
            elif self.progress > 0:
                return 4
            elif self.verifier_seen:
                rejected = False
                for verification_log in self.task_verifications.all():
                    if verification_log.verified == False:
                        rejected = True
                        break
                for assign_request in self.task_assign_requests.all():
                    if assign_request.status==2:
                        rejected = True
                        break
                
                if rejected :
                    return 3
                
                return 2

            return 1

        return 0
    
    @property
    def UnderTaskGroup(self):
        task=self
        while(task.task_parent):
            task=task.task_parent
            if task.group_assignee:
                return task.group_assignee
        return None

    @cached_property
    def GetTaskChildrenId(self):
        task_list=[]
        _children=self.children.all()
        for child in _children:
            task_list.append(child.pk)
        return task_list

    @property
    def GetNewProgressAndColor(self):
        return [{"id": self.pk, "progress_value": self.progress, "progress_color": self.ProgressColor}] + ( self.task_parent.GetNewProgressAndColor if self.task_parent else [])

    @cached_property
    def GetAllTaskChildrenId(self):
        children_set=set()
        temp_children_set=set()
        temp_children_set.add(self.id)

        while(len(temp_children_set)>0):
            item=temp_children_set.pop()
            _tasks=Task.objects.filter(task_parent=item)
            
            try:
                for c in _tasks:
                    children_set.add(c.id)
                    temp_children_set.add(c.id)
            except:
                pass
        
        return children_set

    @property
    def ProgressColor(self):
        try:
            if self.enddate and self.startdate:
                if self.progress == 100:
                    _task_duration = self.enddate - self.startdate
                    _duration_percent = ((self.progress_complete_date.date() - self.startdate) / (_task_duration)) * 100 if (self.progress_complete_date.date() > self.startdate) else 0
                    _color_hue = (cube((self.progress - _duration_percent)/100 if ((self.progress - _duration_percent) > -100) else -1 )*120)+120
                    return "hsla("+str(int(_color_hue))+",100%,60%,"
                else:
                    _task_duration = self.enddate - self.startdate
                    _duration_percent = ((datetime.datetime.now().date() - self.startdate) / (_task_duration)) * 100 if (datetime.datetime.now().date() > self.startdate) else 0
                    _color_hue = (cube((self.progress - _duration_percent)/100 if ((self.progress - _duration_percent) > -100) else -1 )*120)+120
                    return "hsla("+str(int(_color_hue))+",100%,60%,"
            else:
                return "hsla(120,100%,60%,"
        except :
            return "hsla(120,100%,60%,"

    @cached_property
    def GetTaskChildrenSet(self):
        children_set=set()
        parent_set=set()
        parent_set.add(self.id)
        while(len(parent_set)>0):
            item=parent_set.pop()
            _children=Task.objects.filter(task_parent__id=item)
            try:
                for c in _children:
                    parent_set.add(c.id)
                    children_set.add(c.id)
            except:
                pass
        return children_set

    @cached_property
    def GetTaskParentIDSet(self):
        parent_set=set()
        task = self
        while True:
            if task.task_parent == None:
                break
            else:
                task = task.task_parent
                parent_set.add(task.id)
        
        return parent_set
    
    @property
    def GetTaskPortionPercentInParent(self):
        try:
            task_siblings_id = self.task_parent.GetTaskChildrenId
            weight_sum = 0
            task_weight = self.task_portion_in_parent
            for i in task_siblings_id:
                task = Task.objects.get(pk=i)
                weight_sum += task.task_portion_in_parent 
            result = (task_weight/weight_sum)*100
            return round(result , 1)
        except:
            return 100
    @transaction.atomic
    def SetProgressValue(self,_amount):
        self.progress=_amount
        if (self.progress==100):
            self.progress_complete_date = datetime.datetime.now()
        else:
            self.progress_complete_date = None
        self.save()
        if self.task_parent :
            if self.task_parent.progress_autocomplete :
                self.task_parent.UpdateAutoProgress()
        
    @transaction.atomic
    def UpdateAutoProgress(self):
        _portions_sum = 0
        _progress_sum = 0
        
        for _child_task in self.children.all():
            _portions_sum += _child_task.task_portion_in_parent
            _progress_sum += _child_task.task_portion_in_parent * _child_task.progress         
        if _portions_sum>0:
            self.progress = _progress_sum / _portions_sum
        self.save()
        if self.task_parent :
            if self.task_parent.progress_autocomplete :
                self.task_parent.UpdateAutoProgress()
        try:
            task_progress = TaskProgress.objects.get(task=self , progress_date=datetime.datetime.date(datetime.datetime.now()))
            task_progress.progress_value = self.progress
            task_progress.save()                        
        except:                              
            task_progress = TaskProgress()
            task_progress.progress_value = self.progress
            task_progress.user = self.user_assignee
            task_progress.task = self 
            task_progress.progress_date = datetime.datetime.date(datetime.datetime.now())
            task_progress.save()
            


    def GetTaskCategory(self,user):
        _task_category=None
        try:
            _task_category=TaskCategory.objects.get(user=user,task=self)
            return _task_category.dashboard_category
        except:
            _task_category=None
        return _task_category

    objects=models.Manager()
    no_assign=Tasks_No_Assign_Manager()
    no_start=Task_No_Start_Manager()
    started=Task_Started_Manager()
    no_confirmed=Task_No_Confirmed_Manager()
    confirmed_tasks=Task_Confirmed_Manager()


class TaskCategory(models.Model):
    task=models.ForeignKey(Task,blank  = True,null=True,related_name="task_categories",on_delete=models.SET_NULL)
    dashboard_category=models.ForeignKey(DashboardCategory,blank  = True,null=True,related_name="task_dashboard_category",on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        unique_together = ('dashboard_category', 'task',)
        db_table='task_category'


class Task_Assign_Request(models.Model):
    task = models.ForeignKey(Task,blank  = True,null=True,related_name='task_assign_requests',on_delete=models.CASCADE)
    user = models.ForeignKey(User,blank  = True,null=True,related_name='assign_request_user',on_delete=models.CASCADE)
    ############################################################
    status=models.SmallIntegerField(null=True)
    #status value:
    # 1===> accepted
    # 2===> rejected
    ############################################################
    text = models.TextField(blank = True)
    ############################################################
    notification_status=models.SmallIntegerField(null=True)
    #notification_status value
    # null ====> not seen
    # 1    ====> seen
    # 2    ====> deleted
    need_verification=models.BooleanField(null=True)
    ############################################################
    seen = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('pk',)
        db_table='task_assign_request'
        unique_together = ('task', 'user',)
    # def __str__(self):
    #     return self.name

    @property
    def PersianUpdateDate(self):
        return ConvertToSolarDate(self.updated)
    

class Task_Type_Property(models.Model):
    task_type = models.ForeignKey(Task_Type,blank  = True,related_name='task_type_property',null=True,on_delete=models.CASCADE, verbose_name=u'نوع کار')
    name = models.CharField(max_length=100, verbose_name=u'نام')
    description = models.TextField(blank = True ,null=True, verbose_name=u'توضیحات')
    ##################################################
    _Property_Num=1
    _Property_Text=2
    _Property_date=3
    _Property_File=4
    _Property_Bool=5
    value_choices=(
        (_Property_Num,'عددی'),
        (_Property_Text,'متنی'),
        (_Property_date,'تاریخی'),
        (_Property_File,'فایلی'),
        (_Property_Bool,'بولین'),
    )
    value_type=models.SmallIntegerField(choices=value_choices,null=True, verbose_name=u'نوع مقدار')
    ##################################################
    order = OrderField(null=True,blank=True, for_fields=['task_type'])
    deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    slug = models.SlugField(null=True)
    class Meta:
        ordering = ('order',)
        db_table='task_type_property'
        unique_together = ('name', 'task_type',)
        verbose_name = u"ویژگی نوع کار"
        verbose_name_plural = u"ویژگی ها انواع کار"

    def __str__(self):
        return self.name
    @property
    def value_type_name(self):
        if self.value_type==1:
            return 'File'
        else:
            return 'else'


class Task_Property_Num(models.Model):
    task = models.ForeignKey(Task,blank  = True,null=True, related_name='task_num_properties',on_delete=models.CASCADE)
    task_type_property = models.ForeignKey(Task_Type_Property,blank  = True,related_name='task_type_property_num',null=True,on_delete=models.CASCADE)
    value = models.DecimalField(max_digits = 20,decimal_places = 5,null=True)
    deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('task_type_property__order',)
        db_table='task_property_num'
    def __str__(self):
        return str(self.value)


class Task_Property_Text(models.Model):
    task = models.ForeignKey(Task,blank  = True,null=True, related_name='task_text_properties',on_delete=models.CASCADE)
    task_type_property = models.ForeignKey(Task_Type_Property,blank  = True,related_name='task_type_property_text',null=True,on_delete=models.CASCADE)
    value = models.TextField(blank = True)
    deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('task_type_property__order',)
        db_table='task_property_text'
    def __str__(self):
        return str(self.value)


class Task_Property_Bool(models.Model):
    task = models.ForeignKey(Task,blank  = True,null=True, related_name='task_bool_properties',on_delete=models.CASCADE)
    task_type_property = models.ForeignKey(Task_Type_Property,blank  = True,related_name='task_type_property_bool',null=True,on_delete=models.CASCADE)
    value = models.BooleanField(blank = True)
    deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('task_type_property__order',)
        db_table='task_property_bool'
    def __str__(self):
        return str(self.value)


class Task_Property_Date(models.Model):
    task = models.ForeignKey(Task,blank  = True,null=True, related_name='task_date_properties',on_delete=models.CASCADE)
    task_type_property = models.ForeignKey(Task_Type_Property,blank  = True,related_name='task_type_property_date',null=True,on_delete=models.CASCADE)
    value = models.DateTimeField(null=True)
    deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('task_type_property__order',)
        db_table='task_property_date'
    def __str__(self):
        return ConvertToSolarDate(self.value)
    @property
    def PersianDate(self):
        return ConvertToSolarDate(self.value)


class Task_Property_File(models.Model):
    task = models.ForeignKey(Task,blank  = True,null=True, related_name='task_file_properties',on_delete=models.CASCADE)
    task_type_property = models.ForeignKey(Task_Type_Property,blank  = True,related_name='task_type_property_file',null=True,on_delete=models.CASCADE)
    value =models.FileField(upload_to = task_property_file_directory_path,blank=True,null=True)
    filename = models.CharField(null=True,max_length=250)
    deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('task_type_property__order',)
        db_table='task_property_file'
    def __str__(self):
        return str(self.value)

    @property
    def get_absolute_url(self):
        if self.value:
            return settings.MEDIA_URL+str(self.value)
        else:
            return ""


class Task_Prerequisite(models.Model):
    task=models.ForeignKey(Task,related_name="followe",on_delete=models.CASCADE)
    prerequisite=models.ForeignKey(Task,related_name="follower",on_delete=models.CASCADE)
    class Meta:
        ordering = ('pk',)
        db_table='task_prerequisite'
        unique_together = ('prerequisite', 'task',)


class Task_Attachment(models.Model):
    name=models.CharField(null=True,max_length=250)
    task=models.ForeignKey(Task,blank  = True,null=True,related_name="task_attachments",on_delete=models.CASCADE)
    attachment_file=models.FileField(upload_to = user_file_directory_path,blank=True)
    filename=models.CharField(null=True,max_length=250)
    # extension=models.CharField(null=True,max_length=100)
    # mime=models.CharField(null=True,max_length=100)
    # size=models.IntegerField(null=True)
    user = models.ForeignKey(User,blank  = True,null=True,on_delete=models.CASCADE)
    class Meta:
        ordering = ('-pk',)
        db_table='task_attachment'
    def __str__(self):
        return str(self.attachment_file)


class Task_Verification_Log(models.Model):
    verification = models.ForeignKey(Task_Type_Verification, blank=False,null=False,related_name='verification_logs',on_delete=models.CASCADE, verbose_name=u'تاییدیه مرتبط')
    task = models.ForeignKey(Task,blank  = False, null=False,related_name="task_verifications",on_delete=models.CASCADE)
    verified = models.BooleanField(null=True,blank=True,verbose_name=u'تایید درخواست توسط شخص تایید کننده')
    verifier = models.ForeignKey(User,blank  = False, null=True ,related_name="user_verifications",on_delete=models.SET_NULL,verbose_name=u'کاربر تایید کننده')
    verifier_locumtenens = models.ForeignKey(User,blank  = False, null=True ,related_name="user_verifications_locumtenens",on_delete=models.SET_NULL,verbose_name=u'جانشین کاربر تایید کننده')
    last_verifier = models.ForeignKey(User,blank  = False, null=True ,related_name="user_verification_ok",on_delete=models.SET_NULL,verbose_name=u'کاربر نهایی تایید کننده')
    comment = models.TextField(blank= True, null=True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('task','verification__order')
        db_table = 'task_verification_log'
        verbose_name = u"تاییدیه درخواست"
        verbose_name_plural = u"سابقه تایید درخواست ها"
    @property
    def PersianCreatedDate(self):
        return ConvertToSolarDate(self.created)

    @property
    def PersianUpdatedDate(self):
        return ConvertToSolarDate(self.updated)


class TaskProgress(models.Model):
    task=models.ForeignKey(Task,blank  = True,null=True,related_name="task_progress",on_delete=models.CASCADE)
    user=models.ForeignKey(User,blank  = True,null=True,on_delete=models.CASCADE)
    progress_value = models.SmallIntegerField(null=True,default=0)
    progress_date = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('pk',)
        db_table='task_progress'
    @cached_property
    def isTaskUserAssignee(self):
        if self.user==self.task.user_assignee:
            return True
        else:
            return False       


class TaskComment(models.Model):
    content=models.TextField(blank  = True,null=True)
    task=models.ForeignKey(Task,blank = True,null=True,related_name="task_comments",on_delete=models.CASCADE)
    user = models.ForeignKey(User,blank = True,null=True,related_name="task_comments",on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    reply_to = models.ForeignKey("TaskComment",blank = True,null=True,related_name="replyed",on_delete=models.CASCADE)
    class Meta:
        ordering = ('pk',)
        db_table='task_comment'
    @cached_property
    def isTaskUserAssignee(self):
        if self.user==self.task.user_assignee:
            return True
        else:
            return False
    @cached_property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)


class Subtask(models.Model):
    name= models.CharField(max_length=200)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    done = models.BooleanField(default=False)
    done_time = models.DateTimeField(null=True,blank=True)
    order = OrderField(null=True,blank=True, for_fields=['task'])
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        ordering = ('order',)
        db_table='subtask'
        unique_together = ('task', 'name',)


#################################  Task End   #############################
#*******************************************************************************#


#################################                  Timing & Report                   ###########################
class PublicTask(models.Model):
    name=models.CharField(null=True,max_length=100, unique=True)
    popular=models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('popular','name',)
        db_table='public_task'
    def __str__(self):
        return self.name


class PublicTaskTime(models.Model):
    public_task=models.ForeignKey(PublicTask,blank  = True,null=True,related_name="public_task_times",on_delete=models.SET_NULL)
    user=models.ForeignKey(User,blank  = True,null=True,on_delete=models.CASCADE)
    start= models.DateTimeField()
    end= models.DateTimeField()
    tasktime_notification=models.ForeignKey(Notification,blank  = True,null=True,on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('start',)
        db_table='public_task_time'


    @property
    def TaskName(self):
        return self.public_task.name


class TaskTime(models.Model):
    task=models.ForeignKey(Task,blank  = True,null=True,related_name="task_times",on_delete=models.SET_NULL)
    user=models.ForeignKey(User,blank  = True,null=True,on_delete=models.CASCADE)
    start= models.DateTimeField()
    end= models.DateTimeField()
    tasktime_notification=models.ForeignKey(Notification,blank  = True,null=True,related_name='tasktime_notification',on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    ## colors for timeline
    value_choices=(
        (0,"red"),
        (1,"lightsalmon"),
        (2,"lightgreen"),
        (3,"gray"),
    )
    color = models.SmallIntegerField(choices=value_choices,null=True, default=0)
    teleworking = models.BooleanField(default=False)
    mission = models.BooleanField(default=False)

    class Meta:
        ordering = ('start',)
        db_table='task_time'
    @property
    def PersianStartDate(self):
        return ConvertToSolarDate(self.start)
    @property
    def PersianEndDate(self):
        return ConvertToSolarDate(self.end)

    @property
    def StartTime(self):
        return str(self.start)[11:16]
    @property
    def EndTime(self):
        return str(self.end)[11:16]

    def TimeLineColorUpdate(self):
        _reports=self.reports.all()

        
        if len(_reports)==0:
            self.color=0
        
        if len(self.reports.filter(confirmed=False))>0:
            self.color=1

        if len(self.reports.all())>0 and len(self.reports.filter(draft=True))<len(self.reports.all()):
            self.color=1
        
        if len(self.reports.all())>0 and len(self.reports.filter(confirmed=True))==len(self.reports.all()):
            self.color=2
        if len(self.reports.all())>0 and len(self.reports.all())==len(self.reports.filter(draft=True)):
            self.color=3
        self.save()
        return

    @property
    def TaskName(self):
        return self.task.name
    
    @property
    def Duration(self):
        if (self.end and self.start):
            return self.end - self.start
        else:
            return None


class TempTimingRecord(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='timer')
    public_task=models.ForeignKey(PublicTask,blank  = True,null=True,related_name="temp_public_task",on_delete=models.SET_NULL)
    task=models.ForeignKey(Task,blank  = True,null=True,related_name="temp_task",on_delete=models.SET_NULL)
    start= models.DateTimeField()
    description = models.TextField(blank = True ,null=True)
    # status=models.SmallIntegerField(blank=True,null=True)
    #####Status:
    # none :not running
    # 1 : running
    class Meta:
        ordering = ('pk',)
        db_table='temp_time_record'
    def __str__(self):
        return str(self.start)


class Report(models.Model):
    title=models.CharField(blank  = True,null=True,max_length=100)
    content= RichTextUploadingField(blank  = True,null=True )
    report_type=models.SmallIntegerField(blank=True,null=True)
    ####report_type:
    # 1 = common report  
    # 2 = event
    # 3 = result

    #social eng extended types
    # 4 = chat
    # 5 = file
    # 6 = link
    ################
    task_time=models.ForeignKey(TaskTime,blank  = True,null=True,related_name="reports",on_delete=models.CASCADE)
    confirmed=models.BooleanField(default=False)
    confirmed_by_locumtenens=models.BooleanField(default=False)
    confirmed_notification=models.ForeignKey(Notification,blank  = True,null=True,related_name='confirmed_report_notification',on_delete=models.SET_NULL)
    comment_notification=models.ForeignKey(Notification,blank  = True,null=True,related_name='comment_report_notification',on_delete=models.SET_NULL)
    score=models.SmallIntegerField(null=True)
    draft=models.BooleanField(default=False)
    group_shared = models.BooleanField(default=False)
    month_report = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    shared_users = models.ManyToManyField(User,related_name='shared_reports', db_table='report_share')

    tags=TaggableManager()
    class Meta:
        ordering = ('task_time__start',)
        db_table='report'
    def __str__(self):
        return self.title
    @cached_property
    def PersianReportDate(self):
        return ConvertToSolarDate(self.task_time.start)
    @cached_property
    def PersianReportCreationDate(self):
        created_teh=self.created.astimezone(timezone('Asia/Tehran'))
        return ConvertToSolarDate(created_teh)
    @cached_property
    def ReportCreationTime(self):
        created_teh=self.created.astimezone(timezone('Asia/Tehran'))
        return str(created_teh.time().hour) + ":" + str(created_teh.time().minute)
    @cached_property
    def StartTime(self):
        return self.task_time.StartTime
    @cached_property
    def EndTime(self):
        return self.task_time.EndTime
    @cached_property
    def OutOfTime(self):
        out_time = datetime.datetime.combine(self.task_time.start.date() , datetime.time())
        out_time += datetime.timedelta(hours=36)
        if out_time < datetime.datetime.combine(self.created.date() , self.created.time()):
            return True
        else:
            return False
    @cached_property
    def persian_full_time(self):
        return jdt.fromgregorian(date = self.task_time.start.date()).strftime(format='%Y/%m/%d') + " " + str(self.task_time.start.time())[:-3] + " → " + str(self.task_time.end.time())[:-3]


class ReportExtension(models.Model):
    report = models.OneToOneField(Report, null=False, blank=False, on_delete=models.CASCADE, related_name='extension')
    chat_summary = models.TextField(null=True,blank=True)
    target_started = models.BooleanField(default=False, null=False, blank=False)
    malicious_file_link = models.BooleanField(default=False, null=False, blank=False)
    succeed = models.BooleanField(default=True, null=False, blank=False)
    enhancement_score = models.SmallIntegerField(default=0)
    link_address = models.TextField(null=True, blank=True)
    link_user_agent = models.CharField(max_length=50, null=True, blank=True)
    file_type = models.CharField(max_length=20, null=True, blank=True)
    malware_type = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        ordering = ('report__pk',)
        db_table='report_extension'
    def __str__(self):
        return str(self.report)


class ReportAttachment(models.Model):
    name=models.CharField(null=True,max_length=100)
    report=models.ForeignKey(Report,blank  = True,null=True,related_name="report_attachments",on_delete=models.CASCADE)
    attachment_file=models.FileField(upload_to = user_file_directory_path,blank=True)
    filename=models.CharField(null=True,max_length=100)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('pk',)
        db_table='report_attachment'
    
    @property
    def user(self):
        return self.report.task_time.user


class ReportComment(models.Model):
    content=models.TextField(blank  = True,null=True)
    report=models.ForeignKey(Report,blank = True,null=True,related_name="report_comments",on_delete=models.CASCADE)
    user = models.ForeignKey(User,blank = True,null=True,related_name="report_comments",on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('pk',)
        db_table='report_comment'
    @property
    def isReportCreator(self):
        if self.user==self.report.task_time.user:
            return True
        else:
            return False
    @property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)
#################################   Timing & Report End   #############################
#*******************************************************************************#

#################################   Resource Management Start    #######################
class OPArea(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        db_table='op_area'
        verbose_name = u"محور عملیاتی"
        verbose_name_plural = u"محور های عملیاتی"
    def __str__(self):
        return self.name


class OPProject(models.Model):
    name = models.CharField(max_length=100)
    area = models.ForeignKey(OPArea, on_delete=models.PROTECT, related_name="projects")

    class Meta:
        db_table='op_project'
        verbose_name = u"پروژه عملیاتی"
        verbose_name_plural = u"پروژه های عملیاتی"
    def __str__(self):
        return self.name

    @cached_property
    def color(self):
        return "hsla("+str(int(hashlib.sha1(self.name.encode('utf8')).hexdigest()[:3] , 16)%300)+",40%,45%,1)"


class ResourceTypeCreationLimit(models.Model):
    resource_type = models.ForeignKey(ResourceType,on_delete=models.CASCADE,related_name='creators_limit')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='creatable_res_type_limits')

    class Meta:
        db_table='resource_type_creation_limit'
        verbose_name = u"دسترسی ایجاد منبع"
        verbose_name_plural = u"دسترسی های ایجاد منبع"
    def __str__(self):
        return str(self.resource_type) + "-" + str(self.user)


class Resource(models.Model):
    name=models.CharField(max_length=100)
    resource_type=models.ForeignKey(ResourceType,blank  = True,null=True,related_name="resource",on_delete=models.SET_NULL)
    creator=models.ForeignKey(User,blank  = True,null=True,related_name="resource_creator",on_delete=models.SET_NULL)
    owner=models.ForeignKey(User,blank  = True,null=True,related_name="resource_owner",on_delete=models.SET_NULL)
    locumtenens=models.ForeignKey(User,blank  = True,null=True,related_name="resource_locumtenens",on_delete=models.SET_NULL)
    expire_notification=models.ForeignKey(Notification,blank  = True,null=True,related_name='expire_resource_notification',on_delete=models.SET_NULL)
    description = models.TextField(blank = True)
    price = models.DecimalField(max_digits = 20,decimal_places = 5,null=True)
    deleted = models.BooleanField(default=False)    # for logical delete  
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    task=models.ForeignKey(Task,blank  = True,null=True,related_name="resource_task",on_delete=models.SET_NULL)
    payoff_code = models.IntegerField(blank=True, null=True)
    class Meta:
        ordering = ('-updated',)
        db_table='resource'
    def __str__(self):
        return str(self.name)
    
    @cached_property
    def ConsumingResourcePersianExpiration(self):
        if self.resource_type.category==1:
            consuming_resource=None
            try:
                consuming_resource=ConsumingResource.objects.filter(resource=self).order_by('-expiration').first()
            except:
                consuming_resource=None
            if consuming_resource and consuming_resource.expiration:
                return ConvertToSolarDate(consuming_resource.expiration)
            
        
        return ""

    @cached_property
    def HardwareResourceCode(self):
        if self.resource_type.category==2:
            hardware_resource=None
            try:
                hardware_resource=HardwareResource.objects.filter(resource=self).first()
            except:
                hardware_resource=None
            if hardware_resource:
                return hardware_resource.code
        return ""


    @cached_property
    def GetExpireColor(self):
        consuming_resources=ConsumingResource.objects.filter(resource__id=self.id).order_by('-expiration').first()
        if consuming_resources and consuming_resources.expiration:
            if consuming_resources.expiration <= datetime.date.today():
                return  'lightcoral_background'
            elif consuming_resources.expiration<datetime.date.today()+datetime.timedelta(days=4) and consuming_resources.expiration>datetime.date.today():
                return  'khaki_background'
        else:
            return ""
    @cached_property
    def ActiveAssigneeCount(self):
        _count=self.assignements.filter(deleted=None).count()
        return _count


class ResourceAssignment(models.Model):
    resource=models.ForeignKey(Resource,blank  = True,null=True,related_name="assignements",on_delete=models.CASCADE)
    assignee=models.ForeignKey(User,blank  = True,null=True,related_name="resource_assignements",on_delete=models.CASCADE)
    assignee_notification=models.ForeignKey(Notification,blank  = True,null=True,related_name='assignee_resource_notification',on_delete=models.SET_NULL)
    description = models.TextField(blank = True)
    confirmed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    deleted = models.DateTimeField(null=True)
    class Meta:
        ordering = ('-deleted',"-created")
        db_table='resource_assignment'
    def __str__(self):
        return str(self.resource.name+" , "+self.assignee.first_name+" "+self.assignee.last_name)
    @cached_property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)


class ResourceTaskAssignment(models.Model):
    resource=models.ForeignKey(Resource,blank  = True,null=True,related_name="task_assignement",on_delete=models.CASCADE)
    task=models.ForeignKey(Task,blank  = True,null=True,related_name="resource_assignement",on_delete=models.CASCADE)
    assigner=models.ForeignKey(User,blank  = True,null=True,on_delete=models.CASCADE)
    assignee_notification=models.ForeignKey(Notification,blank  = True,null=True,related_name='assignee_resource_task_notification',on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True,null=True)
    class Meta:
        ordering = ('pk',)
        db_table='resource_task_assignment'
        unique_together = ('task', 'resource',)
    @cached_property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)


class ResourceTypeProperty(models.Model):
    name=models.CharField(null=True,max_length=100, verbose_name=u'نام')
    resource_type=models.ForeignKey(ResourceType,blank  = True,null=True,related_name="resource_type_property",on_delete=models.SET_NULL, verbose_name=u'نوع منبع مربوطه')
    order = OrderField(null=True,blank=True, for_fields=['resource_type'])
    ###############################################
    _num=1
    _text=2
    _date=3
    _file=4
    _bool=5
    value_choices=(
        (_num,'عددی'),
        (_text,'متنی'),
        (_date,'تاریخ'),
        (_file,'فایل'),
        (_bool,'بولین'),
    )
    value_type=models.SmallIntegerField(choices=value_choices,default=_num, verbose_name=u'نوع مقدار')
    # value_type value:
    # 1 = Property_Num
    # 2 = Property_Text
    # 3 = Property_date
    # 4 = Property_File
    # 5 = boolean 
    ##################################################
    slug = models.SlugField(null=True)
    isPublic = models.BooleanField(default=False , verbose_name=u'عمومی')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('order',)
        db_table='resource_type_property'
        verbose_name = u"ویژگی نوع مبنع"
        verbose_name_plural = u"ویژگی های انواع منبع"
    def __str__(self):
        return str(self.name)


class ResourcePropertyNum(models.Model):
    resource = models.ForeignKey(Resource,blank  = True,null=True,on_delete=models.CASCADE,related_name='resource_num_properties')
    resource_type_property = models.ForeignKey(ResourceTypeProperty,blank  = True,related_name='resource_type_property_num',null=True,on_delete=models.CASCADE)
    value = models.DecimalField(max_digits = 20,decimal_places = 5,null=True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('resource_type_property__order',)
        db_table='resource_property_num'
    def __str__(self):
        return str(self.value)


class ResourcePropertyText(models.Model):
    resource = models.ForeignKey(Resource,blank  = True,null=True,related_name='resource_text_properties',on_delete=models.CASCADE)
    resource_type_property = models.ForeignKey(ResourceTypeProperty,blank  = True,related_name='resource_type_property_text',null=True,on_delete=models.CASCADE)
    value = models.TextField(blank = True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('resource_type_property__order',)
        db_table='resource_property_text'
    def __str__(self):
        return str(self.value)


class ResourcePropertyDate(models.Model):
    resource = models.ForeignKey(Resource,blank  = True,null=True,related_name='resource_date_properties',on_delete=models.CASCADE)
    resource_type_property = models.ForeignKey(ResourceTypeProperty,blank  = True,related_name='resource_type_property_date',null=True,on_delete=models.CASCADE)
    value = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('resource_type_property__order',)
        db_table='resource_property_date'
    def __str__(self):
        return ConvertToSolarDate(self.value)
    @cached_property
    def PersianDate(self):
        return ConvertToSolarDate(self.value)


class ResourcePropertyFile(models.Model):
    resource = models.ForeignKey(Resource,blank  = True,null=True,related_name='resource_file_properties',on_delete=models.CASCADE)
    resource_type_property = models.ForeignKey(ResourceTypeProperty,blank  = True,related_name='resource_type_property_file',null=True,on_delete=models.CASCADE)
    value = models.FileField(upload_to = task_property_file_directory_path,blank=True,null=True)
    filename = models.CharField(null=True,max_length=250)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('resource_type_property__order',)
        db_table='resource_property_file'
    def __str__(self):
        return str(self.value)

    @cached_property
    def get_absolute_url(self):
        if self.value:
            return settings.MEDIA_URL+str(self.value)
        else:
            return ""


class ResourcePropertyBool(models.Model):
    resource = models.ForeignKey(Resource,blank  = True,null=True,related_name='resource_bool_properties',on_delete=models.CASCADE)
    resource_type_property = models.ForeignKey(ResourceTypeProperty,blank  = True,related_name='resource_type_property_bool',null=True,on_delete=models.CASCADE)
    value = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('resource_type_property__order',)
        db_table='resource_property_bool'


class ResourceTypeRelation(models.Model):
    name=models.CharField(null=True,max_length=100, verbose_name=u'نام')
    source_resource_type = models.ForeignKey(ResourceType,blank  = True,null=True,related_name="from_relations",on_delete=models.CASCADE, verbose_name=u'نوع منبع دارنده رابطه')
    order = OrderField(null=True,blank=True, for_fields=['source_resource_type'])
    destinaton_resource_type = models.ForeignKey(ResourceType,blank  = True,null=True,related_name="to_relations",on_delete=models.CASCADE, verbose_name=u'نوع منبع مقصد رابطه')
    multiple = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    slug = models.SlugField(null=True)

    class Meta:
        ordering = ('pk',)
        db_table='resource_type_relation'
        verbose_name = u"رابطه دو نوع منبع"
        verbose_name_plural = u"روابط انواع منابع"
    def __str__(self):
        return str(self.name)


class ResourceRelation(models.Model):
    relation_type = models.ForeignKey(ResourceTypeRelation,blank  = True,null=True,related_name="relation_type",on_delete=models.CASCADE)
    source_resource = models.ForeignKey(Resource,blank  = True,null=True,related_name="from_relations",on_delete=models.CASCADE)
    destinaton_resource = models.ForeignKey(Resource,blank  = True,null=True,related_name="to_relations",on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    deleted = models.DateTimeField(null=True,blank=True)
    class Meta:
        ordering = ('pk',)
        db_table='resource_relation'


class HardwareResource(models.Model):
    code = models.CharField(null=True,max_length=100)
    serial = models.CharField(null=True,max_length=200)
    resource=models.OneToOneField(Resource,blank  = True,null=True,related_name="hardware_resource",on_delete=models.CASCADE)
    return_status = models.BooleanField(default=False) 
    return_date=models.DateField(null=True)
    health= models.BooleanField(default=False) 
    repair= models.BooleanField(default=False)
    manufacturer = models.CharField(null=True,max_length=100)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('-updated',)
        db_table='hardware_resource'
    def __str__(self):
        return str(self.code)
    @cached_property
    def PersianReturnDate(self):
        return ConvertToSolarDate(self.return_date)
    @cached_property
    def LastAssigneeDate(self):
        assignee=self.resource.assignements.filter(deleted=None).first()
        return ConvertToSolarDate(assignee.created)


class ConsumingResource(models.Model):
    resource=models.ForeignKey(Resource,blank  = True,null=True,related_name="consuming_resources",on_delete=models.CASCADE)
    expiration=models.DateField(null=True)
    expire= models.BooleanField(default=False)
    total_amount=models.IntegerField(null=True)
    consumed_amount=models.IntegerField(null=True)
    price = models.IntegerField(null=True)
    project = models.CharField(max_length=20,null=True)
    op_area = models.ForeignKey(OPArea, blank=True, null=True, on_delete=models.PROTECT, related_name = "consuming_resources")
    op_project = models.ForeignKey(OPProject, blank=True, null=True, on_delete=models.PROTECT, related_name = "consuming_resources")
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('-expire',)
        get_latest_by = 'pk'
        db_table='consuming_resource'
    @cached_property
    def PersianExpiration(self):
        return ConvertToSolarDate(self.expiration)

#################################      Resource Management End    ########################


#################################   Human Resource & Capitals Start   ###########################
class Degree(models.Model):
    user=models.ForeignKey(User,blank  = False, null = False, related_name="degrees",on_delete=models.CASCADE)
     
    ###############################################
    _diploma = 1
    _associate = 2
    _bachelor = 3
    _master = 4 
    _phd = 5
    value_choices=(
        (_diploma,'دیپلم'),
        (_associate,'فوق دیپلم'),
        (_bachelor,'لیسانس'),
        (_master,'فوق لیسانس'),
        (_phd,'دکتری'),
    )
    level =models.SmallIntegerField(choices = value_choices, null = False, blank = False, default = 3)
    # 1-consuming resource
    # 2-hardware Resource
    # 3 software resource
    ###############################################
    university = models.CharField(null  =True, max_length = 100)
    field = models.CharField(null = True, max_length = 100)
    orientation = models.CharField(null = True, max_length = 100)
    from_date = models.DateField(null = True)
    to_date = models.DateField(null = True)
    description = models.TextField(blank = True)
    created = models.DateTimeField(auto_now_add = True, null = True)
    updated = models.DateTimeField(auto_now = True, null = True)
    class Meta:
        ordering = ('user','level',)
        db_table='degree'

    @property
    def PersianFromDate(self):
        return ConvertToSolarDate(self.from_date)
        
    @property
    def PersianToDate(self):
        return ConvertToSolarDate(self.to_date)


class Skill(models.Model):
    user=models.ForeignKey(User, blank  = False, null = False, related_name = "skills", on_delete=models.CASCADE)
    name = models.CharField(max_length = 100, blank  = False, null = False)
    level = models.SmallIntegerField(null = True)
    description = models.TextField(blank = True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('-level',)
        db_table='skill'


class Certificate(models.Model):
    user=models.ForeignKey(User, blank  = False, null = False, related_name = "certificates",on_delete = models.CASCADE)
    name = models.CharField(max_length = 100)
    mark = models.SmallIntegerField(null = True)
    organization = models.CharField(null = True, max_length = 100)
    description = models.TextField(blank = True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('pk',)
        db_table='certificate'


class JobExperience(models.Model):
    user=models.ForeignKey(User,blank  = False, null = False, related_name = "job_exps",on_delete = models.CASCADE)
    organization = models.CharField(max_length=100)
    job_title = models.CharField(max_length=100)
    from_date = models.DateField(null=True)
    to_date = models.DateField(null=True)
    description = models.TextField(blank = True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        ordering = ('from_date',)
        db_table='job_exprience'
    @property
    def PersianFromDate(self):
        return ConvertToSolarDate(self.from_date)
    @property
    def PersianToDate(self):
        return ConvertToSolarDate(self.to_date)


class DailyPerformanceReport(models.Model):
    _present = 'حاضر'
    _absent = 'غایب'
    _overtime_work = 'اضافه کار آزاد'
    _no_shifts = 'بدون شیفت'
    _holiday = 'تعطیلی' 
    _leave = 'مرخصی استحقاقی قراردادی'
    _official_leave = 'مرخصی استحقاقی رسمی'
    _official_leave_2 = 'استحقاقی رسمی'
    _treatment = 'استعلاجی قراردادی'
    _official_treatment = 'استعلاجی رسمی'
    _incentive = 'تشویقی قراردادی'
    _official_incentive = 'تشویقی رسمی'
    _on_way = 'توراهی رسمی'
    _mission = 'ماموریت روزانه'
    _birth = 'تولد فرزند رسمی'
    _death = 'مرخصی فوت بستگان درجه یک'
    value_choices=[
        (_present,'حاضر'),
        (_absent , 'غایب'),
        (_overtime_work,'اضافه کار آزاد'),
        (_no_shifts,'بدون شیفت'),
        (_holiday,'تعطیلی'),
        (_leave,'مرخصی استحقاقی قراردادی'),
        (_official_leave,'مرخصی استحقاقی رسمی'),
        (_official_leave_2,'استحقاقی رسمی'),
        (_treatment, 'استعلاجی قراردادی'),
        (_official_treatment, 'استعلاجی رسمی'),
        (_incentive, 'تشویقی قراردادی'),
        (_official_incentive, 'تشویقی رسمی'),
        (_on_way, 'توراهی رسمی'),
        (_mission, 'ماموریت روزانه'),
        (_birth, 'تولد فرزند رسمی'),
        (_death, 'مرخصی فوت بستگان درجه یک'),
    ]
    user = models.ForeignKey(User, blank = False , null = False ,on_delete = models.CASCADE, verbose_name = u'نام کاربری')
    entry1 = models.DateTimeField(blank=True,null=True,max_length=10,verbose_name = u'ورود 1')
    status = models.CharField(choices=value_choices,max_length=50,null=True,verbose_name = u'وضعیت')
    solar_date = models.CharField(blank = False, null = False, max_length = 10, verbose_name = u'تاریخ شمسی')
    g_date = models.DateField(blank = False, null=False, auto_now= True, verbose_name = u'تاریخ میلادی')
    class Meta:
        db_table = 'daily_performance_report'
        verbose_name = u'گزارش عملکرد روزانه'
        verbose_name_plural = u'گزارش عملکرد روزانه'


class MonthlyPerformanceReport(models.Model):
    _farvardin=1
    _ordibehesht=2
    _khordad=3
    _tir=4
    _mordad=5
    _shahrivar=6
    _mehr=7
    _aban=8
    _azar=9
    _dey=10
    _bahman=11
    _esfand=12
    value_choices=(
        (_farvardin,'فروردین'),
        (_ordibehesht,'اردیبهشت'),
        (_khordad,'خرداد'),
        (_tir,'تیر'),
        (_mordad,'مرداد'),
        (_shahrivar,'شهریور'),
        (_mehr,'مهر'),
        (_aban,'آبان'),
        (_azar,'آذر'),
        (_dey,'دی'),
        (_bahman,'بهمن'),
        (_esfand,'اسفند'),
    )
    user = models.ForeignKey(User, blank = False, null = False, on_delete=models.CASCADE, verbose_name = u'نام کاربری')
    solar_month = models.SmallIntegerField(choices = value_choices, blank = False, null = False, verbose_name = u'ماه')
    solar_year = models.SmallIntegerField(blank = False, null = False, verbose_name = u'سال شمسی')
    entry_sum_duration = models.DurationField(blank = True, null = True, verbose_name = u'جمع ساعات ورودی')
    presence_duration = models.DurationField(blank = True, null = True, verbose_name = u'جمع ساعات حضور')
    performance_duration = models.DurationField(blank = True, null = True, verbose_name = u'جمع ساعات کارکرد')
    leave_hours_duration = models.DurationField(blank = True, null = True, verbose_name = u'جمع ساعات مرخصی')
    delay_hours_duration = models.DurationField(blank = True, null = True, verbose_name = u'جمع ساعات تاخیر')
    delay_count = models.SmallIntegerField(blank = True, null = True, default = 0, verbose_name=u'تعداد روزهای دارای تاخیر')
    rush_hours_duration = models.DurationField(blank = True, null = True, verbose_name = u'جمع ساعات تعجیل')
    lowtime_duration = models.DurationField(blank = True, null = True, verbose_name = u'جمع ساعات کسر کار')
    overtime_duration = models.DurationField(blank = True, null = True, verbose_name = u'اضافه کار')
    holiday_overtime_duration = models.DurationField(blank = True, null = True, verbose_name = u'اضافه تعطیلی')
    month_days = models.SmallIntegerField(blank = False, null = False, verbose_name = u'تعداد روز یکماه')
    month_holidays = models.SmallIntegerField(blank = False, null = False, verbose_name = u'تعداد تعطیلی یکماه')
    class Meta:
        db_table = 'monthly_performance_report'
        verbose_name = u'گزارش عملکرد ماهانه'
        verbose_name_plural = u'گزارش عملکرد ماهانه'
    

class MonthlyCommentAboutEmployee(models.Model):
    user = models.ForeignKey(User,blank  = True,null=True,on_delete=models.CASCADE)
    comment = models.TextField(blank = True)
    five_s = models.SmallIntegerField(null=True,default=0)
    month = models.SmallIntegerField(null=True)
    year = models.SmallIntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        db_table='monthly_comment_about_employee'
        ordering = ('year','month',)
        verbose_name = u'نظرات ماهانه مدیران'
        verbose_name_plural = u'نظرات ماهانه مدیران'
    def __str__(self):
        return self.user.first_name + " " +self.user.last_name + "  " + str(self.year) +"/" + str(self.month)


class EvaluationCriteriaGroup(models.Model):
    name = models.CharField(blank=True,null=True,max_length=200, unique = True, verbose_name=u'نام')
    managers_special = models.BooleanField(default=False ,verbose_name=u'مخصوص مدیران')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        db_table='evaluation_criteria_group'
        ordering = ('name',)
        verbose_name = u'دسته بندی شاخص های ارزیابی'
        verbose_name_plural = u'دسته بندی شاخص های ارزیابی'

    def __str__(self):
        return self.name


class EvaluationCriteria(models.Model):
    name = models.CharField(blank=True,null=True,max_length=200,verbose_name=u'نام')
    description = models.TextField(blank=True,null=True,verbose_name=u'توضیحات')
    group = models.ForeignKey(EvaluationCriteriaGroup, blank = True, null=True, related_name='group_criterias', on_delete=models.CASCADE, verbose_name=u'گروه')
    weight = models.SmallIntegerField(null=True, blank = True, verbose_name=u'وزن')
    # headmaster
    evaluated_by_headmaster = models.BooleanField(default=False,blank = True, verbose_name=u'ارزیابی مدیر غیر مستقیم')
    evaluation_by_headmaster_weight = models.SmallIntegerField(null=True,blank = True, verbose_name=u'وزن ارزیابی مدیر غیر مستقیم ')
    evaluation_by_headmaster_nullable = models.BooleanField(default=False, verbose_name=u'ارزیابی مدیر غیر مستقیم می تواند خالی باشد')
    # manager
    evaluated_by_manager = models.BooleanField(default=False,blank = True, verbose_name=u'ارزیابی مدیر')
    evaluation_by_manager_weight = models.SmallIntegerField(null=True,blank = True, verbose_name=u'وزن ارزیابی مدیر ')
    evaluation_by_manager_nullable = models.BooleanField(default=False, verbose_name=u'ارزیابی مدیر می تواند خالی باشد')
    # sibling
    evaluated_by_siblings = models.BooleanField(default=False, verbose_name=u'ارزیابی همکاران')
    evaluation_by_siblings_weight = models.SmallIntegerField(null=True, blank = True, verbose_name=u'وزن ارزیابی همکاران')
    evaluation_by_siblings_nullable = models.BooleanField(default=False, verbose_name=u'ارزیابی همکاران می تواند خالی باشد')
    # subaltern
    evaluated_by_subaltern = models.BooleanField(default=False, verbose_name=u'ارزیابی زیرمجموعه')
    evaluation_by_subaltern_weight = models.SmallIntegerField(null=True, blank = True, verbose_name=u'وزن ارزیابی زیر مجموعه')
    evaluation_by_subaltern_nullable = models.BooleanField(default=False, verbose_name=u'ارزیابی زیرمجموعه می تواند خالی باشد')
    #staff
    evaluated_by_staff = models.BooleanField(default=False, verbose_name=u'ارزیابی ستاد')
    evaluation_by_staff_weight = models.SmallIntegerField(null=True, blank = True, verbose_name=u'وزن ارزیابی ستاد')
    evaluation_by_staff_nullable = models.BooleanField(default=False, verbose_name=u'ارزیابی ستاد می تواند خالی باشد')
    #all
    evaluated_by_all = models.BooleanField(default=False, verbose_name=u'ارزیابی همه')
    evaluation_by_all_weight = models.SmallIntegerField(null=True, blank = True, verbose_name=u'وزن ارزیابی همه')
    evaluation_by_all_nullable = models.BooleanField(default=False, verbose_name=u'ارزیابی همه می تواند خالی باشد')

    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        db_table='evaluation_criteria'
        ordering = ('group','name',)
        verbose_name = u'شاخص های ارزیابی'
        verbose_name_plural = u'شاخص های ارزیابی'
        unique_together = ('name', 'group', )

    def __str__(self):
        return self.name


class EvaluationConsquenseType(models.Model):
    name = models.CharField(max_length = 50, null = False, blank = False, unique = True, verbose_name=u'عنوان')
    color_code = models.CharField(max_length=10, null = False, blank = False, unique = True, verbose_name=u'کد رنگ')
    unimportant = models.BooleanField(default = False, null = False, blank = False, verbose_name=u'کم اهمیت')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        db_table='evaluation_consequence_type'
        ordering = ('name',)
        verbose_name = u'نوع عواقب ارزیابی'
        verbose_name_plural = u'انواع عواقب ارزیابی'

    def __str__(self):
        return self.name


class EvaluationNote(models.Model):
    note = models.TextField(blank = True, null = True, verbose_name=u'یادداشت' )
    evaluator = models.ForeignKey(User,blank  = True,null=True,related_name='note_evaluator',on_delete=models.SET_NULL, verbose_name=u'نویسنده یادداشت')
    evaluatee = models.ForeignKey(User,blank  = True,null=True,related_name='note_evaluatee',on_delete=models.SET_NULL, verbose_name=u'یادداشت راجع به ')
    criteria = models.ForeignKey(EvaluationCriteria,blank = True, null=True, related_name='criteria_note', on_delete=models.SET_NULL, verbose_name=u'شاخص')
    consequence_amount = models.IntegerField(blank = True, null = True, verbose_name=u'اندازه کمی عواقب')
    month = models.SmallIntegerField(null=True, verbose_name=u'ماه')
    year = models.SmallIntegerField(null=True, verbose_name=u'سال')
    private = models.BooleanField(default=False, verbose_name=u'نمایش فقط برای نویسنده') 
    show_to_all =  models.BooleanField(default=False, verbose_name=u'نمایش برای دیگران') 
    # private & show_to_all : only evaluatee and evaluator
    # private & ~show_to_all : only evaluator
    # ~private & show_to_all : all
    # ~private & ~show_to_all : only evaluatee and managers
    consequence_type = models.ForeignKey(EvaluationConsquenseType, null = True, on_delete=models.SET_NULL, verbose_name=u'نوع عواقب ارزیابی')
    staff_note = models.BooleanField(default = False)



    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        db_table='evaluation_note'
        ordering = ('criteria',)
        verbose_name = u'یادداشت های ارزیابی'
        verbose_name_plural = u'یادداشت های ارزیابی'

    def __str__(self):
        return self.note

    @property
    def jcreated(self):
        return jdt.fromgregorian(date = self.created.date()).strftime(format='%Y/%m/%d')

    @property
    def jupdated(self):
        return jdt.fromgregorian(date = self.updated.date()).strftime(format='%Y/%m/%d')


class EvaluationLog(models.Model):
    score = models.SmallIntegerField(blank = False, null = False)
    # 1 , 2 , 3 , 4 , 5  from the least to the best
    evaluator = models.ForeignKey(User, blank  = True,null = True, related_name = 'evaluator_log', on_delete = models.SET_NULL)
    evaluatee = models.ForeignKey(User, blank  = False, null = False, related_name = 'evaluatee_log', on_delete = models.CASCADE)
    criteria = models.ForeignKey(EvaluationCriteria,blank = False, null = False, on_delete=models.CASCADE, related_name='evaluation_log')
    evaluation_relation = models.SmallIntegerField(blank = False, null = False)
    # 0 manager 
    # 1 sibling 
    # 2 subaltern 
    # 3 staff 
    # 4 undirect manager
    # 5 unrelated
    relation_weight = models.SmallIntegerField(blank = False, null = False)
    evaluation_month = models.SmallIntegerField(null=True)
    evaluation_year = models.SmallIntegerField(null=True)
    staff_log = models.BooleanField(default = False)

    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        db_table='evaluation_log'
        ordering = ('criteria',)
        unique_together = ('evaluator', 'evaluatee', 'criteria', 'evaluation_year', 'evaluation_month','staff_log' )

    def __str__(self):
        return str(self.score) + '-' + self.evaluator.get_full_name() + '-' + self.evaluatee.get_full_name()
    

class EvaluationCriteriaGroupWeight(models.Model):
    criteria_group = models.ForeignKey(EvaluationCriteriaGroup, blank = False, null = False, related_name = 'org_group_weights', on_delete = models.CASCADE)
    org_group = models.ForeignKey(Organization_Group, blank = False, null = False, related_name = 'evaluation_group_weights', on_delete = models.CASCADE)
    weight = models.SmallIntegerField(default = 1, blank = False , null = False)

    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        db_table='evaluation_criteria_group_weight'
        verbose_name = u'وزن دسته های ارزیابی برای گروه ها'
        verbose_name_plural = u'وزن های دسته های ارزیابی برای گروه ها'
        unique_together = ('criteria_group', 'org_group',)

    def __str__(self):
        return self.criteria_group.name + ' ' + self.org_group.name


class AutoEvaluationCriteria(models.Model):
    value_type_choices = (
        (1,'زمان'),
        (2,'عدد'),
    )
    name = models.CharField(blank = False, null = False, max_length=200, unique = True, verbose_name = u'نام')
    value_type = models.SmallIntegerField(null=False, default = 2 , verbose_name=u'نوع', choices = value_type_choices)
    # 1  time
    # 2  int
    criteria = models.ForeignKey(EvaluationCriteria,blank = True, null = True, on_delete=models.CASCADE, related_name='criteria_auto', verbose_name = u'شاخص عادی')
    manager_criteria = models.ForeignKey(EvaluationCriteria,blank = True, null = True, on_delete=models.CASCADE, related_name='manager_criteria_auto', verbose_name = u'شاخص مدیران')
    slug = models.SlugField(null= True, unique = True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='auto_evaluation_criteria'
        ordering = ('name',)
        verbose_name = u'شاخص های محاسبه شونده خودکار'
        verbose_name_plural = u'شاخص های محاسبه شونده خودکار'

    def __str__(self):
        return self.name


class AutoEvaluationLog(models.Model):
    evaluatee = models.ForeignKey(User,blank  = False, null = False, on_delete = models.CASCADE)
    auto_criteria = models.ForeignKey(AutoEvaluationCriteria, blank = False, null = False, on_delete = models.CASCADE, related_name = 'auto_criteria_logs')
    int_value = models.IntegerField(null = True, blank = True)
    time_value_duration = models.DurationField(null = True, blank = True)
    month = models.SmallIntegerField(blank = False, null = False)
    year = models.SmallIntegerField(blank = False, null = False)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='auto_evaluation_log'
        ordering = ('auto_criteria',)
        unique_together = ('evaluatee', 'auto_criteria', 'year', 'month',)
    def __str__(self):
        return self.evaluatee.first_name + " " + self.evaluatee.last_name + "  " + str(self.year) + "/" + str(self.month)

    @property
    def time_value_duration_str(self):
        hours = 0
        minutes = 0
        if self.time_value_duration.days > 0:
            hours += self.time_value_duration.days * 24
        hours += int(self.time_value_duration.seconds / 3600)
        minutes = int((self.time_value_duration.seconds % 3600)/60)
        return str(hours) + ':' + str(minutes)


class SyntheticEvaluationCriteria(models.Model):
    name = models.CharField(null= False, blank= False, max_length= 100, verbose_name=u'نام')
    criterias = models.ManyToManyField(EvaluationCriteria, related_name='synthetic_criterias', verbose_name = u'شاخص های مرتبط')

    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)
    class Meta:
        db_table='synthetic_evaluation_criteria'
        ordering = ('name',)
        verbose_name = u'شاخص ترکیبی'
        verbose_name_plural = u'شاخص های ترکیبی'

    def __str__(self):
        return str(self.name)

class Currency(models.Model):
    title = models.CharField(max_length= 10, blank= False, null= False, unique= True, verbose_name = u'عنوان واحد ارزی')
    rialratio = models.DecimalField(max_digits = 15, decimal_places = 5 , blank= False, null= False, verbose_name = u'یک واحد از این ارز چند ریال است؟')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    @cached_property
    def Remain(self):
        wallets = Wallet.objects.filter(currency=self)
        result = 0
        for wal in wallets :
            result += wal.current_balance
        
        return result

    class Meta:
        db_table='currency'
        ordering = ('title',)
        verbose_name = u'واحد ارزی'
        verbose_name_plural = u'واحدهای ارزی'

    def __str__(self):
        return self.title

class Wallet(models.Model):
    name = models.CharField(max_length = 50, blank= False, null= False, unique= True, verbose_name = u'نام منبع')
    currency = models.ForeignKey(Currency, blank = False, null = False, on_delete = models.CASCADE, verbose_name = u'واحد ارزی منبع')
    identifier = models.CharField(max_length = 50, blank= False, null= False, unique= True, verbose_name = u'شناسه یا شماره حساب')
    provider = models.CharField(max_length = 50, blank= False, null= False, verbose_name = u'ارائه کننده')

    initial_balance = models.DecimalField(max_digits = 30, decimal_places = 15 , blank= False, null= False, default= 0, verbose_name = u'موجودی اولیه')
    current_balance_d = models.DecimalField(max_digits = 30, decimal_places = 15 , blank= False, null= False, default= 0, verbose_name = u'موجودی فعلی')

    type_choice = (
        (0, 'کارت'),
        (1, 'کیف پول'),
    )
    wallet_type = models.SmallIntegerField(choices = type_choice, default = 0, blank = False, null = False, verbose_name = u'نوع منبع مالی')
    password = models.CharField(max_length = 100, null = True, blank= True, verbose_name = u'رمز کیف پول')

    card_cvv2 = models.SmallIntegerField(null = True, blank= True, verbose_name = u'cvv2 کارت')
    card_expire = models.CharField(max_length = 5, null = True, blank= True, verbose_name = u'تاریخ انقضا کارت')
    active = models.BooleanField(default = True, blank = False, null = False, verbose_name = u'فعال')
    deliver_date = models.DateField(default=datetime.date.today,blank = False, null = False, verbose_name = u'تاریخ تحویل گرفتن')
    deliver_receipt = models.FileField(upload_to = user_receipt_directory_path, null = True, blank=True , verbose_name= u'رسید تحویل گرفتن')
    creator = models.ForeignKey(User, default = 2, blank = False, null = False, on_delete = models.PROTECT, verbose_name= u'کاربر ثبت کننده')
    description = models.CharField(max_length = 250, blank= True, null= True, unique= True, verbose_name = u'توضیحات')
    key_image = models.FileField(upload_to = user_receipt_directory_path, null = True, blank=True , verbose_name= u'تصویر کلید')
    master = models.BooleanField(default = True, blank = False, null = False, verbose_name = u'اصلی')
    archived = models.BooleanField(default = True, blank = False, null = False, verbose_name = u'بایگانی شده')
    op_area = models.ForeignKey(OPArea, blank=True, null=True, on_delete=models.PROTECT, related_name = "wallets", verbose_name = u'محور عملیاتی مربوطه')
    op_project = models.ForeignKey(OPProject, blank=True, null=True, on_delete=models.PROTECT, related_name = "wallets", verbose_name = u'پروژه عملیاتی مربوطه')
    
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='wallet'
        ordering = ('-current_balance_d',)
        verbose_name = u'کارت یا کیف پول'
        verbose_name_plural = u'کارت ها و کیف پول ها'

    def __str__(self):
        return self.name

    @cached_property
    def current_balance(self):
        result = self.initial_balance
        transaction_before = Transaction.objects.filter(wallet = self)
        for trans in transaction_before :
            if trans.incordec :
                result -= (trans.amount + trans.fee)
            else :
                result += trans.amount

        return result

    def current_balance_payoff(self, payoff_wal_id):
        result = self.initial_balance
        if self.pay_offs.all().count() > 0:
            result = self.pay_offs.all().order_by('-pk').first().balance_after
        transaction_before = Transaction.objects.filter(wallet = self, payoff_wallet__id = payoff_wal_id)
        for trans in transaction_before :
            if trans.incordec :
                result -= (trans.amount + trans.fee)
            else :
                result += trans.amount

        return result


class PayOff(models.Model):
    title = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name=u"عنوان تسویه")
    wallet = models.ForeignKey(Wallet,on_delete=models.PROTECT, blank=False , null=False, verbose_name=u"کیف پول مربوطه", related_name = 'pay_offs')
    date = models.DateField(blank = True, null = True, verbose_name=u"تاریخ انجام تسویه")
    image = models.FileField(upload_to = user_receipt_directory_path, null = True, blank=True , verbose_name= u'تصویر رسید تسویه')
    amount = models.DecimalField(max_digits = 30, decimal_places = 15 , blank= False, null= False, verbose_name = u'مبلغ تسویه')
    balance_after = models.DecimalField(max_digits = 30, decimal_places = 15 , blank= False, null= False, verbose_name = u'موجودی حساب بعد از تسویه')
    creator = models.ForeignKey(User, blank = False, null = False, on_delete = models.PROTECT, verbose_name= u'کاربر ثبت کننده تسویه')
    comment = models.TextField(verbose_name= u'توضیحات', null = True, blank= True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='wallet_payoff'
        ordering = ('-created',)
        verbose_name = u'تسویه'
        verbose_name_plural = u'تسویه ها'

    @property
    def PersianDate(self):
        return ConvertToSolarDate(self.date)

class Transaction(models.Model):
    inordec_choices = (
        (0 , 'واریز'),
        (1 , 'برداشت'),
    )
    title = models.CharField(max_length=30,blank=True, null= True, verbose_name=u"عنوان")
    amount = models.DecimalField(max_digits = 30, decimal_places = 15 , blank= False, null= False, verbose_name = u'مبلغ تراکنش')
    amount_dollar = models.DecimalField(max_digits = 30, decimal_places = 15 , blank= True, null= True, default=0, verbose_name = u'مبلغ دلاری تراکنش')
    time = models.DateTimeField(blank = False, null = False, verbose_name = u'زمان انجام تراکنش')
    incordec = models.SmallIntegerField(blank = False, null = False, choices = inordec_choices , verbose_name = u'واریز یا برداشت بودن تراکنش')
    wallet = models.ForeignKey(Wallet, blank = False, null = False, on_delete = models.CASCADE, verbose_name = u'کیف پول مربوطه')
    wallet_balance_after_d = models.DecimalField(max_digits = 30, decimal_places = 15 , blank= False, null= False, verbose_name = u'موجودی حساب بعد از تراکنش')
    live_ratio = models.DecimalField(max_digits = 15, decimal_places = 5 , blank= True, null= True, verbose_name = u'ارزش واحد پول به ریال موقع انجام تراکنش')
    fee = models.DecimalField(max_digits = 30, decimal_places = 15 , blank= False, null= False, default= 0, verbose_name = u'کارمزد تراکنش')
    fee_dollar = models.DecimalField(max_digits = 30, decimal_places = 15 , blank= True, null= True, default= 0, verbose_name = u'کارمزد دلاری تراکنش')
    receipt_file = models.FileField(upload_to = user_receipt_directory_path, null = False, blank=False, verbose_name = u'تصویر رسید تراکنش')
    receipt_file_name = models.CharField(max_length=512, blank=True, null=True)
    dest_resource = models.ForeignKey(Resource, on_delete = models.PROTECT, verbose_name= u'منیع مرتبط با تراکنش', null = True, blank= True)
    source_transaction = models.OneToOneField('self', on_delete = models.PROTECT, verbose_name = u'تراکنش برداشت متناظر با واریز', null = True, blank= True, related_name='dest_transaction')
    comment = models.TextField(verbose_name= u'توضیحات', null = True, blank= True)
    creator = models.ForeignKey(User, blank = False, null = False, on_delete = models.PROTECT, verbose_name= u'کاربر ثبت کننده تراکنش')
    payoff_wallet = models.ForeignKey(Wallet, blank = False, null = False, on_delete=models.PROTECT, related_name="payoff_trans")
    payed_off = models.BooleanField(default=False,verbose_name="تسویه شده")
    pay_off = models.ForeignKey(PayOff,blank=True, null=True, on_delete=models.PROTECT, related_name="transactions", verbose_name="تسویه مرتبط")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='wallet_transaction'
        ordering = ('-time',)
        verbose_name = u'تراکنش'
        verbose_name_plural = u'تراکنش ها'

    @cached_property
    def wallet_balance_after(self):
        transaction_before = Transaction.objects.filter(time__lte = self.time, wallet = self.wallet)
        result = self.wallet.initial_balance
        for trans in transaction_before :
            if trans.incordec :
                result -= (trans.amount + trans.fee)
            else :
                result += trans.amount

        return result

    def __str__(self):
        return str(self.amount)

class TransactionAdditionalReceipt(models.Model):
    transaction = models.ForeignKey(Transaction, blank= False , null=False, on_delete=models.CASCADE, related_name='additional_receipts')
    receipt_file = models.FileField(upload_to = user_receipt_directory_path, null = False, blank=False, verbose_name = u'تصویر رسید تراکنش')
    receipt_file_name = models.CharField(max_length=512, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table='wallet_transaction_receipt'
        ordering = ('-transaction',)
        verbose_name = u'تصاویر تراکنش'
        verbose_name_plural = u'تصاویر تراکنش ها'
    
class FeedbackType(models.Model):
    name = models.CharField(max_length=100, unique= True, blank= False, null = False, verbose_name=u'عنوان نوع بازخورد')
    has_value = models.BooleanField(default= False , verbose_name=u'بازخورد دارای اندازه عددی')
    value_unit = models.CharField(max_length=20 , blank= True , null= True, verbose_name=u'واحد اندازه عددی')
    needs_verification = models.BooleanField(default= False, verbose_name=u'نیازمند تایید')
    needs_investigation = models.BooleanField(default= False, verbose_name=u'نیازمند رسیدگی برای اعمال')
    investigator = models.ForeignKey(User, blank = True, null = True, on_delete = models.PROTECT, verbose_name= u'مسئول رسیدگی')
    color_code = models.CharField(max_length=10, null = False, blank = False,  default='green', verbose_name=u'کد رنگ')
    pos_or_neg = models.BooleanField(default= True, verbose_name=u'بازخورد مثبت')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='feedback_type'
        ordering = ('name',)
        verbose_name = u'نوع بازخورد'
        verbose_name_plural = u'انواع بازخورد'

    def __str__(self):
        return self.name

class Feedback(models.Model):
    feedback_type = models.ForeignKey(FeedbackType, blank = False, null = False, on_delete= models.CASCADE, verbose_name=u'نوع بازخورد')
    user = models.ForeignKey(User, blank = False, null = False, related_name='feedbacks', on_delete= models.CASCADE, verbose_name=u'کاربر مورد درخواست بازخورد')
    requester = models.ForeignKey(User, blank = False, null = False, related_name='requested_feedbacks', on_delete= models.CASCADE, verbose_name=u'درخواست کننده بازخورد')
    title = models.CharField(max_length= 100, blank= False, null = False, verbose_name=u'عنوان یا دلیل بازخورد')
    description = models.TextField(blank= True, null= False, verbose_name=u'توضیح درخواست کننده')
    value = models.IntegerField(blank= True, null= True, verbose_name=u'مقدار بازخورد')
    comment = models.TextField(blank= True, null = True, verbose_name=u'نظر ستاد')
    verified = models.BooleanField(default= False, verbose_name=u'تایید شده توسط مدیر')
    rejected = models.BooleanField(default= False, verbose_name=u'رد شده توسط مدیر')
    ver_rej_date = models.DateTimeField(blank = True, null = True, verbose_name=u'زمان تایید یا رد مدیر')
    investigated = models.BooleanField(default= False, verbose_name=u'رسیدگی شده')
    investigation_comment = models.TextField(blank= True, null = True, verbose_name=u'توضیحات رسیدگی')
    invest_date = models.DateTimeField(blank = True, null = True, verbose_name=u'زمان اتمام رسیدگی')
    seen = models.BooleanField(default= False, verbose_name=u'دیده شده')

    logs = models.ManyToManyField(EvaluationLog, related_name='log_feedbacks', db_table='feedback_evaluation_log')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='feedback'
        ordering = ('updated',)
        verbose_name = u'بازخورد'
        verbose_name_plural = u'بازخوردها'

    def __str__(self):
        return self.user.get_full_name() + '-' + self.title
    
    @property
    def PersianCreationDate(self):
        return ConvertToSolarDate(self.created)

    @property
    def PersianVerRejDate(self):
        try:
            return ConvertToSolarDate(self.ver_rej_date)
        except:
            return ""

    @property
    def PersianInvestDate(self):
        try:
            return ConvertToSolarDate(self.invest_date)
        except:
            return ""


class Regulation(models.Model):
    title = models.CharField(max_length= 50, null= False, blank= False, verbose_name=u'عنوان')
    content = RichTextUploadingField(null= True, blank= True,verbose_name=u'متن')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='regulation'
        ordering = ('title',)
        verbose_name = u'آیین نامه'
        verbose_name_plural = u'آیین نامه ها'

    @property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)

    def __str__(self):
        return  self.title


class Challenge(models.Model):
    title=models.CharField(blank  = True,null=True,max_length=100, verbose_name=u'عنوان')
    content= RichTextUploadingField(blank  = True,null=True, verbose_name=u'متن' )
    user = models.ForeignKey(User, blank = False, null = False, related_name='challenge', on_delete= models.CASCADE, verbose_name=u'نویسنده')
    public_access = models.BooleanField(default=False, verbose_name=u'عمومی')
    importance = models.IntegerField(blank= True, null= True, verbose_name=u'درجه اهمیت')
    # max = 4   and  min = 1
    situation = models.IntegerField(blank= True, null= True, verbose_name=u'وضعیت')
    # 1 : without solution
    # 2 : with solution
    # 3 : solved
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        ordering = ('created',)
        db_table='challenge'

    @property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)

    @property
    def CommentsNumber(self):
        _commments = ChallengeComment.objects.filter(challenge = self)
        _number = len(_commments)
        return _number


    @property
    def SolutionsNumber(self):
        _solutions = ChallengeSolution.objects.filter(challenge = self)
        _number = len(_solutions)
        return _number

    @property
    def SameChallengeNumber(self):
        _same = SameChallenge.objects.filter(challenge = self)
        _number = len(_same)
        return _number

    def __str__(self):
        return self.title
    
class ChallengeSolution(models.Model):
    challenge = models.ForeignKey(Challenge, blank = False, null = False, related_name='challenge_solution', on_delete= models.CASCADE, verbose_name=u'چالش')
    content= RichTextUploadingField(blank  = True,null=True, verbose_name=u'متن' )
    user = models.ForeignKey(User, blank = False, null = False, related_name='challenge_solution', on_delete= models.CASCADE, verbose_name=u'نویسنده')
    confirmed_by_auther = models.BooleanField(default=False, verbose_name=u'حل شده')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        ordering = ('created',)
        db_table='challenge_solution'

    @property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)

    @property
    def AgreeVote(self):
        _votes = SolutionVote.objects.filter(solution = self,value = 1)
        _number = len(_votes)
        return _number

    @property
    def DisAgreeVote(self):
        _votes = SolutionVote.objects.filter(solution = self,value = -1)
        _number = len(_votes)
        return _number * -1

    def __str__(self):
        return self.content

class ChallengeComment(models.Model):
    challenge = models.ForeignKey(Challenge, blank = False, null = False, related_name='challenge_comment', on_delete= models.CASCADE, verbose_name=u'چالش')
    content= RichTextUploadingField(blank  = True,null=True, verbose_name=u'متن' )
    user = models.ForeignKey(User, blank = False, null = False, related_name='challenge_comment', on_delete= models.CASCADE, verbose_name=u'نویسنده')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        ordering = ('created',)
        db_table='challenge_comment'

    @property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)


    def __str__(self):
        return self.content

class SolutionComment(models.Model):
    solution = models.ForeignKey(ChallengeSolution, blank = False, null = False, related_name='solution_comment', on_delete= models.CASCADE, verbose_name=u'راه کار')
    content= RichTextUploadingField(blank  = True,null=True, verbose_name=u'متن' )
    user = models.ForeignKey(User, blank = False, null = False, related_name='solution_comment', on_delete= models.CASCADE, verbose_name=u'نویسنده')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        ordering = ('created',)
        db_table='solution_comment'

    @property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)

    def __str__(self):
        return self.content


class SameChallenge(models.Model):
    challenge = models.ForeignKey(Challenge, blank = False, null = False, related_name='same_challenge', on_delete= models.CASCADE, verbose_name=u'راه کار')
    user = models.ForeignKey(User, blank = False, null = False, related_name='same_challenge', on_delete= models.CASCADE, verbose_name=u'نویسنده')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        ordering = ('created',)
        db_table='same_challenge'

    @property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)

    def __str__(self):
        return self.challenge

class SolutionVote(models.Model):
    solution = models.ForeignKey(ChallengeSolution, blank = False, null = False, related_name='solution_vote', on_delete= models.CASCADE, verbose_name=u'راه کار')
    user = models.ForeignKey(User, blank = False, null = False, related_name='solution_vote', on_delete= models.CASCADE, verbose_name=u'نویسنده')
    value = models.IntegerField(blank= True, null= True, verbose_name=u'رای')
    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        ordering = ('created',)
        db_table='solution_vote'

    @property
    def PersianCreateDate(self):
        return ConvertToSolarDate(self.created)

    def __str__(self):
        return self.value


class MonthStatistic(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="statistics")
    year = models.SmallIntegerField()
    month = models.SmallIntegerField()

    worked = models.SmallIntegerField()
    absent = models.SmallIntegerField()
    mission = models.SmallIntegerField()
    leave_right = models.DecimalField(max_digits = 6, decimal_places = 2)
    leave_sick = models.SmallIntegerField()
    leave_reward = models.DecimalField(max_digits = 6, decimal_places = 2)
    leave_child = models.SmallIntegerField()
    leave_die = models.SmallIntegerField()
    undertime = models.SmallIntegerField()
    overtime_min = models.SmallIntegerField()
    overtime_hour = models.SmallIntegerField()
    overtime_night = models.SmallIntegerField()
    quality = models.SmallIntegerField()
    overtime_quality = models.SmallIntegerField()
    teleworking = models.SmallIntegerField()
    food = models.SmallIntegerField()
    overtime_limit = models.SmallIntegerField()
    undertime_day = models.SmallIntegerField()

    created = models.DateTimeField(auto_now_add=True,null=True)
    updated = models.DateTimeField(auto_now=True,null=True)

    class Meta:
        ordering = ('created',)
        db_table='month_statistic'
        unique_together = ('user', 'year', 'month',)