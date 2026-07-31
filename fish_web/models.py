from django.db import models


class FishMaster(models.Model):
    """魚種マスタ：魚ごとの基本情報・おすすめ判定に使う情報を保持する"""

    # 魚種を一意に識別するための名前（システム内部用）
    name = models.CharField(max_length=50, unique=True)
    # 画面表示用の名前
    display_name = models.CharField(max_length=50)
    # 冷凍魚かどうか（Trueの場合は旬スコアの算出対象から除外する）
    is_frozen = models.BooleanField()
    # 旬の時期（例：「12月〜2月」など）
    season = models.CharField(max_length=100, blank=True)
    # 味の特徴の説明文
    taste = models.TextField(blank=True)
    # おすすめの調理方法
    cooking_method = models.CharField(max_length=200, blank=True)
    # 栄養情報の説明文
    nutrition = models.TextField(blank=True)
    # レシピ紹介ページのURL
    recipe_url = models.CharField(max_length=200, blank=True)
    # 価格帯の分類（例：「高級」「庶民」など）
    price_category = models.CharField(max_length=20, blank=True)
    # 価格の統計的な偏差値（Zスコア）。未計算の場合はNoneを許可
    z_score = models.FloatField(null=True, blank=True)
    # 代替候補となる魚種（自分自身を参照する多対多）
    alternatives = models.ManyToManyField('self', blank=True)

    def __str__(self):
        return self.display_name


class MonthlyStats(models.Model):
    """月別集計：魚種ごとの月次の取扱数量・平均単価を保持する"""

    # 対象の魚種名（FishMaster.nameに対応する値を文字列で保持）
    fish_name = models.CharField(max_length=50)
    year = models.IntegerField()
    month = models.IntegerField()
    # 取扱数量
    volume = models.FloatField()
    # 加重平均単価（CLAUDE.mdのルールに基づき加重平均で算出した値を保持）
    price = models.FloatField()

    def __str__(self):
        return f"{self.fish_name} {self.year}/{self.month}"


class ForecastResult(models.Model):
    """予測結果：将来の取扱数量・単価の予測値を保持する"""

    fish_name = models.CharField(max_length=50)
    # 予測対象の年月
    target_year = models.IntegerField()
    target_month = models.IntegerField()
    # 予測された取扱数量
    forecast_volume = models.FloatField()
    # 予測された単価
    forecast_price = models.FloatField()

    def __str__(self):
        return f"{self.fish_name} {self.target_year}/{self.target_month}"


class RecommendScore(models.Model):
    """おすすめスコア：魚種ごとの月次おすすめ度とその内訳を保持する"""

    fish_name = models.CharField(max_length=50)
    year = models.IntegerField()
    month = models.IntegerField()
    # 総合おすすめスコア
    total_score = models.FloatField()
    # 価格の安定度スコア
    price_stability = models.FloatField()
    # 価格変動リスクスコア
    price_risk = models.FloatField()
    # 価格の安さスコア
    price_cheap = models.FloatField()
    # 供給の安定度スコア
    supply_stability = models.FloatField()
    # 季節性（旬）スコア
    seasonality = models.FloatField()
    # スコアの分類（例：「おすすめ」「注意」など）
    category = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.fish_name} {self.year}/{self.month}"
