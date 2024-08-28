from django.contrib.auth import authenticate, login,logout
from django.shortcuts import render, redirect
from ...models import Employee
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse


@csrf_exempt
def sitelogin(request):
    context={}
    _hasError = False
    if request.method=="POST":
        username = request.POST['username'].lower()
        password = request.POST['password']
        
        if (not _hasError and not username ):
            context["Error"]=" نام کاربری را مقداردهی کنید."
            _hasError=True
        if (not _hasError and not password ):
            context["Error"]="گذرواژه را مقداردهی کنید."
            _hasError=True
        if(not _hasError):
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if not request.POST.get('remember_me', None):
                    request.session.set_expiry(0)
                if 'csrfmiddlewaretoken' in request.POST.keys():
                    return redirect("dashboard:index")
                else:
                    return JsonResponse({'sessionid': request.session.session_key})
            else:
                context["Error"]="اطلاعات کاربری شما معتبر نمی باشد."
    else:
        if (request.user.id):
            return redirect("dashboard:index")
    return render(request, 'user/login.html', {'context': context})

def logout_view(request):
    logout(request)
    # Redirect to a success page.
    return redirect("user:login")