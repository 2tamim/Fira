from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import Task,Task_Attachment
from django.http import JsonResponse
from django.core import serializers
from django.core.exceptions import PermissionDenied

@login_required(login_url='user:login') #redirect when user is not logged in
def add(request,id):
    data={}
    _user = request.user
    if request.method=="POST":
        _user = request.user
        task=Task.objects.get(pk=id)
        if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
            as_user = request.user.locumtenens_organization_groups.first().manager
        else:
            as_user = request.user

        under_task_group_access = False
        if (task.UnderTaskGroup and ( _user ==  task.UnderTaskGroup.head or task.id in  _user.employee.UnderTaskGroupTasks)):
            under_task_group_access = True
        if (task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet) or under_task_group_access):
            try:
                attachment=Task_Attachment()
                if 'task_edit_attachment_modal_file_input' in request.FILES:
                    _file=request.FILES['task_edit_attachment_modal_file_input']
                    attachment.attachment_file = _file
                    attachment.filename=request.POST["task_edit_attachment_modal_filename"]
                    attachment.name = request.POST["task_edit_attachment_modal_title"]
                    attachment.user=request.user
                    attachment.task=task
                    attachment.save()
                    data['message']="فایل با موفقیت ذخیره شد"
                    
                elif 'task_profile_attachment_modal_file_input' in request.FILES:
                    _file=request.FILES['task_profile_attachment_modal_file_input']
                    attachment.attachment_file = _file
                    attachment.filename=request.POST["task_profile_attachment_modal_filename"]
                    attachment.name = request.POST["task_profile_attachment_modal_title"]
                    attachment.user=request.user
                    attachment.task=task
                    attachment.save()
                    data['message']="فایل با موفقیت ذخیره شد"                   
                else:
                    data['message']="فایلی جهت ارسال انتخاب نشده است"
                
            except Exception as err:
                data['message']=err.args[0]

        else:
            raise PermissionDenied
            
        
    return JsonResponse(data)



@login_required(login_url='user:login') #redirect when user is not logged in
def tolist(request,id):
    data={}
    try:
        task=Task.objects.get(pk=id)
        if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
            as_user = request.user.locumtenens_organization_groups.first().manager
        else:
            as_user = request.user

        under_task_group_access = False
        if (task.UnderTaskGroup and ( _user ==  task.UnderTaskGroup.head or task.id in  _user.employee.UnderTaskGroupTasks)):
            under_task_group_access = True
        if (task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet) or under_task_group_access or \
            task.id in as_user.employee.CopyFromAccessTasks ):
            _files=serializers.serialize('json',Task_Attachment.objects.filter(task_id=id))
            data["files"]=_files
        else:
            raise PermissionDenied
        
    except Exception as err:
        data['message']=err.args[0]
            
        
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def socialtolist(request,id):
    data={}
    try:
        task=Task.objects.get(pk=id)
        if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
            as_user = request.user.locumtenens_organization_groups.first().manager
        else:
            as_user = request.user

        under_task_group_access = False
        if (task.UnderTaskGroup and ( _user ==  task.UnderTaskGroup.head or task.id in  _user.employee.UnderTaskGroupTasks)):
            under_task_group_access = True
        if (task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet) or under_task_group_access or \
            task.id in as_user.employee.CopyFromAccessTasks ):
            _files=Task_Attachment.objects.filter(task_id=id)
            pictures = []
            notpicture = []
            picture_extension = ["jpg","png","jpeg"]
            for i in _files:
                if i.filename.split(".")[-1].lower() in picture_extension:
                    pictures.append(i)
                else:
                    notpicture.append(i)
            data["files"]=serializers.serialize( 'json' , notpicture )
            data["pictures"] = serializers.serialize( 'json' , pictures )
            
        else:
            raise PermissionDenied
        
    except Exception as err:
        data['message']=err.args[0]
            
        
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def delete(request,id):
    data={}
    try:
        _user = request.user
        _task_file=Task_Attachment.objects.get(pk=id)
        if _task_file.user == _user :
            _task_file=Task_Attachment.objects.get(pk=id)
            _task_file.attachment_file.delete()
            _task_file.delete()
            data["message"]="حذف با موفقیت انجام شد"
        else:
            raise PermissionDenied
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)