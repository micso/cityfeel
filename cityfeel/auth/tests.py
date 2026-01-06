from django.test import TestCase
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model
from .models import Friendship

User = get_user_model()


class FriendshipModelTest(TestCase):
    """Testy dla modelu Friendship (Zadanie #44)."""

    def setUp(self):
        """Przygotowanie danych testowych."""
        self.user1 = User.objects.create_user(username='user1', email='u1@ex.com', password='password123')
        self.user2 = User.objects.create_user(username='user2', email='u2@ex.com', password='password123')
        self.user3 = User.objects.create_user(username='user3', email='u3@ex.com', password='password123')

    def test_create_friendship_success(self):
        """Test czy można poprawnie utworzyć znajomość."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2
        )

        self.assertEqual(Friendship.objects.count(), 1)
        self.assertEqual(friendship.status, Friendship.PENDING)  # Domyślny status
        self.assertEqual(friendship.user, self.user1)
        self.assertEqual(friendship.friend, self.user2)

    def test_unique_constraint(self):
        """
        Test czy działa UNIQUE(user, friend).
        Nie powinno dać się utworzyć drugiej takiej samej pary.
        """
        # Pierwsza relacja
        Friendship.objects.create(user=self.user1, friend=self.user2)

        # Próba utworzenia duplikatu powinna rzucić błąd IntegrityError
        with self.assertRaises(IntegrityError):
            Friendship.objects.create(user=self.user1, friend=self.user2)

    def test_self_friendship_constraint(self):
        """
        Test czy działa CHECK(user != friend).
        Nie powinno dać się dodać samego siebie do znajomych.
        """
        # Próba zaprzyjaźnienia się ze sobą powinna rzucić błąd IntegrityError
        with self.assertRaises(IntegrityError):
            Friendship.objects.create(user=self.user1, friend=self.user1)

    def test_status_choices(self):
        """Test czy można zmienić status na 'accepted'."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )
        self.assertEqual(friendship.status, 'accepted')

    def test_reverse_relationship_is_not_blocked(self):
        """
        Test czy unikalność jest kierunkowa (user1->user2 to nie to samo co user2->user1).
        W modelu zdefiniowaliśmy unique_together na (user, friend), więc odwrotna relacja JEST dozwolona.
        (To zależy od logiki biznesowej, ale przy obecnym modelu jest to poprawne zachowanie).
        """
        Friendship.objects.create(user=self.user1, friend=self.user2)

        # To powinno się udać (user2 zaprasza user1)
        reverse_friendship = Friendship.objects.create(user=self.user2, friend=self.user1)

        self.assertEqual(Friendship.objects.count(), 2)