from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Aviso dentro do site: um texto curto que leva para a página do assunto."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="notifications", verbose_name="destinatário")
    # O texto é gravado pronto: se a peça mudar de nome depois, o aviso conta o que aconteceu na hora.
    text = models.CharField("texto", max_length=200)
    url = models.CharField("link", max_length=200)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    # Vazio enquanto a pessoa não viu o aviso na página de avisos.
    read_at = models.DateTimeField("lido em", null=True, blank=True)

    class Meta:
        verbose_name = "aviso"
        verbose_name_plural = "avisos"

    def __str__(self):
        return self.text

    @property
    def is_read(self):
        return self.read_at is not None
