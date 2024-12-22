from datetime import timezone
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from DetailProduct.forms import ReviewForm
from Homepage.models import Phone
from .models import Review
import json
from django.db.models import Avg
from Wishlist.models import Favorite
from collections import defaultdict
from django.contrib import messages
from django.utils import timezone

# WEB
@login_required(login_url='/authenticate/login')
@csrf_exempt
def product_detail(request, product_id):
    product = get_object_or_404(Phone, id=product_id)
    reviews = Review.objects.filter(product=product)
    user_has_review = reviews.filter(user=request.user).exists()
    user_review = reviews.filter(user=request.user).first() if user_has_review else None
    user_favorites = []
    if request.user.is_authenticated:
        user_favorites = Favorite.objects.filter(user=request.user).values_list('phone_id', flat=True)
    star_counts = [
        (5, product.five_star),
        (4, product.four_star),
        (3, product.three_star),
        (2, product.two_star),
        (1, product.one_star),
    ]
    
    context = {
        'product': product,
        'reviews': reviews,
        'user_has_review': user_has_review,
        'user_review': user_review,
        'user_favorites': user_favorites,  
        'star_counts': star_counts, 
    }
    return render(request, 'detail.html', context)

@csrf_exempt
@login_required(login_url='/authenticate/login')
def toggle_favorite(request, phone_id):
    phone = get_object_or_404(Phone, id=phone_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, phone=phone)
    if not created:
        favorite.delete() 
        is_favorite = False
    else:
        is_favorite = True
    return JsonResponse({'is_favorite': is_favorite})

@login_required(login_url='/authenticate/login')
@csrf_exempt
def review_page(request, product_id):
    product = get_object_or_404(Phone, id=product_id)
    user_reviews = Review.objects.filter(product=product)
    form = ReviewForm(request.POST or None)
    review_counts = defaultdict(int)
    user_has_reviewed = Review.objects.filter(product=product, user=request.user).exists()
    
    for review in user_reviews:
        review_counts[review.rating] += 1

    if request.method == 'POST':
        if form.is_valid():
            if user_has_reviewed:
                messages.error(request, "Anda sudah memberikan review untuk produk ini")
                return redirect('DetailProduct:review_page', product_id=product_id)
            
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            messages.success(request, "Review berhasil ditambahkan!")
            return redirect('DetailProduct:review_page', product_id=product_id)

    context = {
        'product': product,
        'reviews': user_reviews,
        'form': form,
        'review_counts': review_counts,
        'user_has_reviewed': user_has_reviewed
    }
    return render(request, 'review_page.html', context)

@login_required(login_url='/authenticate/login')
@csrf_exempt
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    product_id = str(review.product.id)
    if review.user != request.user:
        return redirect('DetailProduct:review_page', product_id=product_id)
        
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.last_edited = timezone.now()
            review.save()
            messages.success(request, "Review berhasil diperbarui!")
            return redirect('DetailProduct:review_page', product_id=product_id)
    else:
        form = ReviewForm(instance=review)
    
    context = {
        'form': form,
        'review': review,
        'product_id': product_id
    }
    return render(request, 'edit_review.html', context)

@login_required(login_url='/authenticate/login')
@csrf_exempt
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    product_id = review.product.id 
    if review.user != request.user:
        return redirect('DetailProduct:review_page', product_id=product_id)
        
    review.delete()
    messages.success(request, "Review berhasil dihapus!")
    return redirect('DetailProduct:review_page', product_id=product_id)


# FLUTTER
@csrf_exempt
def create_review_flutter(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            content = data.get('content', '').strip()
            rating = data.get('rating')

            if not product_id or not rating:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Product ID dan rating wajib diisi.'
                }, status=400)

            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    raise ValueError
            except ValueError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Rating harus berupa angka antara 1 dan 5.'
                }, status=400)

            product = get_object_or_404(Phone, id=product_id)
            if Review.objects.filter(product=product, user=request.user).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Anda sudah memberikan review untuk produk ini.'
                }, status=400)

            new_review = Review(
                user=request.user,
                product=product,
                content=content,
                rating=rating
            )
            new_review.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Review berhasil ditambahkan.',
                'review_id': new_review.id
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Data JSON tidak valid.'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Terjadi kesalahan: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Metode request tidak diizinkan.'
        }, status=405)

@csrf_exempt
def edit_review_flutter(request, review_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            review = get_object_or_404(Review, id=review_id)
            if review.user != request.user:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Anda tidak memiliki izin untuk mengedit review ini.'
                }, status=403)

            content = data.get('content', '').strip()
            rating = data.get('rating')

            if rating:
                try:
                    rating = int(rating)
                    if rating < 1 or rating > 5:
                        raise ValueError
                except ValueError:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Rating harus berupa angka antara 1 dan 5.'
                    }, status=400)
                review.rating = rating

            if 'content' in data:
                review.content = content
            review.save()
            return JsonResponse({
                'status': 'success',
                'message': 'Review berhasil diperbarui.'
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Data JSON tidak valid.'
            }, status=400)
        except Review.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Review tidak ditemukan.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Terjadi kesalahan: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Metode request tidak diizinkan.'
        }, status=405)


@csrf_exempt
def delete_review_flutter(request, review_id):
    if request.method == 'POST':
        try:
            review = get_object_or_404(Review, id=review_id)
            if review.user != request.user:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Anda tidak memiliki izin untuk menghapus review ini.'
                }, status=403)

            review.delete()

            return JsonResponse({
                'status': 'success',
                'message': 'Review berhasil dihapus.'
            }, status=200)

        except Review.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Review tidak ditemukan.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Terjadi kesalahan: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Metode request tidak diizinkan.'
        }, status=405)

def list_reviews_flutter(request, product_id):
    if request.method == 'GET':
        try:
            product = get_object_or_404(Phone, id=product_id)
            reviews = Review.objects.filter(product=product).order_by('-date_added')
            review_data = []
            for review in reviews:
                profile_image_url = getattr(review.user, 'profile_image_url', '')
                review_data.append({
                    'id': review.id,
                    'user': {
                        'username': review.user.username,
                        'profile_image_url': profile_image_url if profile_image_url else '/static/images/default_profile.png' 
                    },
                    'content': review.content,
                    'rating': review.rating,
                    'date_added': review.date_added.strftime('%Y-%m-%d %H:%M:%S'),
                    'last_edited': review.last_edited.strftime('%Y-%m-%d %H:%M:%S') if review.last_edited else None
                })

            return JsonResponse({
                'status': 'success',
                'reviews': review_data
            }, status=200)

        except Phone.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Produk tidak ditemukan.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Terjadi kesalahan: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Metode request tidak diizinkan.'
        }, status=405)
