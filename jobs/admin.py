from django.contrib import admin
from .models import Job, Chunk


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'created_at')
    list_filter = ('status', )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'index', 'status')
    list_filter = ('status', )
