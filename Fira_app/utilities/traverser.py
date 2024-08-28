from ..models import Task,Employee,Organization_Group
from django.contrib.auth.models import User
def GetTaskChildrenSet(_task_id):
    children_set=set()
    parent_set=set()
    parent_set.add(_task_id)
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


def GetEmployeeParentSet(_user_id):
    parent_set=set()
    try:
        employee=Employee.objects.get(user__id=_user_id)
        if (employee.organization_group==None):
            return parent_set
        group=Organization_Group.objects.get(pk=employee.organization_group.id)
        if (group.manager==None):
            return parent_set

        while(group.manager):
            parent_set.add(group.manager.id)
            group=Organization_Group.objects.get(pk=group.group_parent.id)
        return parent_set
    except:
        return parent_set


def GetEmployeeParent(_user_id):
    try:
        employee=Employee.objects.get(user__id=_user_id)
        if (employee.organization_group==None):
            return None
        group=Organization_Group.objects.get(pk=employee.organization_group.id)
        if (group.manager==None):
            return None
        else:
            return group.manager.id
    except:
        return None
    