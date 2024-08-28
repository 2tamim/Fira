from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from ..utilities.date_tools import shamsiDate
import datetime

register = template.Library()

@register.simple_tag
def solar_date():
    _date = datetime.date.today()
    _weekday=datetime.datetime.today().weekday()
    _day=""
    if (_weekday==5):
        _day="شنبه"
    if (_weekday==6):
        _day="یکشنبه"
    if (_weekday==0):
        _day="دوشنبه"
    if (_weekday==1):
        _day="سه شنبه"
    if (_weekday==2):
        _day="چهارشنبه"
    if (_weekday==3):
        _day="پنج شنبه"
    if (_weekday==4):
        _day="جمعه"

    _shamsi=shamsiDate(_date.year,_date.month,_date.day)
    month=""
    if (_shamsi[1]==1):
        month="فروردین"
    if (_shamsi[1]==2):
        month="اردیبهشت"
    if (_shamsi[1]==3):
        month="خرداد"
    if (_shamsi[1]==4):
        month="تیر"
    if (_shamsi[1]==5):
        month="مرداد"
    if (_shamsi[1]==6):
        month="شهریور"
    if (_shamsi[1]==7):
        month="مهر"
    if (_shamsi[1]==8):
        month="آبان"
    if (_shamsi[1]==9):
        month="آذر"
    if (_shamsi[1]==10):
        month="دی"
    if (_shamsi[1]==11):
        month="بهمن"
    if (_shamsi[1]==12):
        month="اسفند"
    return mark_safe(" امروز: "+ _day +" , "+ ('00'+str(_shamsi[2]))[-2:]+" "+ month +" "+str(_shamsi[0]))