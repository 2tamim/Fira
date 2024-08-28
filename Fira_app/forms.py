
from ckeditor.fields import RichTextField
from ckeditor_uploader import widgets
from django import forms

class ReportContentForm(forms.Form):
    content= forms.CharField(widget=widgets.CKEditorUploadingWidget(),label="")

