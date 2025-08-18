"""
URL configuration for djangoKoloFantastyki project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from website import views

urlpatterns = [
    path('rules/', views.RulesView.as_view(), name='rules'),
    path('ticket/', views.GenerateTicketView.as_view(), name='generate_ticket'),
    path('verify-ticket/<str:ticket_id>', views.VerifyTicketView.as_view(), name='verify-ticket'),
    path('contact/', views.ContactView.as_view(), name='contact'),
]