from django.test import TestCase, Client
from django.shortcuts import resolve_url
from django.utils import timezone
from django.urls import reverse

from model_mommy import mommy
import mock
import datetime

from django.contrib.auth.models import User
from events.ipstack import get_ipstack_geocoder
from events.models import Team
# Create your tests here.


class TeamDisplayTests(TestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_show_team(self):
        team = mommy.make(Team)
        team.save()

        team_url = team.get_absolute_url()

        c = Client()
        response = c.get(team_url)
        assert(response.status_code == 200)

    def test_show_about_team(self):
        team = mommy.make(Team)
        team.about_page = "about this team!"
        team.save()

        team_about_url = reverse('show-team-about-by-slug', kwargs={'team_slug': team.slug})

        c = Client()
        response = c.get(team_about_url)
        assert(response.status_code == 200)

    def test_show_about_team_redirects_if_none(self):
        team = mommy.make(Team)
        team.about_page = ""
        team.save()

        team_about_url = reverse('show-team-about-by-slug', kwargs={'team_slug': team.slug})

        c = Client()
        response = c.get(team_about_url)
        assert(response.status_code == 302)
