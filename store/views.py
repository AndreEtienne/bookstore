from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect
from .models import Book, BookOrder, Cart
from django.core.urlresolvers import reverse
from django.utils import timezone
import paypalrestsdk


# Create your views here.


def index(request):
    return render(request, 'template.html')


def store(request):
    books = Book.objects.all()
    context = {
        'books': books,
    }
    return render(request, 'base.html', context)


def book_details(request, book_id):
    context = {
        'book': Book.objects.get(pk=book_id)
    }
    return render(request, 'store/detail.html', context)


def add_to_cart(request, book_id):
    if request.user.is_authenticated():
        try:
            book = Book.objects.get(pk=book_id)
        except ObjectDoesNotExist:
            pass
        else:
            try:
                cart = Cart.objects.get(user=request.user, active=True)
            except ObjectDoesNotExist:
                cart = Cart.objects.create(
                    user=request.user
                )
                cart.save()
            cart.add_to_cart(book_id)
        return redirect('cart')
    else:
        return redirect('index')


def remove_from_cart(request, book_id):
    if request.user.is_authenticated():
        try:
            book = Book.objects.get(pk=book_id)
        except ObjectDoesNotExist:
            pass
        else:
            cart = Cart.objects.get(user=request.user, active=True)
            cart.remove_form_cart(book_id)
        return redirect('cart')
    else:
        return redirect('index')


def cart(request):
    if request.user.is_authenticated():
        cart = Cart.objects.filter(user=request.user.id, active=True)
        orders = BookOrder.objects.filter(cart=cart)
        total = 0
        count = 0
        for order in orders:
            total += (order.book.price * order.quantity)
            count += order.quantity
        context = {
            'cart': orders,
            'total': total,
            'count': count,
        }
        return render(request, 'store/cart.html', context)
    else:
        return redirect('index')


def checkout(request, processor):
    if request.user.is_authenticated():
        cart = Cart.objects.filter(user=request.user.id, active=True)
        orders = BookOrder.objects.filter(cart=cart)
        if processor == "paypal":
            redirect_url = checkout_paypal(cart, orders)
            return redirect(redirect_url)
        else:
            return redirect('index')


def checkout_paypal(request, cart, orders):
    if request.user.is_authenticated():
        items = []
        total = 0
        for order in orders:
            total += (order.book.price * order.quantity)
            book = order.book
            item = {
                'name': book.title,
                'sku': book.id,
                'price': str(book.price),
                'currency': 'USD',
                'quantity': order.quantity
            }
            items.append(item)
            paypalrestsdk.configure({
                "mode": "sandbox",  # sandbox or live
                "client_id": "AQVi4fYYoOdC1SaGMosOEewEy7MHIXMeSxa5DWiq-RNn13D4jrwlwKk7A4nI4OISIER-bbTepEkhFYST",
                "client_secret": "ECoYNR0keq6bjKwWK_-20rlhNeUDOtC2uT6Ii6mBPxkhBy3R5WoRkMuI-IcqCN0PnlTphi4VNJZWzq9Y"})
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": "http://localhost:8000/store/process/paypal",
                    "cancel_url": "http://localhost:8000/store/"},
                "transactions": [{
                    "item_list": {
                        "items": items},
                    "amount": {
                        "total": str(total),
                        "currency": "USD"},
                    "description": "Mystery Books order."}]})

            if payment.create():
                cart_instance = cart.get()
                cart_instance.payment_id = payment.id
                cart_instance.save()
                for link in payment.links:
                    if link.metode == "REDIRECT":
                        redirect_url = str(link.href)
                        return redirect_url
                print("Payment created successfully")
            else:
                return reverse('payment.error')
        else:
            return redirect('index')
