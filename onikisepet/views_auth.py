from django.contrib.auth.views import LoginView

from onikisepet.permissions import get_post_login_redirect_url


class RoleAwareLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        return get_post_login_redirect_url(self.request.user)
