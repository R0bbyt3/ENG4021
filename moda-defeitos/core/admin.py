from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


from .models import UserProfile, Category, ProductImage, Favorite, Cart, CartItem, Order, OrderItem


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "store_name"]
    list_filter = ["role"]
    search_fields = ["user__username", "user__email", "store_name"]
    list_select_related = ["user"]


admin.site.register([Category, ProductImage, Favorite, Cart, CartItem, Order, OrderItem])
