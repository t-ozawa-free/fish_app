"""市場データCSVを集計・予測・スコア算出してDBに登録する管理コマンド"""
import csv
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand

from fish_web.models import FishMaster, ForecastResult, MonthlyStats, RecommendScore

# コスパ最強・今だけお得・値上がり注意で表示する上位件数
TOP_N = 4


class Command(BaseCommand):
    """python manage.py update_market_data で実行する市場データ更新コマンド"""

    help = '市場データCSVを集計・予測・スコア算出してDBに登録する'

    def handle(self, *args, **options):
        self._step1_monthly_stats()
        self._step2_forecast_result()
        self._step3_recommend_score()
        self._step4_cleanup_question_log()

    def _read_csv(self, filename):
        """app/data配下のCSVをBOM付きUTF-8として読み込みdictのリストを返す"""
        path = settings.BASE_DIR / 'data' / filename
        with open(path, encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))

    # ------------------------------------------------------------------
    # Step1: MonthlyStatsの登録
    # ------------------------------------------------------------------
    def _step1_monthly_stats(self):
        self.stdout.write('Step1: MonthlyStatsの登録を開始します')
        try:
            rows = self._read_csv('monthly_weighted.csv')
        except OSError as e:
            self.stderr.write(f'Step1: monthly_weighted.csvの読み込みに失敗しました: {e}')
            return

        objects = [
            MonthlyStats(
                fish_name=row['品目名称'],
                year=int(row['年']),
                month=int(row['月']),
                volume=float(row['取扱数量']),
                price=float(row['平均単価']),
            )
            for row in rows
        ]

        # 既存データを全削除してから登録し直す
        MonthlyStats.objects.all().delete()
        MonthlyStats.objects.bulk_create(objects)

        self.stdout.write(f'Step1: MonthlyStatsの登録が完了しました（{len(objects)}件）')

    # ------------------------------------------------------------------
    # Step2: ForecastResultの登録
    # ------------------------------------------------------------------
    def _step2_forecast_result(self):
        self.stdout.write('Step2: ForecastResultの登録を開始します')
        try:
            rows = self._read_csv('forecast_result.csv')
        except OSError as e:
            self.stderr.write(f'Step2: forecast_result.csvの読み込みに失敗しました: {e}')
            return

        objects = [
            ForecastResult(
                fish_name=row['品目名称'],
                target_year=int(row['年']),
                target_month=int(row['月']),
                forecast_volume=float(row['予測取扱数量']),
                forecast_price=float(row['予測平均単価']),
            )
            for row in rows
        ]

        # 既存データを全削除してから登録し直す
        ForecastResult.objects.all().delete()
        ForecastResult.objects.bulk_create(objects)

        self.stdout.write(f'Step2: ForecastResultの登録が完了しました（{len(objects)}件）')

    # ------------------------------------------------------------------
    # Step3: RecommendScoreの登録
    # ------------------------------------------------------------------
    def _step3_recommend_score(self):
        self.stdout.write('Step3: RecommendScoreの登録を開始します')
        try:
            # 月平均取扱数量（コスパ最強・今だけお得・旬だから食べようの数量判定に使用）
            overall_stats = {
                row['品目名称']: float(row['月平均取扱数量'])
                for row in self._read_csv('overall_stats.csv')
            }
            # 魚種間Zスコア（コスパ最強の判定に使用）
            cross_zscores = {
                row['品目名称']: float(row['Zスコア'])
                for row in self._read_csv('zscore_weighted.csv')
            }
            # 価格トレンド（値上がり注意の判定に使用）
            trends = {
                row['品目名称']: row['価格トレンド']
                for row in self._read_csv('trend_result.csv')
            }
            # 時系列Zスコア（コスパ最強・今だけお得・値上がり注意の判定に使用）
            # CSVの最新年月は問わず、ファイルの内容がそのまま「現在の価格ポジション」を表す
            time_zscores = {
                row['品目名称']: float(row['時系列Zスコア'])
                for row in self._read_csv('latest_price_zscore.csv')
            }
        except OSError as e:
            self.stderr.write(f'Step3: CSVの読み込みに失敗しました: {e}')
            return

        today = date.today()
        this_year, this_month = today.year, today.month

        shun_list = []
        kospa_candidates = []
        otoku_candidates = []
        chuui_candidates = []

        for fish in FishMaster.objects.all():
            name = fish.name
            volume = self._resolve_current_volume(name, this_year, this_month)
            avg_volume = overall_stats.get(name)
            cross_zscore = cross_zscores.get(name)
            time_zscore = time_zscores.get(name)
            trend = trends.get(name)

            # 値上がり注意：時系列Zスコアと価格トレンドのみで判定する（取扱数量は問わない）
            is_chuui = (
                time_zscore is not None
                and trend is not None
                and time_zscore >= 1.0
                and trend == '上昇傾向'
            )
            if is_chuui:
                chuui_candidates.append((name, time_zscore))

            # 旬だから食べよう：値上がり注意でも対象に含める
            if (
                volume is not None
                and avg_volume is not None
                and this_month in fish.season
                and not fish.is_frozen
                and volume >= avg_volume * 0.5
            ):
                shun_list.append(name)

            # コスパ最強：値上がり注意に該当する魚種は除外する
            if (
                not is_chuui
                and volume is not None
                and avg_volume is not None
                and cross_zscore is not None
                and time_zscore is not None
                and cross_zscore <= 0.0
                and time_zscore <= 0.0
                and volume >= avg_volume * 0.7
            ):
                kospa_candidates.append((name, volume))

            # 今だけお得：値上がり注意に該当する魚種は除外する
            if (
                not is_chuui
                and volume is not None
                and avg_volume is not None
                and time_zscore is not None
                and time_zscore <= -0.5
                and volume >= avg_volume * 0.7
            ):
                otoku_candidates.append((name, time_zscore))

        # 上位件数制限：コスパは取扱数量が多い順、お得・注意は時系列Zスコアで昇順/降順に上位4件
        kospa_list = [
            name for name, _ in sorted(kospa_candidates, key=lambda x: x[1], reverse=True)[:TOP_N]
        ]
        otoku_list = [
            name for name, _ in sorted(otoku_candidates, key=lambda x: x[1])[:TOP_N]
        ]
        chuui_list = [
            name for name, _ in sorted(chuui_candidates, key=lambda x: x[1], reverse=True)[:TOP_N]
        ]

        objects = (
            [self._build_recommend_score(name, this_year, this_month, '旬') for name in shun_list]
            + [self._build_recommend_score(name, this_year, this_month, 'コスパ') for name in kospa_list]
            + [self._build_recommend_score(name, this_year, this_month, 'お得') for name in otoku_list]
            + [self._build_recommend_score(name, this_year, this_month, '注意') for name in chuui_list]
        )

        # 既存データを全削除してから登録し直す
        RecommendScore.objects.all().delete()
        RecommendScore.objects.bulk_create(objects)

        self.stdout.write(
            'Step3: RecommendScoreの登録が完了しました'
            f'（旬:{len(shun_list)}件 コスパ:{len(kospa_list)}件 '
            f'お得:{len(otoku_list)}件 注意:{len(chuui_list)}件 合計:{len(objects)}件）'
        )

    def _resolve_current_volume(self, fish_name, year, month):
        """今月の取扱数量を取得する。実績データが無い場合は予測データで代用する"""
        actual = MonthlyStats.objects.filter(fish_name=fish_name, year=year, month=month).first()
        if actual is not None:
            return actual.volume

        forecast = ForecastResult.objects.filter(
            fish_name=fish_name, target_year=year, target_month=month
        ).first()
        if forecast is not None:
            return forecast.forecast_volume

        self.stderr.write(f'Step3: {fish_name}の{year}年{month}月の取扱数量データが見つかりません')
        return None

    def _build_recommend_score(self, fish_name, year, month, category):
        """RecommendScoreを生成する。数値スコアの算出方法は未定義のため0.0で登録する"""
        return RecommendScore(
            fish_name=fish_name,
            year=year,
            month=month,
            total_score=0.0,
            price_stability=0.0,
            price_risk=0.0,
            price_cheap=0.0,
            supply_stability=0.0,
            seasonality=0.0,
            category=category,
        )

    # ------------------------------------------------------------------
    # Step4: 古いログの削除
    # ------------------------------------------------------------------
    def _step4_cleanup_question_log(self):
        self.stdout.write('Step4: 古いログの削除を開始します')
        # QuestionLogモデルが未実装のため削除処理はスキップする
        self.stdout.write('Step4: QuestionLogモデルが未実装のためスキップしました')
