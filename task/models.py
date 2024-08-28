from django.db import models

# Create your models here.
from Tadbir3_app.models import Task, Task_Type, Task_Assign_Request, User, Task_Type_State, Task_Type_Property,\
     Task_Property_Num, Task_Property_Text, Task_Property_Bool, Task_Property_Date,Task_Property_File, Task_Type_Auto_Request,\
        Task_Attachment, Task_Type_Verification, Task_Verification_Log, TaskProgress, TaskComment, Subtask



class TaskExtend(models.Model):
   task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="extends")
   previous_deadline = models.DateField()
   requested_deadline = models.DateField()
   description = models.TextField()
   rejected = models.BooleanField(default=False)
   accepted_deadline = models.DateField(blank=True, null=True)

   class Meta:
        db_table='task_extend'