from collections import defaultdict
from datetime import date

from django.http import QueryDict
from django.views.generic import TemplateView

from .models import FishMaster, ForecastResult, MonthlyStats, RecommendScore
from .utils import get_next_month


def _build_price_map(fish_names, year, month, use_monthly_stats):
    """対象魚種名の価格をMonthlyStats（あれば）またはForecastResultから引き当てる"""
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


def _collect_categories(scores):
    """魚種名ごとに該当する全カテゴリの集合を作る（複数カテゴリ該当時のバッジ判定用）"""
    membership = defaultdict(set)
    for score in scores:
        membership[score.fish_name].add(score.category)
    return membership


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
        this_price_map = _build_price_map(
            {score.fish_name for score in this_scores}, this_year, this_month, use_monthly_stats=True
        )
        next_price_map = _build_price_map(
            {score.fish_name for score in next_scores}, next_year, next_month, use_monthly_stats=False
        )
        this_membership = _collect_categories(this_scores)
        next_membership = _collect_categories(next_scores)

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

    def _build_fish_items(self, scores, category, membership, fish_master_map, price_map):
        """指定カテゴリに該当する魚種のカード表示用データ（辞書のリスト）を作る"""
        items = []
        for score in scores:
            if score.category != category:
                continue
            name = score.fish_name
            fish = fish_master_map.get(name)
            categories = membership.get(name, set())
            items.append(
                {
                    "fish_name": name,
                    "display_name": fish.display_name if fish else name,
                    "is_frozen": fish.is_frozen if fish else False,
                    "price": price_map.get(name),
                    "is_season": "旬" in categories,
                    "is_cheap": "コスパ" in categories,
                    "is_deal": "お得" in categories,
                    "is_caution": "注意" in categories,
                }
            )
        return items


class FishListView(TemplateView):
    """SCR002：魚種一覧画面。全魚種をカード一覧表示し、並び替え・絞り込みに対応する"""

    template_name = "fish_web/fish_list.html"

    # 並び替えの選択肢（value, 表示ラベル）
    SORT_OPTIONS = [
        ("recommend", "おすすめ順"),
        ("price_asc", "価格が安い順"),
        ("price_desc", "価格が高い順"),
    ]
    # 絞り込みの選択肢（value, 表示ラベル）
    FILTER_OPTIONS = [
        ("season", "今が旬"),
        ("fresh", "鮮魚のみ"),
        ("frozen", "冷凍のみ"),
        ("no_caution", "注意を除く"),
    ]
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sort = self._get_sort(self.request)
        filters = self._get_filters(self.request)

        today = date.today()
        this_year, this_month = today.year, today.month

        fish_masters = list(FishMaster.objects.all().order_by("name"))
        fish_names = {fish.name for fish in fish_masters}
        price_map = _build_price_map(fish_names, this_year, this_month, use_monthly_stats=True)
        scores = list(
            RecommendScore.objects.filter(year=this_year, month=this_month, fish_name__in=fish_names)
        )
        membership = _collect_categories(scores)

        fish_list = [self._build_item(fish, membership, price_map) for fish in fish_masters]
        fish_list = self._apply_filters(fish_list, filters)
        fish_list = self._apply_sort(fish_list, sort)

        context.update(
            {
                "fish_list": fish_list,
                "sort": sort,
                "filters": filters,
                "sort_options": self.SORT_OPTIONS,
                "filter_tags": self._build_filter_tags(filters, sort),
            }
        )
        return context

    def _get_sort(self, request):
        """並び替え指定をGETパラメータから取得する。不正な値はおすすめ順にフォールバックする"""
        sort = request.GET.get("sort", "recommend")
        valid_sorts = {key for key, _ in self.SORT_OPTIONS}
        return sort if sort in valid_sorts else "recommend"

    def _get_filters(self, request):
        """絞り込み指定をGETパラメータから取得する（複数選択可、不正な値は無視）"""
        valid_filters = {key for key, _ in self.FILTER_OPTIONS}
        return [f for f in request.GET.getlist("filter") if f in valid_filters]

    def _build_item(self, fish, membership, price_map):
        """1魚種分のカード表示用データ（辞書）を作る"""
        categories = membership.get(fish.name, set())
        return {
            "fish_name": fish.name,
            "display_name": fish.display_name,
            "is_frozen": fish.is_frozen,
            "price": price_map.get(fish.name),
            "is_season": "旬" in categories,
            "is_cheap": "コスパ" in categories,
            "is_deal": "お得" in categories,
            "is_caution": "注意" in categories,
        }

    def _apply_filters(self, fish_list, filters):
        """選択中の絞り込み条件をAND条件で適用する"""
        if "season" in filters:
            fish_list = [f for f in fish_list if f["is_season"]]
        if "frozen" in filters:
            fish_list = [f for f in fish_list if f["is_frozen"]]
        if "fresh" in filters:
            fish_list = [f for f in fish_list if not f["is_frozen"]]
        if "no_caution" in filters:
            fish_list = [f for f in fish_list if not f["is_caution"]]
        return fish_list

    def _apply_sort(self, fish_list, sort):
        """指定された並び順で魚種リストを並び替える"""
        if sort == "price_asc":
            return sorted(fish_list, key=lambda f: (f["price"] is None, f["price"] or 0))
        if sort == "price_desc":
            return sorted(fish_list, key=lambda f: (f["price"] is None, -(f["price"] or 0)))
        return sorted(fish_list, key=lambda f: (self._category_rank(f), f["display_name"]))

    def _category_rank(self, fish):
        """おすすめ順の優先度：旬 > コスパ > お得 > 注意のみ > 該当なし"""
        for rank, category_key in enumerate(("is_season", "is_cheap", "is_deal")):
            if fish[category_key]:
                return rank
        if fish["is_caution"]:
            return 3
        return 4

    def _build_filter_tags(self, filters, sort):
        """絞り込みタグごとのON/OFF切り替え用リンクを作る（JS不使用のためGETリンクで実現）"""
        tags = []
        for key, label in self.FILTER_OPTIONS:
            active = key in filters
            next_filters = [f for f in filters if f != key] if active else filters + [key]
            query = QueryDict(mutable=True)
            query["sort"] = sort
            for f in next_filters:
                query.appendlist("filter", f)
            tags.append({"key": key, "label": label, "active": active, "url": f"?{query.urlencode()}"})
        return tags


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
