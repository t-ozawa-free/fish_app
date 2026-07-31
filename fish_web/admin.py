from django.contrib import admin

from .models import FishMaster, ForecastResult, MonthlyStats, RecommendScore

# 管理画面（/admin/）からデータの確認・登録ができるように4モデルを登録する
admin.site.register(FishMaster)
admin.site.register(MonthlyStats)
admin.site.register(ForecastResult)
admin.site.register(RecommendScore)
