from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Notification
from .services import mark_read


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at', '-pk')
    page = Paginator(notifications, 20).get_page(request.GET.get('page'))
    # A lista é montada antes de marcar como lido, para a tela ainda destacar o que era novo.
    shown = list(page)
    mark_read(shown)
    return render(request, 'notifications/list.html', {'page_obj': page, 'notifications': shown})
