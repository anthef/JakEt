from django.shortcuts import render

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from Homepage.models import Phone  
from .models import Favorite  
from django.http import HttpResponse, JsonResponse
from django.core import serializers
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)

#WEB FAVORITE
@csrf_exempt
@login_required(login_url='/authenticate/login/')
def favorite_list(request):
    if request.method == 'GET':
        favorites = Favorite.objects.filter(user=request.user)
        favorite_phones = [phone.phone.to_dict() for phone in favorites]  # Assuming Phone has a to_dict method
        return JsonResponse(favorite_phones, safe=False)
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)
    
@login_required(login_url='/authenticate/login/')
@csrf_exempt
def favorite_list_web(request):
    if request.method == 'GET':
        favorites = Favorite.objects.filter(user=request.user)
        return render(request, 'wishlist.html', {'favorites': favorites})
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)

@login_required(login_url='/authenticate/login/')
@csrf_exempt
def remove_favorite_web(request, phone_id):
    if request.method == 'POST':
        phone = get_object_or_404(Phone, id=phone_id)
        favorite = Favorite.objects.filter(user=request.user, phone=phone)
        if favorite.exists():
            favorite.delete()
        return redirect('Wishlist:favorite_list')  
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


#APP FAVORITE
@csrf_exempt
def show_wishlist_json(request):
    if request.method == 'GET':
        favorites = Favorite.objects.filter(user=request.user)
        phone_ids = favorites.values_list('phone_id', flat=True)
        phones = Phone.objects.filter(id__in=phone_ids)
        serialized_phones = serializers.serialize("json", phones)
        return HttpResponse(serialized_phones, content_type='application/json')
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)

@csrf_exempt
def add_to_favorite_flutter(request):
    logger.debug("add_to_favorite_flutter called by user: %s", request.user)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_id = data.get("phone_id")
            if not phone_id:
                logger.warning("No phone_id provided")
                return JsonResponse({
                    "status": "error",
                    "message": "No phone_id provided"
                }, status=400)
            
            phone = Phone.objects.get(pk=phone_id)
            favorite, created = Favorite.objects.get_or_create(
                user=request.user,
                phone=phone
            )
            
            # Return consistent response format
            logger.info("Favorite %s for phone_id: %s by user: %s", 
                        "created" if created else "exists", phone_id, request.user)
            return JsonResponse({
                "status": "success" if created else "info",
                "message": "Added to favorites" if created else "Already in favorites"
            }, status=200)
            
        except Phone.DoesNotExist:
            logger.error("Phone with id %s not found", phone_id)
            return JsonResponse({
                "status": "error",
                "message": "Phone not found"
            }, status=404)
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            return JsonResponse({
                "status": "error",
                "message": "Invalid JSON"
            }, status=400)
    logger.warning("Invalid request method: %s", request.method)
    return JsonResponse({
        "status": "error",
        "message": "Invalid request method"
    }, status=405)


@csrf_exempt
def remove_from_favorite_flutter(request):
    if request.method == 'POST':
        try:
            logger.debug(f"Request Body: {request.body}")

            data = json.loads(request.body)
            phone_id = data.get("phone_id")
            logger.debug(f"Received phone_id: {phone_id}")

            if not phone_id:
                return JsonResponse({"status": "error", "message": "No phone_id provided"}, status=400)
            
            phone = Phone.objects.get(pk=phone_id)
            favorite = Favorite.objects.filter(user=request.user, phone=phone)
            if favorite.exists():
                favorite.delete()
                return JsonResponse({"status": "success", "message": "Removed from favorites"}, status=200)
            else:
                return JsonResponse({"status": "info", "message": "Not in favorites"}, status=200)
        except Phone.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Phone not found"}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({"status": "error", "message": "An unexpected error occurred"}, status=500)
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)
