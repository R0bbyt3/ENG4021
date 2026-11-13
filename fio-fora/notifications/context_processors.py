from .services import unread_count


def unread_notifications(request):
    """Disponibiliza unread_notifications em todos os templates, para o sininho do cabeçalho."""
    if not request.user.is_authenticated:
        return {'unread_notifications': 0}
    return {'unread_notifications': unread_count(request.user)}
