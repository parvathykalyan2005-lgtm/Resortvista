from django.test import SimpleTestCase
from django.urls import reverse


class GuestAboutUrlTests(SimpleTestCase):
	def test_guest_about_route_has_unique_name(self):
		self.assertEqual(reverse('guest_about'), '/about/')

	def test_guest_about_page_loads(self):
		response = self.client.get(reverse('guest_about'))
		self.assertEqual(response.status_code, 200)


class GuestContactUrlTests(SimpleTestCase):
	def test_guest_contact_route_has_unique_name(self):
		self.assertEqual(reverse('guest_contact'), '/contact/')

	def test_guest_contact_page_loads(self):
		response = self.client.get(reverse('guest_contact'))
		self.assertEqual(response.status_code, 200)

	def test_guest_contact_post_redirects_to_guest_contact(self):
		response = self.client.post(reverse('guest_contact'), {
			'name': 'Guest User',
			'email': 'guest@example.com',
			'phone': '9876543210',
			'subject': 'Hello',
			'message': 'Testing contact form',
		})
		self.assertRedirects(response, reverse('guest_contact'))
