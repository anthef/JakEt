import json
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import IntegrityError
from Authenticate.models import UserData
from django.contrib.auth.models import User
from Profile.forms import ProfileForm
from django.views.decorators.csrf import csrf_exempt
import base64
from django.core.files.base import ContentFile

@login_required(login_url='/authenticate')
@csrf_exempt
def profile_view(request):
    try:
        user_data = UserData.objects.get(user=request.user)
        context = {
            'profile_picture': user_data.profile_picture,
            'profile_name': user_data.profile_name,
            'username': user_data.username,
            'about': user_data.about,
            'phone': user_data.phone,
            'email': user_data.email,
            'user_data': user_data,
        }
        return render(request, 'profile.html', context)
    except UserData.DoesNotExist:
        return redirect('Profile:create_profile')

@login_required(login_url='/authenticate')
@csrf_exempt
def create_profile(request):
    if UserData.objects.filter(user=request.user).exists():
        return redirect('Profile:profile_view')

    form = ProfileForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        profile_name = form.cleaned_data['profile_name']
        username = form.cleaned_data['username']
        about = form.cleaned_data['about']
        phone = form.cleaned_data['phone']
        email = form.cleaned_data['email']
        profile_picture = request.FILES.get('profile_picture')

        try:
            user = request.user
            user.username = username
            user.save()
            user_data = UserData.objects.create(
                user=request.user,
                profile_name=profile_name,
                username=username,
                about=about,
                phone=phone,
                email=email,
                profile_picture=profile_picture,
            )
            user_data.save()
            messages.success(request, "Profile created successfully!")
            return redirect('Profile:profile_view')
        except IntegrityError:
            messages.error(request, "An error occurred while creating the profile. Please try again.")

    return render(request, 'create_profile.html', {'form': form})

@login_required(login_url='/authenticate')
@csrf_exempt
def edit_profile(request):
    profile = UserData.objects.get(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)

    if request.method == "POST":
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'delete_picture' in request.POST:
            if profile.profile_picture:
                profile.profile_picture.delete(save=False)
                profile.profile_picture = None
                profile.save()
                return JsonResponse({'status': 'success', 'message': 'Profile picture successfully deleted.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'No profile picture to delete.'})

        if form.is_valid():
            new_username = form.cleaned_data['username']
            user = profile.user
            if user.username != new_username:
                if User.objects.filter(username=new_username).exists():
                    messages.error(request, "Username already exists.")
                    return redirect('Profile:edit_profile')
                user.username = new_username

            form.save() 
            user.save()  

            messages.success(request, "Profile updated successfully!")
            return redirect(reverse('Profile:profile_view'))
        else:
            messages.error(request, "Profile update failed.")

    return render(request, 'edit_profile.html', {'form': form})


@login_required(login_url='/authenticate')
@csrf_exempt
def delete_profile_picture(request):
    if request.method == "POST":
        profile = UserData.objects.get(user=request.user)
        if profile.profile_picture:
            profile.profile_picture.delete(save=True)
            profile.profile_picture = None
            profile.save()
            return JsonResponse({'message': 'Profile picture successfully deleted.'})
        else:
            return JsonResponse({'message': 'No profile picture to delete.'}, status=404)
    return JsonResponse({'message': 'Invalid request.'}, status=405)

@csrf_exempt
def show_xml(request):
    data = UserData.objects.all()
    return HttpResponse(serializers.serialize("xml", data), content_type="application/xml")

@csrf_exempt
def show_json(request):
    data = UserData.objects.all()
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")

@csrf_exempt
def create_profile_flutter(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode('utf-8'))

            profile_name = data.get("profile_name", "")
            username = data.get("username", "")
            phone = data.get("phone", "")
            email = data.get("email", "")
            about = data.get("about", "")
            profile_picture_data = data.get("profilePicture", None)

            if not (profile_name and username and phone and email and about):
                return JsonResponse({"status": "error", "message": "All fields are required."}, status=400)

            # Handle profile picture if provided
            profile_picture = None
            if profile_picture_data:
                if "base64" in profile_picture_data:  # Handle Base64 data
                    format, imgstr = profile_picture_data.split(';base64,')
                    ext = format.split('/')[-1]
                    profile_picture = ContentFile(base64.b64decode(imgstr), name=f"profile_{request.user.id}.{ext}")
                else:
                    return JsonResponse({"status": "error", "message": "Invalid profile picture format."}, status=400)

            # Create or update user profile
            user = request.user
            user.username = username
            user.save()

            user_data, created = UserData.objects.update_or_create(
                user=user,
                defaults={
                    "profile_name": profile_name,
                    "username": username,
                    "about": about,
                    "phone": phone,
                    "email": email,
                    "profile_picture": profile_picture,
                }
            )

            return JsonResponse({"status": "success", "message": "Profile created successfully."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=405)

@csrf_exempt
def edit_profile_flutter(request):
    if request.method == "POST":
        try:
            # Mengambil data JSON dari body request
            data = json.loads(request.body.decode('utf-8'))

            # Mengambil data dari request
            profile_name = data.get("profile_name", "")
            username = data.get("username", "")
            phone = data.get("phone", "")
            email = data.get("email", "")
            about = data.get("about", "")
            profile_picture_data = data.get("profilePicture", None)  # Memeriksa adanya gambar profil dalam format base64

            # Validasi: Memastikan semua field wajib terisi
            if not (profile_name and username and phone and email and about):
                return JsonResponse({"status": "error", "message": "All fields are required."}, status=400)

            # Memeriksa apakah username sudah ada
            user = request.user
            if user.username != username:
                if User.objects.filter(username=username).exists():
                    return JsonResponse({"status": "error", "message": "Username already exists."}, status=400)

            # Menangani gambar profil jika ada
            profile_picture = None
            if profile_picture_data:
                if "base64" in profile_picture_data:  # Menangani data gambar dalam format base64
                    format, imgstr = profile_picture_data.split(';base64,')
                    ext = format.split('/')[-1]
                    profile_picture = ContentFile(base64.b64decode(imgstr), name=f"profile_{request.user.id}.{ext}")
                else:
                    return JsonResponse({"status": "error", "message": "Invalid profile picture format."}, status=400)

            # Mengupdate informasi pengguna
            user.username = username
            user.save()

            # Update atau buat data profil baru
            user_data, created = UserData.objects.update_or_create(
                user=user,
                defaults={
                    "profile_name": profile_name,
                    "username": username,
                    "about": about,
                    "phone": phone,
                    "email": email,
                    "profile_picture": profile_picture,
                }
            )

            return JsonResponse({"status": "success", "message": "Profile updated successfully."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=405)
