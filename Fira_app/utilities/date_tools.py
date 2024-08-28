from jdatetime import JalaliToGregorian, GregorianToJalali
import datetime

def gLeapYear(y):
    if (y%4==0) and ((y%100!=0) or (y%400==0)):
        return True
    else: 
        return False

def sLeapYear(y):
    ary = [1, 5, 9, 13, 17, 22, 26, 30]
    result = False
    b = y%33
    if b in ary: 
        result = True
    return result

def shamsiDate(gyear, gmonth, gday):
    _gl = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    _g  = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    
    deydiffjan = 10
    if gLeapYear(gyear-1):  
        deydiffjan = 11
    if gLeapYear(gyear):  
        gd = _gl[gmonth-1]+gday
    else: 
        gd = _g[gmonth-1]+gday
    
    if gd>79:
        sy = gyear - 621
        gd = gd - 79
        if gd<=186:
            gmod = gd%31
            if gmod==0:
                sd = 31
                sm = int(gd/31)
            else:
                sd = gmod
                sm = int(gd/31) + 1
        else:
            gd = gd - 186
            gmod = gd%30
            if gmod==0:
                sd = 30
                sm = int(gd/30) + 6
            else:
                sd = gmod
                sm = int(gd/30) + 7
    else:
        sy = gyear - 622
        gd = gd+deydiffjan
        gmod = gd%30
        if gmod==0:
            sd = 30
            sm = int(gd/30) + 9 
        else:
            sd = gmod; 
            sm = int(gd/30) + 10 

    result = [sy, sm, sd]
    return result

def GetSolarDateNow():
    _date = datetime.date.today()
    _shamsi=shamsiDate(_date.year,_date.month,_date.day)
    
    return str(_shamsi[0])+"/"+('00'+str(_shamsi[1]))[-2:]+"/"+('00'+str(_shamsi[2]))[-2:]

def ConvertToMiladi(solaryear):
    _solar=solaryear.split("/")
    year=int(_solar[0])
    month=int(_solar[1])
    day=int(_solar[2])
    gregorian_date_obj = JalaliToGregorian(year,month,day)
    return str(gregorian_date_obj.getGregorianList()[0])+"-"+str(gregorian_date_obj.getGregorianList()[1])+"-"+str(gregorian_date_obj.getGregorianList()[2])

def ConvertToSolarDate(Miladi):
    if Miladi==None:
        return ""
    _miladi=str(Miladi)[:10].split("-")
    year=int(_miladi[0])
    month=int(_miladi[1])
    day=int(_miladi[2])
    jalali_date_obj = GregorianToJalali(year,month,day)
    return str(jalali_date_obj.getJalaliList()[0])+"/"+str(jalali_date_obj.getJalaliList()[1])+"/"+str(jalali_date_obj.getJalaliList()[2])


# get two datetime d1 ,d2 and return d2-d1 as timedelta
def DateTimeDifference(d1,d2):
    return d2-d1

def ConvertTimeDeltaToStringTime(_timedelta):
    _seconds=(_timedelta.days*24*60*60) +(_timedelta.seconds)
    _new_time_delta=datetime.timedelta(seconds=_seconds)
    if (_new_time_delta.days>0):
        _days=_new_time_delta.days
        _time=('00'+(str(_new_time_delta)[-8:]).strip())[-8:].split(":")
        _newtime=str(int(_time[0])+int(_days*24))+":"+ ('00'+str(int(_time[1])))[-2:]+":"+('00'+str(int(_time[2])))[-2:]
        return _newtime
    return ('00'+str(datetime.timedelta(seconds=_seconds)))[-8:]

def GetWeekDay(date_time):
    _weekday=date_time.weekday()
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
    
    return _day


def GetPersianMonthName(month_id):
    
    month=int(month_id)
    if month==1:
        return "فروردین"
    elif month==2:
        return "اردیبهشت"
    elif month==3:
        return "خرداد"
    elif month==4:
        return "تیر"
    elif month==5:
        return "مرداد"
    elif month==6:
        return "شهریور"
    elif month==7:
        return "مهر"
    elif month==8:
        return "آبان"
    elif month==9:
        return "آذر"
    elif month==10:
        return "دی"
    elif month==11:
        return "بهمن"
    elif month==12:
        return "اسفند"
    else:
        return ""