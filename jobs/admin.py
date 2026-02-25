from django.contrib import admin
from .models import Job, Chunk


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """
    Django admin configuration for the Job model.

    Displays the job ID, status, and creation timestamp in the admin list view.
    Allows filtering by job status and makes the creation and update timestamps read-only.
    """
    list_display = ('id', 'status', 'created_at')
    list_filter = ('status', )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    """
    Django admin configuration for the Chunk model.

    Displays the chunk ID, associated job, index, and status in the admin list view.
    Allows filtering by chunk status.
    """
    list_display = ('id', 'job', 'index', 'status')
    list_filter = ('status', )
