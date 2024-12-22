# views.py
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Chat, DailyCustomerService
import json
from django.core import serializers
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.models import User

@login_required
@csrf_exempt
def customer_service(request, user_id=None):
    if request.user.is_superuser and user_id:
        viewing_user = User.objects.get(id=user_id)
    else:
        viewing_user = request.user

    # Restrict regular users from viewing other users' chats
    if not request.user.is_superuser and viewing_user != request.user:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

    daily_chats = Chat.objects.filter(user=viewing_user).order_by('date', 'time_sent')
    grouped_chats = {}

    for chat in daily_chats:
        if request.user.is_superuser:
            chat.mark_as_read()
        if chat.date not in grouped_chats:
            grouped_chats[chat.date] = []
        grouped_chats[chat.date].append(chat)

    context = {
        'grouped_chats': grouped_chats,
        'today': timezone.now().date(),
        'viewing_user': viewing_user,
    }

    return render(request, 'customer-service.html', context)

@login_required
@csrf_exempt
def send_message(request, user_id=None):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()

            # Check if the user is a superuser and set the recipient accordingly
            if request.user.is_superuser and user_id:
                receiving_user = User.objects.get(id=user_id)
                sentByUser = False
            else:
                receiving_user = request.user
                sentByUser = True

            if message:
                # Create a new chat message for the intended recipient
                chat = Chat.objects.create(
                    user=receiving_user,
                    message=message,
                    sent_by_user=sentByUser
                )

                return JsonResponse({
                    'status': 'success',
                    'message': {
                        'id': chat.id,
                        'message': chat.message,
                        'time': chat.time_sent.strftime('%H:%M'),
                        'date': chat.date.strftime('%Y-%m-%d'),
                        'sent_by_user': chat.sent_by_user,
                    }
                })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def get_messages(request):
    # Get messages after a certain timestamp
    last_msg_time = request.GET.get('after', None)
    
    messages = Chat.objects.filter(
        user=request.user
    )
    
    if last_msg_time:
        messages = messages.filter(time_sent__gt=last_msg_time)
    
    messages = messages.order_by('date', 'time_sent')
    
    data = [{
        'id': msg.id,
        'message': msg.message,
        'time': msg.time_sent.strftime('%H:%M'),
        'date': msg.date.strftime('%Y-%m-%d')
    } for msg in messages]
    
    return JsonResponse({'messages': data})

@csrf_exempt
def show_json(request):
    chats = Chat.objects.filter(user=request.user)
    return HttpResponse(serializers.serialize('json', chats), content_type='application/json')

@csrf_exempt
def send_message_flutter(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get("message")
            receiving_user = request.user

            if not message or not receiving_user:
                return JsonResponse({'status': 'error', 'message': 'Missing message or user_id'}, status=400)
            
            chat = Chat.objects.create(
                user=receiving_user,
                message=message,
                sent_by_user=True
            )

            return JsonResponse({
                'status': 'success',
                'message': {
                    'id': chat.id,
                    'message': chat.message,
                    'time': chat.time_sent.strftime('%H:%M'),
                    'date': chat.date.strftime('%Y-%m-%d'),
                    'sent_by_user': chat.sent_by_user,
                }
            })
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
