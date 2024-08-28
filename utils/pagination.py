from rest_framework.pagination import PageNumberPagination

class SmallPagesPagination(PageNumberPagination):
    page_size = 5


class NormalPagesPagination(PageNumberPagination):
    page_size = 10

class LargePagesPagination(PageNumberPagination):
    page_size = 50