from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ControlAccessTests(TestCase):
    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse('control'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/account/login/', response['Location'])

    def test_regular_publisher_cannot_open_staff_control(self):
        user = get_user_model().objects.create_user(username='publisher-example', password='a-long-test-password-1234')
        self.client.force_login(user)
        response = self.client.get(reverse('control'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/account/login/', response['Location'])

    def test_staff_can_open_control_and_see_navigation(self):
        user = get_user_model().objects.create_user(username='editor-example', password='a-long-test-password-1234', is_staff=True)
        self.client.force_login(user)
        response = self.client.get(reverse('control'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Newsroom Control Center')
        self.assertContains(response, 'PR review')
        self.assertContains(response, '/cms/')

    def test_staff_menu_is_hidden_from_anonymous_users(self):
        response = self.client.get('/account/login/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Newsroom Control Center')
