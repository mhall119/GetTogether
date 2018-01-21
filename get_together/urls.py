"""get_together URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from events import views as event_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('searchables/', event_views.searchable_list),
    path('api/places/', event_views.places_list),
    path('api/countries/', event_views.country_list),
    path('api/spr/', event_views.spr_list),
    path('api/cities/', event_views.city_list),

    path('events/', views.events_list, name='events'),
    path('create-team/', views.create_team, name='create-team'),
    path('teams/', views.teams_list, name='teams'),
    path('team/<int:team_id>/', views.show_team, name='show-team'),
    path('team/<int:team_id>/create-event/', views.create_event, name='create-event'),
    path('events/<int:event_id>/<str:event_slug>/', views.show_event, name='show-event'),

    path('places/', views.places_list, name='places'),
    path('create-place/', views.create_place, name='create-place'),

    path('oauth/', include('social_django.urls', namespace='social')),
]
