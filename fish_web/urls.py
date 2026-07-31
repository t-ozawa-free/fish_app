from django.urls import path

from . import views

# {% url 'fish_web:xxx' %}で参照するための名前空間
app_name = "fish_web"

urlpatterns = [
    # SCR001：ダッシュボード
    path("", views.DashboardView.as_view(), name="dashboard"),
    # SCR002：魚種一覧
    path("fish/", views.FishListView.as_view(), name="fish_list"),
    # SCR003：魚種詳細（魚種名をURLで受け取る）
    path("fish/<str:name>/", views.FishDetailView.as_view(), name="fish_detail"),
    # SCR004：グラフ
    path("graph/", views.GraphView.as_view(), name="graph"),
]
