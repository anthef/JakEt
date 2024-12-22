from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse
from .forms import FirstDataForm, RegisterForm
from django.contrib.auth.models import User
from .models import UserData
import datetime
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

'''
DJANGO WEB AUTHENTICATION
'''
@csrf_exempt
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username telah digunakan oleh pengguna lain.")
            else:
                user = User.objects.create_user(username=username, password=password)
                user.save()
                messages.success(request, 'Akun Anda berhasil dibuat! Silakan login.')
                return redirect('Authenticate:login')
        else:
            messages.error(request, "Form tidak valid. Silakan cek kembali.")
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})

@csrf_exempt
def log_in(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)   
            if user.is_staff:
                response = HttpResponseRedirect(reverse("Dashboard:main_dashboard"))
                response.set_cookie('last_login', str(datetime.datetime.now()))  
                return response

            response = HttpResponseRedirect(reverse("Homepage:home_section")) 
            response.set_cookie('last_login', str(datetime.datetime.now()))  
            return response
        else:
            messages.error(request, 'Username atau password salah. Silakan coba lagi.')
    
    return render(request, 'login.html')

@csrf_exempt
def log_out(request):
    logout(request)
    response = HttpResponseRedirect(reverse('Homepage:home_section'))  
    response.delete_cookie('last_login')  
    return response

'''
FLUTTER APP AUTHENTICATION
'''

@csrf_exempt
def register_app(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data['username']
        password1 = data['password1']
        password2 = data['password2']

        if password1 != password2:
            return JsonResponse({
                "status": False,
                "message": "Passwords do not match."
            }, status=400)
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                "status": False,
                "message": "Username already exists."
            }, status=400)
        
        user = User.objects.create_user(username=username, password=password1)
        user.save()
        
        return JsonResponse({
            "username": user.username,
            "status": 'success',
            "message": "User created successfully!"
        }, status=200)
    
    else:
        return JsonResponse({
            "status": False,
            "message": "Invalid request method."
        }, status=400)


@csrf_exempt
def login_app(request):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)
            print("Login sukses!")
            return JsonResponse({
                "username": user.username,
                "status": True,
                "message": "Login sukses!"
            }, status=200)
        else:
            return JsonResponse({
                "status": False,
                "message": "Login gagal, akun dinonaktifkan."
            }, status=401)

    else:
        return JsonResponse({
            "status": False,
            "message": "Login gagal, periksa kembali email atau kata sandi."
        }, status=401)

@csrf_exempt
def logout_app(request):
    if request.method != 'POST':
        return JsonResponse({
            "status": False,
            "message": "Method not allowed. Use POST."
        }, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({
            "status": False,
            "message": "User is not authenticated."
        }, status=401)

    try:
        username = request.user.username
        logout(request)
        return JsonResponse({
            "username": username,
            "status": True,
            "message": "Logout successful!"
        }, status=200)
    except Exception as e:
        return JsonResponse({
            "status": False,
            "message": "Logout failed."
        }, status=500)


@csrf_exempt
def check_login(request):
    if request.user.is_authenticated:
        return JsonResponse({
            "status": True,
            "username": request.user.username,
        }, status=200)
    else:
        return JsonResponse({
            "status": False,
            "message": "User is not authenticated.",
        }, status=200)
