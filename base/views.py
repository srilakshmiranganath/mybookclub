from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from .models import Room, Book, Message, User, Invitation
from .forms import RoomForm, UserForm, MyUserCreationForm

def loginPage(request):
    page = 'login'

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
        except:
            messages.error(request, 'User does not exist.')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('user-profile', pk=user.id)
        else:
            messages.error(request, 'Incorrect Username or Password.')

    context = {'page' : page}
    return render(request, 'base/login_register.html', context)

def logoutPage(request):
    logout(request)
    return redirect('home')

def registerUser(request):
    form = MyUserCreationForm()

    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'An error occured during registration.')
    context = {'form' : form}
    return render(request, 'base/login_register.html', context)

def home(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ' '
    rooms = Room.objects.all()
    books = Book.objects.all()

    room_count = rooms.count()
    room_messages = Message.objects.filter(Q(room__book__name__icontains=q))
    context = {'rooms' : rooms, 'books' : books, 'room_count' : room_count, 'room_messages' : room_messages}
    return render(request, 'base/home.html', context)

def room(request, pk):
    room = Room.objects.get(id=pk)
    room_messages = room.message_set.all()
    participants = room.participants.all()

    if request.method == 'POST' and 'body' in request.POST:
        room_message = Message.objects.create(
            user=request.user,
            room=room,
            body=request.POST.get('body')
        )
        room.participants.add(request.user)
        return redirect('room', pk=room.id)
    
    if request.method == 'POST' and 'invite_email' in request.POST:
        email = request.POST.get('invite_email')

        try:
            receiver = User.objects.get(email=email)
        except:
            HttpResponse('User with that email does not exist.')

        if request.user != room.host:
            return HttpResponse('You are not allowed to send invitations.')
        
        existing_invitation = Invitation.objects.filter(room=room, receiver=receiver, status='PENDING').exists()
        if existing_invitation or receiver in participants:
            return HttpResponse('User hase been sent an invitation or is already a participant.')
        
        Invitation.objects.create(sender=request.user, receiver=receiver, room=room)
        return HttpResponse(f"Invitation sent to {receiver.username}.")
    context = {'room' : room, 'room_messages' : room_messages, 'participants' : participants}
    return render(request, 'base/room.html', context)

def userProfile(request, pk):
    user = User.objects.get(id=pk)
    rooms = user.room_set.all()
    room_messages = user.message_set.all()
    books = Book.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        invitation_id = request.POST.get('invitation_id')

        if action == 'accept':
            return acceptInvitation(request, invitation_id)
        elif action == 'reject':
            return rejectInvitation(request, invitation_id)

    if request.user.id == user.id:
        invitations = user.received_invitations.filter(status='PENDING')
    else:
        invitations = None

    context = {'user' : user, 'rooms' : rooms, 'room_messages' : room_messages, 'books' : books, 'invitations' : invitations}
    return render(request, 'base/profile.html', context)

def acceptInvitation(request, invitation_id):
    invitation = Invitation.objects.get(id=invitation_id, receiver=request.user)

    if invitation.status != 'PENDING':
        return HttpResponse('Invitation no longer valid.')
    
    invitation.room.participants.add(request.user)
    invitation.status = 'ACCEPTED'
    invitation.save()
    return render(request, 'base/profile.html', {'invitation' : invitation})

def rejectInvitation(request, invitation_id):
    invitation = Invitation.objects.get(id=invitation_id, receiver=request.user)

    if invitation.status != 'PENDING':
        return HttpResponse('Invitation no longer valid.') 

    invitation.status = 'REJECTED'
    invitation.save()
    return render(request, 'base/profile.html', {'invitation' : invitation})   

@login_required(login_url='/login')
def createRoom(request):
    form = RoomForm()
    if request.method == 'POST':
        book_name = request.POST.get('book')
        book, created = Book.objects.get_or_create(name=book_name)

        room = Room.objects.create(
            host=request.user,
            book=book,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            
        )
        room.participants.add(request.user)
        return redirect('home')
    context = {'form' : form}
    return render(request, 'base/room_form.html', context)

@login_required(login_url='/login')
def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)

    if request.user != room.host:
        return HttpResponse('You are not allowed here!')
    
    if request.method == 'POST':
        book_name = request.POST.get('book')
        book, created = Book.objects.get_or_create(name=book_name)
        room.name = request.POST.get('name')
        room.book = book
        room.description = request.POST.get('description')
        room.save()
        return redirect('home')

    context = {'form' : form}
    return render(request, 'base/room_form.html', context)

@login_required(login_url='/login')
def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)

    if request.user != room.host:
        return HttpResponse('You are not allowed here!')
    
    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj' : room})

@login_required(login_url='/login')
def deleteMessage(request, pk):
    message = Message.objects.get(id=pk)

    if request.user != message.user:
        return HttpResponse('You are not allowed here!')
    
    if request.method == 'POST':
        message.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj' : message})

@login_required(login_url='/login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)

    return render(request, 'base/update-user.html', {'user' : user, 'form' : form})
