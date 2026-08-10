from collections import defaultdict
from datetime import date

from django.views.generic import TemplateView

from .models import FishMaster, ForecastResult, MonthlyStats, RecommendScore
from .utils import get_next_month


class DashboardView(TemplateView):
    """SCR001：ダッシュボード画面。今月・来月のカテゴリ別おすすめ魚種を表示する"""

    template_name = "fish_web/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = date.today()
        this_year, this_month = today.year, today.month
        next_year, next_month = get_next_month(this_year, this_month)

        this_scores = list(RecommendScore.objects.filter(year=this_year, month=this_month))
        next_scores = list(
            RecommendScore.objects.filter(target_year=next_year, target_month=next_month)
        )

        fish_master_map = {fish.name: fish for fish in FishMaster.objects.all()}
        this_price_map = self._build_price_map(this_scores, this_year, this_month, use_monthly_stats=True)
        next_price_map = self._build_price_map(next_scores, next_year, next_month, use_monthly_stats=False)
        this_membership = self._collect_categories(this_scores)
        next_membership = self._collect_categories(next_scores)

        context.update(
            {
                "this_year": this_year,
                "this_month": this_month,
                "next_year": next_year,
                "next_month": next_month,
                "this_season": self._build_fish_items(
                    this_scores, "旬", this_membership, fish_master_map, this_price_map
                ),
                "this_cheap": self._build_fish_items(
                    this_scores, "コスパ", this_membership, fish_master_map, this_price_map
                ),
                "this_deal": self._build_fish_items(
                    this_scores, "お得", this_membership, fish_master_map, this_price_map
                ),
                "this_caution": self._build_fish_items(
                    this_scores, "注意", this_membership, fish_master_map, this_price_map
                ),
                "next_season": self._build_fish_items(
                    next_scores, "旬", next_membership, fish_master_map, next_price_map
                ),
                "next_cheap": self._build_fish_items(
                    next_scores, "コスパ", next_membership, fish_master_map, next_price_map
                ),
                "next_deal": self._build_fish_items(
                    next_scores, "お得", next_membership, fish_master_map, next_price_map
                ),
                "next_caution": self._build_fish_items(
                    next_scores, "注意", next_membership, fish_master_map, next_price_map
                ),
            }
        )
        return context

    def _collect_categories(self, scores):
        """魚種名ごとに該当する全カテゴリの集合を作る（複数カテゴリ該当時のバッジ判定用）"""
        membership = defaultdict(set)
        for score in scores:
            membership[score.fish_name].add(score.category)
        return membership

    def _build_price_map(self, scores, year, month, use_monthly_stats):
        """対象魚種の価格をMonthlyStats（あれば）またはForecastResultから引き当てる"""
        fish_names = {score.fish_name for score in scores}
        price_map = {}

        if use_monthly_stats:
            for stats in MonthlyStats.objects.filter(fish_name__in=fish_names, year=year, month=month):
                price_map[stats.fish_name] = stats.price

        missing_names = fish_names - price_map.keys()
        if missing_names:
            for forecast in ForecastResult.objects.filter(
                fish_name__in=missing_names, target_year=year, target_month=month
            ):
                price_map[forecast.fish_name] = forecast.forecast_price

        return price_map

    def _build_fish_items(self, scores, category, membership, fish_master_map, price_map):
        """指定カテゴリに該当する魚種のカード表示用データ（辞書のリスト）を作る"""
        items = []
        for score in scores:
            if score.category != category:
                continue
            name = score.fish_name
            fish = fish_master_map.get(name)
            categories = membership.get(name, set())
            price = price_map.get(name)
            items.append(
                {
                    "fish_name": name,
                    "display_name": fish.display_name if fish else name,
                    "is_frozen": fish.is_frozen if fish else False,
                    "price": price,
                    # 100gあたりの目安価格（円/kgを10で割って切り捨て）
                    "price_per_100g": int(price // 10) if price is not None else None,
                    "is_season": "旬" in categories,
                    "is_cheap": "コスパ" in categories,
                    "is_deal": "お得" in categories,
                    "is_caution": "注意" in categories,
                }
            )
        return items


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
