import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import colormath
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
import urllib.parse
import logging

class CVRRuleChecker:
    def __init__(self):
        self.rules = self.load_rules()
        self.logger = self.setup_logger()

    def setup_logger(self):
        logger = logging.getLogger('cvr_rule_checker')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def load_rules(self):
        """ルール設定をJSONから読み込む"""
        rules_path = os.path.join(os.path.dirname(__file__), 'data', 'rules.json')
        if os.path.exists(rules_path):
            with open(rules_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルトルールを返す（ここでは例としていくつかの項目を設定）
            return {
                "CTA": {
                    "CTA-1": {"name": "CTAボタンのコントラスト比", "max_score": 10, "threshold": 4.5},
                    "CTA-2": {"name": "ファーストビュー内のCTA存在", "max_score": 15, "enabled": True},
                    # 他のCTAルール...
                },
                "FORM": {
                    "FORM-1": {"name": "フォーム項目数", "max_score": 10, "ideal_count": 5},
                    # 他のフォームルール...
                },
                # 他のカテゴリ...
            }

    def check_url(self, url):
        """URLに対してすべてのルールをチェック"""
        self.logger.info(f"URLのルールチェック開始: {url}")

        # Seleniumセットアップ
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            # ページの読み込み
            driver.get(url)
            time.sleep(3)  # ページが完全に読み込まれるまで待機

            # HTMLコンテンツの取得
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            # 結果を格納する辞書
            results = {
                "url": url,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "categories": {},
                "total_score": 0,
                "max_possible_score": 0,
                "percentage": 0
            }

            # カテゴリごとにルールチェック
            for category, rules in self.rules.items():
                category_results = {
                    "rules": {},
                    "score": 0,
                    "max_score": 0,
                    "percentage": 0
                }

                for rule_id, rule_config in rules.items():
                    if rule_config.get("enabled", True):
                        # ルールメソッドの動的呼び出し
                        method_name = f"check_{rule_id.lower().replace('-', '_')}"
                        if hasattr(self, method_name):
                            rule_method = getattr(self, method_name)
                            result = rule_method(driver, soup, rule_config)

                            category_results["rules"][rule_id] = result
                            category_results["score"] += result["score"]
                            category_results["max_score"] += rule_config["max_score"]

                # カテゴリのパーセンテージを計算
                if category_results["max_score"] > 0:
                    category_results["percentage"] = round(
                        (category_results["score"] / category_results["max_score"]) * 100, 1
                    )

                results["categories"][category] = category_results
                results["total_score"] += category_results["score"]
                results["max_possible_score"] += category_results["max_score"]

            # 総合パーセンテージを計算
            if results["max_possible_score"] > 0:
                results["percentage"] = round(
                    (results["total_score"] / results["max_possible_score"]) * 100, 1
                )

            self.logger.info(f"ルールチェック完了: スコア {results['total_score']}/{results['max_possible_score']} ({results['percentage']}%)")
            return results

        except Exception as e:
            self.logger.error(f"ルールチェックエラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "url": url,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e),
                "categories": {},
                "total_score": 0,
                "max_possible_score": 0,
                "percentage": 0
            }
        finally:
            driver.quit()

    # 以下、個別ルールのチェックメソッド
    def check_cta_1(self, driver, soup, rule_config):
        """CTAボタンのコントラスト比をチェック"""
        try:
            # CTAボタンを特定（class名に'btn'や'button'を含む要素）
            cta_elements = soup.find_all(['a', 'button'], class_=lambda c: c and ('btn' in c.lower() or 'button' in c.lower() or 'cta' in c.lower()))

            if not cta_elements:
                return {
                    "name": rule_config["name"],
                    "score": 0,
                    "max_score": rule_config["max_score"],
                    "details": "CTAボタンが見つかりません"
                }

            # 最高コントラスト比を初期化
            best_contrast = 0

            for cta in cta_elements:
                # JSを実行してボタンの色と背景色を取得
                script = """
                function getColors(element) {
                    const style = window.getComputedStyle(element);
                    const bgColor = style.backgroundColor;
                    const textColor = style.color;
                    return [bgColor, textColor];
                }
                return getColors(arguments[0]);
                """
                colors = driver.execute_script(script, driver.find_element_by_xpath(f"//*[text()='{cta.text}']"))

                # RGB値を抽出（形式: 'rgb(r, g, b)' または 'rgba(r, g, b, a)'）
                bg_color = self.parse_rgb(colors[0])
                text_color = self.parse_rgb(colors[1])

                if bg_color and text_color:
                    # コントラスト比の計算
                    contrast = self.calculate_contrast(bg_color, text_color)
                    if contrast > best_contrast:
                        best_contrast = contrast

            # スコアの計算
            threshold = rule_config.get("threshold", 4.5)
            if best_contrast >= threshold:
                score = rule_config["max_score"]
                details = f"良好なコントラスト比: {best_contrast:.2f} (推奨: {threshold}以上)"
            else:
                # コントラスト比に比例したスコア
                score = int((best_contrast / threshold) * rule_config["max_score"])
                details = f"コントラスト比が不足: {best_contrast:.2f} (推奨: {threshold}以上)"

            return {
                "name": rule_config["name"],
                "score": score,
                "max_score": rule_config["max_score"],
                "details": details,
                "contrast_ratio": best_contrast
            }

        except Exception as e:
            self.logger.error(f"CTA-1チェックエラー: {str(e)}")
            return {
                "name": rule_config["name"],
                "score": 0,
                "max_score": rule_config["max_score"],
                "details": f"エラー: {str(e)}"
            }

    def parse_rgb(self, color_str):
        """RGB文字列からRGB値を抽出"""
        if not color_str:
            return None

        match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)', color_str)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return None

    def calculate_contrast(self, color1, color2):
        """2色間のコントラスト比を計算"""
        # L*値の計算（輝度）
        def calculate_luminance(rgb):
            rgb_normalized = [c/255 for c in rgb]
            rgb_linear = [c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4 for c in rgb_normalized]
            return 0.2126 * rgb_linear[0] + 0.7152 * rgb_linear[1] + 0.0722 * rgb_linear[2]

        l1 = calculate_luminance(color1)
        l2 = calculate_luminance(color2)

        # 明るい色/暗い色の比率
        if l1 > l2:
            return (l1 + 0.05) / (l2 + 0.05)
        else:
            return (l2 + 0.05) / (l1 + 0.05)

    def check_cta_2(self, driver, soup, rule_config):
        """ファーストビュー内のCTA存在をチェック"""
        try:
            # ページの高さを取得
            viewport_height = driver.execute_script("return window.innerHeight")

            # CTAボタンを特定
            cta_elements = soup.find_all(['a', 'button'], class_=lambda c: c and ('btn' in c.lower() or 'button' in c.lower() or 'cta' in c.lower()))

            if not cta_elements:
                return {
                    "name": rule_config["name"],
                    "score": 0,
                    "max_score": rule_config["max_score"],
                    "details": "CTAボタンが見つかりません"
                }

            # CTAの位置をチェック
            cta_in_viewport = False

            for cta in cta_elements:
                # 要素の位置を取得
                try:
                    element = driver.find_element_by_xpath(f"//*[contains(text(), '{cta.text.strip()}')]")
                    location = element.location['y']

                    # ビューポート内にあるかチェック
                    if location <= viewport_height:
                        cta_in_viewport = True
                        break
                except:
                    continue

            if cta_in_viewport:
                return {
                    "name": rule_config["name"],
                    "score": rule_config["max_score"],
                    "max_score": rule_config["max_score"],
                    "details": "ファーストビュー内にCTAが存在します"
                }
            else:
                return {
                    "name": rule_config["name"],
                    "score": 0,
                    "max_score": rule_config["max_score"],
                    "details": "ファーストビュー内にCTAが見つかりません"
                }

        except Exception as e:
            self.logger.error(f"CTA-2チェックエラー: {str(e)}")
            return {
                "name": rule_config["name"],
                "score": 0,
                "max_score": rule_config["max_score"],
                "details": f"エラー: {str(e)}"
            }

    # 他のチェックメソッドも同様に実装...
    # 例えば:
    def check_form_1(self, driver, soup, rule_config):
        """フォーム項目数をチェック"""
        try:
            # フォーム要素を検索
            forms = soup.find_all('form')

            if not forms:
                return {
                    "name": rule_config["name"],
                    "score": rule_config["max_score"] // 2,  # フォームがない場合は中間点
                    "max_score": rule_config["max_score"],
                    "details": "フォームが見つかりません"
                }

            # 最も入力項目の少ないフォームを評価対象とする
            min_fields = float('inf')
            for form in forms:
                input_fields = form.find_all(['input', 'textarea', 'select'])
                # type="hidden"や"submit"は除外
                visible_fields = [f for f in input_fields if f.get('type') not in ['hidden', 'submit', 'button']]
                if len(visible_fields) < min_fields and len(visible_fields) > 0:
                    min_fields = len(visible_fields)

            if min_fields == float('inf'):
                min_fields = 0

            # 理想の項目数に基づいてスコア計算
            ideal_count = rule_config.get("ideal_count", 5)
            if min_fields <= ideal_count:
                score = rule_config["max_score"]
                details = f"フォーム項目数は適切です: {min_fields}項目 (理想: {ideal_count}以下)"
            else:
                # 項目数が多いほどスコア減少
                reduction_factor = (min_fields - ideal_count) * 0.2
                score = max(0, int(rule_config["max_score"] * (1 - reduction_factor)))
                details = f"フォーム項目数が多すぎます: {min_fields}項目 (理想: {ideal_count}以下)"

            return {
                "name": rule_config["name"],
                "score": score,
                "max_score": rule_config["max_score"],
                "details": details,
                "field_count": min_fields
            }

        except Exception as e:
            self.logger.error(f"FORM-1チェックエラー: {str(e)}")
            return {
                "name": rule_config["name"],
                "score": 0,
                "max_score": rule_config["max_score"],
                "details": f"エラー: {str(e)}"
            }
