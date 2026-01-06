from django.contrib import admin
from .models import Friendship

@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator', 'target', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('creator__username', 'target__username')
    ordering = ('-created_at',)