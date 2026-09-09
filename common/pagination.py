from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """List envelope fixed by api.md §1.4: {items, page_info}.

    `?page=1&size=20`. `size` is capped so a client cannot request an unbounded
    page (page_size_query_param + max_page_size).
    """

    page_query_param = "page"
    page_size_query_param = "size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "items": data,
                "page_info": {
                    "page": self.page.number,
                    "size": self.get_page_size(self.request),
                    "total": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                },
            }
        )
