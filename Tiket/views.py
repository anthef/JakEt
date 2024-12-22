import datetime
from django.shortcuts import render, redirect, reverse, get_object_or_404
from Tiket.forms import TiketForm
from Tiket.models import Tiket
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.views.decorators.http import require_POST
from ServiceCenter.models import ServiceCenter
from Authenticate.models import UserData
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def create_tiket(request, id):
    service_center = get_object_or_404(ServiceCenter, pk=id)
    if request.method == "POST":
        form = TiketForm(request.POST)
        form.request = request
        if form.is_valid():
            tiket = form.save(commit=False)
            if request.user.is_authenticated:
                user, created = UserData.objects.get_or_create(user=request.user) 
                tiket.user = user
            else:
                tiket.user = None
            tiket.save()
            return redirect('ServiceCenter:show_service_page')
    else:
        form = TiketForm(initial={'service_center': service_center})
    context = {'form': form, 'service_center': service_center}
    return render(request, "make_appointment.html", context)


@csrf_exempt
def reschedule_appointment(request, id):
    # Get tiket berdasarkan id
    tiket = get_object_or_404(Tiket, pk=id)
    if request.method == "POST":
        form = TiketForm(request.POST, instance=tiket, request=request)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('ServiceCenter:show_service_page'))
    else:
        form = TiketForm(instance=tiket, request=request)

    context = {'form': form}
    return render(request, "reschedule_appointment.html", context)


def cancel_appointment(request, id):
    tiket = Tiket.objects.get(pk=id)
    
    if request.method == "POST":
        tiket.delete()
        return HttpResponseRedirect(reverse('ServiceCenter:show_service_page'))
    
    return render(request, 'confirm_cancel.html', {'tiket': tiket})

@csrf_exempt
def show_xml(request):
    data = Tiket.objects.all()
    return HttpResponse(serializers.serialize("xml", data), content_type="application/xml")

@csrf_exempt
def show_json(request):
    if request.user.is_authenticated:
        user_data = UserData.objects.get(user=request.user)
        data = Tiket.objects.filter(user=user_data).select_related('service_center')
        tiket_list = []
        for tiket in data:
            tiket_dict = {
                'id': str(tiket.id),
                'service_date': tiket.service_date,
                'service_time': tiket.service_time,
                'specific_problems': tiket.specific_problems,
                'service_center': {
                    'name': tiket.service_center.name,
                    'address': tiket.service_center.address,
                    'contact': tiket.service_center.contact,
                    'image': tiket.service_center.image.url,
                },
            }
            tiket_list.append(tiket_dict)
        return JsonResponse(tiket_list, safe=False)
    else:
        return JsonResponse([], safe=False)

@csrf_exempt
def show_xml_by_id(request, id):
    data = Tiket.objects.filter(pk=id)
    return HttpResponse(serializers.serialize("xml", data), content_type="application/xml")

@csrf_exempt
def show_json_by_id(request, id):
    data = Tiket.objects.filter(pk=id)
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")

@csrf_exempt
def create_ticket_flutter(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            service_center = ServiceCenter.objects.get(id=data["service_center_id"])

            if request.user.is_authenticated:
                user_data, created = UserData.objects.get_or_create(user=request.user)
            else:
                return JsonResponse({"status": "error", "message": "User not authenticated."}, status=403)
    
            new_ticket = Tiket.objects.create(
                user=user_data, 
                service_center=service_center,
                service_date=data["service_date"],  
                service_time=data["service_time"],  
                specific_problems=data["specific_problems"],
            )
            new_ticket.save()

            return JsonResponse({"status": "success"}, status=200)
        except ServiceCenter.DoesNotExist:
            return JsonResponse({"status": "error"}, status=404)
    else:
        return JsonResponse({"status": "error"}, status=405)

@csrf_exempt
def reschedule_ticket_flutter(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ticket_id = data.get("ticket_id")

            tiket = get_object_or_404(Tiket, id=ticket_id)

            if request.user.is_authenticated:
                if tiket.user.user != request.user:
                    return JsonResponse({"status": "error"}, status=403)
            else:
                return JsonResponse({"status": "error"}, status=403)
            
            if "service_date" in data:
                tiket.service_date = data["service_date"]
            if "service_time" in data:
                tiket.service_time = data["service_time"]
            if "specific_problems" in data:
                tiket.specific_problems = data["specific_problems"]

            tiket.save()

            return JsonResponse({"status": "success"}, status=200)
        except Tiket.DoesNotExist:
            return JsonResponse({"status": "error"}, status=404)
    else:
        return JsonResponse({"status": "error"}, status=405)
    
@csrf_exempt
def cancel_appointment_flutter(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ticket_id = data.get('ticket_id')
            tiket = get_object_or_404(Tiket, pk=ticket_id)

            if not request.user.is_authenticated:
                return JsonResponse({"status": "error"}, status=403)

            user_data = UserData.objects.filter(user=request.user).first()
            if tiket.user != user_data:
                return JsonResponse({"status": "error"}, status=403)

            tiket.delete()
            return JsonResponse({"status": "success"}, status=200)

        except Tiket.DoesNotExist:
            return JsonResponse({"status": "error"}, status=404)
    else:
        return JsonResponse({"status": "error"}, status=405)