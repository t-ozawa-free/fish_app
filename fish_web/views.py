from django.views.generic import TemplateView


class DashboardView(TemplateView):
    """SCR001：ダッシュボード画面（中身は今後実装、現状はタイトルのみ）"""

    template_name = "fish_web/dashboard.html"


class FishListView(TemplateView):
    """SCR002：魚種一覧画面（中身は今後実装、現状はタイトルのみ）"""

    template_name = "fish_web/fish_list.html"


class FishDetailView(TemplateView):
    """SCR003：魚種詳細画面。URLで指定された魚種名をテンプレートに渡す"""

    template_name = "fish_web/fish_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # URLパラメータ<str:name>で指定された魚種名を画面に渡す
        context["name"] = kwargs.get("name")
        return context


class GraphView(TemplateView):
    """SCR004：グラフ画面（中身は今後実装、現状はタイトルのみ）"""

    template_name = "fish_web/graph.html"
