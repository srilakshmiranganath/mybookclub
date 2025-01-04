from django.contrib import admin

# Register your models here.
from .models import Room, Book, Message, User

admin.site.register(User)
admin.site.register(Room)
admin.site.register(Book)
admin.site.register(Message)