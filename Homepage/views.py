from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseBadRequest, HttpResponse
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from .models import Phone
from Wishlist.models import Favorite
from ServiceCenter.models import ServiceCenter
from django.core import serializers
import json

# Django Views
def home_section(request):
    phones = Phone.objects.all()
    service = ServiceCenter.objects.all()
    user_favorites = []
    if request.user.is_authenticated:
        user_favorites = Favorite.objects.filter(user=request.user).values_list('phone_id', flat=True)
    context = {
        'phones': phones,
        'user_favorites': user_favorites, 
        'service' : service
    }
    return render(request, 'home.html', context)

def list_products(request):
    phones = Phone.objects.all()
    brands = Phone.objects.values_list('brand', flat=True).distinct()
    storages = Phone.objects.values_list('storage', flat=True).distinct()
    rams = Phone.objects.values_list('ram', flat=True).distinct()

    brand_filter = request.GET.get('brand')
    storage_filter = request.GET.get('storage')
    ram_filter = request.GET.get('ram')
    price_sort = request.GET.get('sort_price')

    if brand_filter:
        phones = phones.filter(brand=brand_filter)
    if storage_filter:
        phones = phones.filter(storage=storage_filter)
    if ram_filter:
        phones = phones.filter(ram=ram_filter)
    
    if price_sort == 'high_to_low':
        phones = phones.order_by('-price_inr')
    elif price_sort == 'low_to_high':
        phones = phones.order_by('price_inr')

    user_favorites = []
    if request.user.is_authenticated:
        user_favorites = Favorite.objects.filter(user=request.user).values_list('phone_id', flat=True)

    context = {
        'phones': phones,
        'brands': brands,
        'storages': storages,
        'rams': rams,
        'user_favorites': user_favorites  
    }
    return render(request, 'list_product.html', context)


# @csrf_exempt
# @login_required(login_url='/authenticate/login')
# def toggle_favorite(request, phone_id):
#     phone = get_object_or_404(Phone, id=phone_id)
#     favorite, created = Favorite.objects.get_or_create(user=request.user, phone=phone)
#     if not created:
#         favorite.delete() 
#         is_favorite = False
#     else:
#         is_favorite = True
#     return JsonResponse({'is_favorite': is_favorite})

@csrf_exempt
@login_required(login_url='/authenticate/login/')
def toggle_favorite(request, phone_id):
    if request.method == 'POST':
        phone = get_object_or_404(Phone, id=phone_id)
        favorite, created = Favorite.objects.get_or_create(user=request.user, phone=phone)
        if not created:
            favorite.delete()
            is_favorite = False
        else:
            is_favorite = True
        return JsonResponse({'is_favorite': is_favorite})
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)
    
@csrf_exempt
def search_results(request):
    query = request.GET.get('q')
    brand_filter = request.GET.get('brand')
    storage_filter = request.GET.get('storage')
    ram_filter = request.GET.get('ram')
    price_sort = request.GET.get('sort_price')
    phones = Phone.objects.all()
    if query:
        phones = phones.filter(brand__icontains=query) | phones.filter(model__icontains=query)
    if brand_filter:
        phones = phones.filter(brand=brand_filter)
    if storage_filter:
        phones = phones.filter(storage=storage_filter)
    if ram_filter:
        phones = phones.filter(ram=ram_filter)

    if price_sort == 'high_to_low':
        phones = phones.order_by('-price_inr')
    elif price_sort == 'low_to_high':
        phones = phones.order_by('price_inr')

    brands = Phone.objects.values_list('brand', flat=True).distinct()
    storages = Phone.objects.values_list('storage', flat=True).distinct()
    rams = Phone.objects.values_list('ram', flat=True).distinct()

    user_favorites = []
    if request.user.is_authenticated:
        user_favorites = Favorite.objects.filter(user=request.user).values_list('phone_id', flat=True)

    context = {
        'phones': phones,
        'brands': brands,
        'storages': storages,
        'rams': rams,
        'user_favorites': user_favorites,
        'query': query,  
    }

    return render(request, 'search_results.html', context)

@login_required(login_url='/authenticate/login')
@csrf_exempt
def search_suggestions(request):
    query = request.GET.get('q', '')
    if query:
        suggestions = Phone.objects.filter(brand__icontains=query) | Phone.objects.filter(model__icontains=query)
        suggestions = suggestions.distinct()[:4] 
        results = [{'product_id': str(phone.id), 'brand': phone.brand, 'model': phone.model} for phone in suggestions]
        return JsonResponse(results, safe=False)
    return JsonResponse([], safe=False)

# Flutter Views
@csrf_exempt
def show_json(request):
    data = Phone.objects.all()
    return HttpResponse(serializers.serialize("json",data),content_type='application/json')

@csrf_exempt
def show_json_by_id(request, id):
    data = Phone.objects.filter(pk=id)
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")


