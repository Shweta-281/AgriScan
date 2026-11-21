import json
from decimal import Decimal
from django.db.models import F, Sum, Q
from django.db.models.fields import DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from analytics.utils import send_sms
from .forms import ProductForm
from .models import Product, Category, CartItem, Order, OrderItem

def store(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    
    # Handles the ?search=DiseaseName from the result page
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
        
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
        
    return render(request, 'marketplace/store.html', {
        'products': products, 
        'categories': categories,
        'search_query': search_query
    })

@login_required
def add_to_cart(request, product_id):
    if request.user.role != 'farmer':
        return redirect('store')
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f"Added {product.name} to cart!")
    return redirect('view_cart')

@login_required
def view_cart(request):
    if request.user.role != 'farmer':
        return redirect('store')
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.total_price() for item in cart_items)
    return render(request, 'marketplace/cart.html', {'cart_items': cart_items, 'total': total})

@login_required
def checkout(request):
    if request.user.role != 'farmer':
        return redirect('store')
        
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('store')

    total = sum(item.total_price() for item in cart_items)
    
    return render(request, 'marketplace/checkout.html', {
        'cart_items': cart_items, 
        'total': total
    })

@login_required
def process_payment(request):
    if request.method != 'POST':
        return redirect('checkout')
        
    if request.user.role != 'farmer':
        return redirect('store')
        
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items.exists():
        return redirect('store')

    total = sum(item.total_price() for item in cart_items)
    
    order = Order.objects.create(
        farmer=request.user, 
        total_amount=total,
        status='Processing' 
    )
    
    sellers = set()
    for item in cart_items:
        OrderItem.objects.create(
            order=order, 
            product=item.product, 
            quantity=item.quantity, 
            price=item.product.price
        )
        item.product.stock -= item.quantity
        item.product.save()
        sellers.add(item.product.seller)
        
    cart_items.delete()
    
    if request.user.phone:
        send_sms(request.user.phone, f"AgriScan: Your payment of ₹{total} for Order #{order.id} was successful. Thank you!")
        
    for seller in sellers:
        if seller.phone:
            send_sms(seller.phone, f"AgriScan Seller Alert: You have a new order (#{order.id}). Please check your dashboard.")
            
    return render(request, 'marketplace/payment_success.html', {'order': order})

@login_required
def seller_dashboard(request):
    if request.user.role != 'seller':
        return redirect('home')
        
    products = Product.objects.filter(seller=request.user)
    order_items = OrderItem.objects.filter(product__seller=request.user).order_by('-order__created_at')
    
    revenue_data = order_items.aggregate(
        total_revenue=Coalesce(Sum(F('quantity') * F('price'), output_field=DecimalField()), Decimal('0.00'))
    )
    total_revenue = revenue_data['total_revenue']

    top_products = order_items.values('product__name').annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:5]

    chart_labels = [item['product__name'] for item in top_products]
    chart_data = [item['total_sold'] for item in top_products]

    low_stock_products = products.filter(stock__lt=10)

    context = {
        'products': products,
        'order_items': order_items,
        'total_revenue': total_revenue,
        'low_stock_products': low_stock_products,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'marketplace/seller_dashboard.html', context)

@login_required
def add_product(request):
    if request.user.role != 'seller':
        return redirect('home')
        
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user 
            product.save()
            messages.success(request, "✅ Product added successfully!")
            return redirect('seller_dashboard')
    else:
        form = ProductForm()
        
    return render(request, 'marketplace/add_product.html', {'form': form})

@login_required
def order_history(request):
    if request.user.role != 'farmer':
        return redirect('home')
        
    orders = Order.objects.filter(farmer=request.user).prefetch_related('items').order_by('-created_at')
    
    return render(request, 'marketplace/order_history.html', {'orders': orders})