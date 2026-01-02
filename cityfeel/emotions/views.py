from rest_framework import viewsets, permissions
from .models import EmotionPoint, Comment, Photo
from .serializers import EmotionPointSerializer, CommentSerializer, PhotoSerializer

class EmotionPointViewSet(viewsets.ModelViewSet):
    queryset = EmotionPoint.objects.all()
    serializer_class = EmotionPointSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CommentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows comments to be viewed or created.
    """
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    # Automatycznie przypisz zalogowanego u¿ytkownika jako autora
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PhotoViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows photos to be viewed or uploaded.
    """
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]