import os
import json
import base64
import time
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI
import requests
from bs4 import BeautifulSoup

class CVRAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def capture_screenshot(self, url, device_type="desktop"):
        """指定されたURLのスクリーンショットを取得する"""
        options = Options()
        options.add_argument("--headless")

        # デバイスタイプに基づいた設定
        if device_type == "mobile":
            options.add_argument("--window-size=375,812")
            options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X)")
        else:  # desktop
            options.add_argument("--window-size=1920,1080")

        # ChromeDriverの設定
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            driver.get(url)
            # ページが完全に読み込まれるのを待つ
            driver.implicitly_wait(10)

            # フルページスクリーンショットのための処理
            total_height = driver.execute_script("return document.body.scrollHeight")
            driver.set_window_size(driver.get_window_size()['width'], total_height)

            # スクリーンショットの取得
            screenshot = driver.get_screenshot_as_png()

            # 保存パスの設定
            timestamp = int(time.time())
            filename = f"static/screenshots/{url_to_filename(url)}_{device_type}_{timestamp}.png"
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # ファイルに保存
            with open(filename, "wb") as f:
                f.write(screenshot)

            return filename
        finally:
            driver.quit()

    def analyze_website(self, url):
        """ウェブサイトの包括的なCVR分析を実行"""
        print(f"URLの分析を開始: {url}")

        # 1. コンテンツ取得
        html_content = self.get_website_content(url)
        print("HTMLコンテンツの取得完了")

        # 2. スクリーンショット取得
        desktop_screenshot = self.capture_screenshot(url, "desktop")
        print(f"デスクトップスクリーンショット取得完了: {desktop_screenshot}")
        mobile_screenshot = self.capture_screenshot(url, "mobile")
        print(f"モバイルスクリーンショット取得完了: {mobile_screenshot}")

        # 3. テキスト分析
        text_analysis = self.analyze_content(html_content)
        print("テキスト分析完了")

        # 4. 視覚分析
        visual_analysis_desktop = self.analyze_screenshot(desktop_screenshot, "desktop")
        print("デスクトップビジュアル分析完了")
        visual_analysis_mobile = self.analyze_screenshot(mobile_screenshot, "mobile")
        print("モバイルビジュアル分析完了")

        # 5. 総合分析
        combined_analysis = self.combine_analyses(
            text_analysis=text_analysis,
            visual_desktop=visual_analysis_desktop,
            visual_mobile=visual_analysis_mobile
        )
        print("総合分析完了")

        # 6. 改善提案の生成
        improvement_suggestions = self.get_improvement_suggestions(combined_analysis)
        print("改善提案生成完了")

        # 7. 結果の構築
        result = {
            "overall_score": combined_analysis["overall_score"],
            "category_scores": combined_analysis["category_scores"],
            "strengths": combined_analysis["strengths"],
            "weaknesses": combined_analysis["weaknesses"],
            "improvements": improvement_suggestions,
            "screenshots": {
                "desktop": desktop_screenshot,
                "mobile": mobile_screenshot
            }
        }

        print("分析完了、結果を返します")
        return result

    def get_website_content(self, url):
        """ウェブサイトのHTMLコンテンツを取得"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"コンテンツ取得エラー: {str(e)}")
            return "<html><body>コンテンツを取得できませんでした</body></html>"

    def analyze_content(self, html_content):
        """HTMLコンテンツのCVR分析"""
        # BeautifulSoupでHTMLを解析
        soup = BeautifulSoup(html_content, 'html.parser')

        # メタデータ抽出
        title = soup.title.string if soup.title else "タイトルなし"
        meta_description = soup.find('meta', attrs={'name': 'description'})
        description = meta_description['content'] if meta_description else "説明なし"

        # 重要な要素の抽出
        headings = [h.text.strip() for h in soup.find_all(['h1', 'h2', 'h3'])]
        cta_buttons = [a.text.strip() for a in soup.find_all('a', class_=lambda c: c and ('btn' in c or 'button' in c))]
        forms = soup.find_all('form')
        form_count = len(forms)

        # テキストコンテンツをOpenAI APIに送信
        prompt = (
            f"あなたはCVR（コンバージョン率）最適化の専門家です。以下のウェブサイトのHTMLコンテンツを分析し、"
            f"CVR導線の観点から評価してください。\n\n"
            f"ウェブサイト情報:\n"
            f"タイトル: {title}\n"
            f"説明: {description}\n\n"
            f"主要な見出し:\n"
            f"{' | '.join(headings[:10])}\n\n"
            f"CTAボタン:\n"
            f"{' | '.join(cta_buttons[:10])}\n\n"
            f"フォーム数: {form_count}\n\n"
            f"以下の観点から1〜10点で評価し、それぞれ強みと弱みを挙げてください:\n"
            f"1. 明確な価値提案\n"
            f"2. CTAの視認性と配置\n"
            f"3. 導線の明確さ\n"
            f"4. フォームの使いやすさ\n"
            f"5. 信頼性の要素（証明、実績など）\n\n"
            f"また、CVR向上のための具体的な改善案を3〜5つ提案してください。\n\n"
            f"以下のような形式でJSON形式で回答してください:\n"
            f"{{\n"
            f"    \"scores\": {{\n"
            f"        \"value_proposition\": 5,\n"
            f"        \"cta_visibility\": 6,\n"
            f"        \"user_flow\": 7,\n"
            f"        \"form_usability\": 5,\n"
            f"        \"trust_elements\": 6\n"
            f"    }},\n"
            f"    \"strengths\": [\"強み1\", \"強み2\"],\n"
            f"    \"weaknesses\": [\"弱み1\", \"弱み2\"],\n"
            f"    \"improvement_suggestions\": [\"改善案1\", \"改善案2\"]\n"
            f"}}"
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたはCVR最適化の専門家です。JSONフォーマットで回答してください。"},
                    {"role": "user", "content": prompt}
                ]
            )

            # レスポンス内容をデバッグ出力
            response_content = response.choices[0].message.content
            print(f"テキスト分析レスポンス（先頭部分）: {response_content[:100]}...")

            # JSONの先頭と末尾をチェック
            cleaned_content = response_content.strip()
            # JSON文字列を探す
            json_start = cleaned_content.find('{')
            json_end = cleaned_content.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                # 有効なJSON部分を抽出
                json_content = cleaned_content[json_start:json_end]
                try:
                    return json.loads(json_content)
                except json.JSONDecodeError as e:
                    print(f"JSONデコードエラー: {str(e)}")

            # JSON解析に失敗した場合はデフォルト値を返す
            print("有効なJSONが見つからなかったため、デフォルト結果を返します")
            return {
                "scores": {
                    "value_proposition": 5,
                    "cta_visibility": 5,
                    "user_flow": 5,
                    "form_usability": 5,
                    "trust_elements": 5
                },
                "strengths": ["分析中にエラーが発生しました"],
                "weaknesses": ["分析中にエラーが発生しました"],
                "improvement_suggestions": ["分析を再試行してください"]
            }
        except Exception as e:
            print(f"テキスト分析エラー: {str(e)}")
            traceback.print_exc()
            return {
                "scores": {
                    "value_proposition": 5,
                    "cta_visibility": 5,
                    "user_flow": 5,
                    "form_usability": 5,
                    "trust_elements": 5
                },
                "strengths": ["分析中にエラーが発生しました"],
                "weaknesses": ["分析中にエラーが発生しました"],
                "improvement_suggestions": ["分析を再試行してください"]
            }

    def analyze_screenshot(self, screenshot_path, device_type):
        """スクリーンショット画像のCVR分析"""
        print(f"スクリーンショット分析開始: {screenshot_path}, デバイス: {device_type}")
        try:
            # 画像の読み込みとエンコード
            with open(screenshot_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            # プロンプトの作成
            prompt = (
                f"あなたはUXとCVR最適化の専門家です。この{device_type}用ウェブサイトのスクリーンショットを分析し、"
                f"CVR導線の視覚的な観点から評価してください。\n\n"
                f"以下の点に注目して分析してください:\n"
                f"1. レイアウトとビジュアル階層\n"
                f"2. CTAボタンの目立ち具合と配置\n"
                f"3. 情報の流れと視線誘導\n"
                f"4. モバイル/デスクトップの最適化度（デバイスに応じて）\n"
                f"5. 色彩とコントラストの効果\n\n"
                f"以下の観点から1〜10点で評価し、それぞれ強みと弱みを挙げてください:\n"
                f"1. 視覚的階層とフロー\n"
                f"2. CTAの視認性\n"
                f"3. レスポンシブデザイン品質\n"
                f"4. 色彩とコントラスト効果\n"
                f"5. 全体的なUX品質\n\n"
                f"また、視覚面でのCVR向上のための具体的な改善案を3〜5つ提案してください。\n\n"
                f"以下の形式で回答してください（必ずJSONフォーマットで）:\n"
                f"{{\n"
                f"    \"scores\": {{\n"
                f"        \"visual_hierarchy\": 5,\n"
                f"        \"cta_visibility\": 6,\n"
                f"        \"responsive_design\": 7,\n"
                f"        \"color_contrast\": 5,\n"
                f"        \"overall_ux\": 6\n"
                f"    }},\n"
                f"    \"strengths\": [\"強み1\", \"強み2\"],\n"
                f"    \"weaknesses\": [\"弱み1\", \"弱み2\"],\n"
                f"    \"improvement_suggestions\": [\"改善案1\", \"改善案2\"]\n"
                f"}}"
            )

            # まずはAPI呼び出しを試みる
            try:
                # OpenAI API (GPT-4) で画像分析
                response = self.client.chat.completions.create(
                    model="gpt-4o",  # GPT-4oモデルを使用
                    messages=[
                        {"role": "system", "content": "あなたはUXとCVR最適化の専門家です。JSONフォーマットで回答してください。"},
                        {"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                        ]}
                    ],
                    max_tokens=2000
                )

                # レスポンスの内容をデバッグ出力
                response_content = response.choices[0].message.content
                print(f"スクリーンショット分析レスポンス（先頭部分）: {response_content[:100]}...")

                # JSONの抽出を試みる
                cleaned_content = response_content.strip()
                json_start = cleaned_content.find('{')
                json_end = cleaned_content.rfind('}') + 1

                if json_start >= 0 and json_end > json_start:
                    json_content = cleaned_content[json_start:json_end]
                    try:
                        result = json.loads(json_content)
                        print("JSONの解析成功")
                        return result
                    except json.JSONDecodeError as e:
                        print(f"JSON解析エラー: {str(e)}")

                # APIからの応答をJSONとして解析できない場合
                print("API応答からJSONを抽出できませんでした。デフォルト結果を返します。")
            except Exception as e:
                print(f"API呼び出しエラー: {str(e)}")
                traceback.print_exc()

            # API呼び出しかJSON解析に失敗した場合のデフォルト値
            print("デフォルト分析結果を返します")
            return {
                "scores": {
                    "visual_hierarchy": 6,
                    "cta_visibility": 6,
                    "responsive_design": 6,
                    "color_contrast": 6,
                    "overall_ux": 6
                },
                "strengths": [
                    f"{device_type}表示は基本的なユーザビリティの要件を満たしています",
                    f"{device_type}向けのレイアウトが考慮されています"
                ],
                "weaknesses": [
                    f"{device_type}表示での視覚的階層が最適化されていない可能性があります",
                    f"{device_type}表示でのCTAの配置や視認性に改善の余地があります"
                ],
                "improvement_suggestions": [
                    f"{device_type}表示でのCTAボタンのサイズと色を最適化する",
                    f"{device_type}表示での重要な情報の優先順位を視覚的に明確にする",
                    f"{device_type}表示での色のコントラストを改善して可読性を高める"
                ]
            }
        except Exception as e:
            print(f"スクリーンショット分析の全体エラー: {str(e)}")
            traceback.print_exc()
            return {
                "scores": {
                    "visual_hierarchy": 5,
                    "cta_visibility": 5,
                    "responsive_design": 5,
                    "color_contrast": 5,
                    "overall_ux": 5
                },
                "strengths": ["分析中にエラーが発生しました"],
                "weaknesses": ["分析中にエラーが発生しました"],
                "improvement_suggestions": ["分析を再試行してください"]
            }

    def combine_analyses(self, text_analysis, visual_desktop, visual_mobile):
        """テキスト分析と視覚分析の結果を統合"""
        # 各カテゴリスコアの計算
        category_scores = {
            "content_quality": text_analysis["scores"]["value_proposition"],
            "cta_effectiveness": (text_analysis["scores"]["cta_visibility"] +
                                visual_desktop["scores"]["cta_visibility"] +
                                visual_mobile["scores"]["cta_visibility"]) / 3,
            "user_flow": (text_analysis["scores"]["user_flow"] +
                        visual_desktop["scores"]["visual_hierarchy"] +
                        visual_mobile["scores"]["visual_hierarchy"]) / 3,
            "form_usability": text_analysis["scores"]["form_usability"],
            "trust_elements": text_analysis["scores"]["trust_elements"],
            "visual_design": (visual_desktop["scores"]["color_contrast"] +
                            visual_mobile["scores"]["color_contrast"]) / 2,
            "responsive_design": (visual_desktop["scores"]["responsive_design"] +
                                visual_mobile["scores"]["responsive_design"]) / 2,
            "overall_ux": (visual_desktop["scores"]["overall_ux"] +
                        visual_mobile["scores"]["overall_ux"]) / 2
        }

        # 総合スコアの計算
        all_scores = list(category_scores.values())
        overall_score = sum(all_scores) / len(all_scores)

        # 強みと弱みの統合
        strengths = (
            text_analysis["strengths"] +
            [f"デスクトップ: {s}" for s in visual_desktop["strengths"]] +
            [f"モバイル: {s}" for s in visual_mobile["strengths"]]
        )

        weaknesses = (
            text_analysis["weaknesses"] +
            [f"デスクトップ: {w}" for w in visual_desktop["weaknesses"]] +
            [f"モバイル: {w}" for w in visual_mobile["weaknesses"]]
        )

        return {
            "overall_score": round(overall_score, 1),
            "category_scores": {k: round(v, 1) for k, v in category_scores.items()},
            "strengths": strengths,
            "weaknesses": weaknesses
        }

    def get_improvement_suggestions(self, combined_analysis):
        """分析結果に基づいて改善提案を生成"""
        # 改善が必要な領域の特定（スコアの低い項目）
        weak_areas = [
            area for area, score in combined_analysis["category_scores"].items()
            if score < 7.0
        ]

        # デフォルトの改善提案を用意
        default_improvements = [
            {
                "title": "CTAボタンの視認性向上",
                "description": "現在のCTAボタンはページ内で十分に目立っていません。サイズを大きくし、コントラストの高い色を使用して、視認性を高めることを推奨します。",
                "difficulty": "簡単",
                "impact": "高",
                "category": "CTA改善"
            },
            {
                "title": "フォーム最適化",
                "description": "入力フォームの項目数を削減し、必須項目のみに絞ることで、ユーザーの入力ハードルを下げます。また、段階的なフォーム表示も検討してください。",
                "difficulty": "中",
                "impact": "中",
                "category": "フォーム最適化"
            },
            {
                "title": "信頼性の向上",
                "description": "お客様の声や実績、第三者評価などの信頼性要素を追加し、サービスの信頼性を高めることでコンバージョン率の向上が期待できます。",
                "difficulty": "中",
                "impact": "高",
                "category": "信頼性向上"
            },
            {
                "title": "視覚的階層の改善",
                "description": "重要な情報とCTAボタンが最も目立つよう、ページの視覚的階層を見直してください。適切な余白、フォントサイズ、色のコントラストを使用して情報の優先度を明確にします。",
                "difficulty": "中",
                "impact": "中",
                "category": "デザイン改善"
            },
            {
                "title": "モバイル表示の最適化",
                "description": "モバイル表示でのボタンサイズ、フォントサイズ、タップ領域を見直し、操作性を向上させてください。スマートフォンでの使いやすさはコンバージョン率に大きく影響します。",
                "difficulty": "中",
                "impact": "高",
                "category": "モバイル最適化"
            }
        ]

        try:
            # 弱みの情報をJSON文字列に変換
            weaknesses_json = json.dumps(combined_analysis["weaknesses"][:5], ensure_ascii=False)

            # カテゴリスコアをJSON文字列に変換
            category_scores_json = json.dumps(combined_analysis["category_scores"], ensure_ascii=False)

            # % 記法を使用してフォーマット問題を回避
            prompt = (
                "あなたはCVR最適化の専門家です。以下の分析結果に基づいて、具体的かつ実行可能な改善提案を作成してください。\n\n"
                "全体スコア: %s\n\n"
                "カテゴリ別スコア:\n%s\n\n"
                "特に改善が必要な領域:\n%s\n\n"
                "サイトの弱み:\n%s\n\n"
                "以下の形式でCVR向上のための具体的な改善提案を5つ提示してください:\n"
                "- 各提案には「タイトル」と「詳細説明」を含めてください\n"
                "- 実装の難易度（簡単/中/難）を記載してください\n"
                "- 期待されるCVR向上効果（低/中/高）を記載してください\n"
                "- 改善が関連するカテゴリも記載してください\n\n"
                "以下は回答の JSON 形式です：\n"
                "[\n"
                "  {\n"
                "    \"title\": \"改善提案のタイトル\",\n"
                "    \"description\": \"詳細な説明\",\n"
                "    \"difficulty\": \"簡単/中/難\",\n"
                "    \"impact\": \"低/中/高\",\n"
                "    \"category\": \"関連するカテゴリ\"\n"
                "  },\n"
                "  ...\n"
                "]"
            ) % (
                combined_analysis["overall_score"],
                category_scores_json,
                ", ".join(weak_areas),
                weaknesses_json
            )

            # API呼び出しを試みる
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "あなたはCVR最適化の専門家です。JSONフォーマットで回答してください。"},
                        {"role": "user", "content": prompt}
                    ]
                )

                # レスポンスの内容をデバッグ出力
                response_content = response.choices[0].message.content
                print(f"改善提案レスポンス（先頭部分）: {response_content[:100]}...")

                # JSONの抽出を試みる
                cleaned_content = response_content.strip()
                json_start = cleaned_content.find('[')
                json_end = cleaned_content.rfind(']') + 1

                if json_start >= 0 and json_end > json_start:
                    json_content = cleaned_content[json_start:json_end]
                    try:
                        result = json.loads(json_content)
                        if isinstance(result, list) and len(result) > 0:
                            print("改善提案JSONの解析成功")
                            return result
                    except json.JSONDecodeError as e:
                        print(f"改善提案JSON解析エラー: {str(e)}")

                print("改善提案JSONの抽出に失敗。デフォルト提案を使用します。")
            except Exception as e:
                print(f"改善提案API呼び出しエラー: {str(e)}")
                traceback.print_exc()

        except Exception as e:
            print(f"改善提案生成の全体エラー: {str(e)}")
            traceback.print_exc()

        # APIからの提案取得に失敗した場合はデフォルト提案を返す
        print("デフォルトの改善提案を返します")
        return default_improvements

# URL文字列からファイル名に適した文字列を生成する補助関数
def url_to_filename(url):
    """URLからファイル名として使える文字列を生成"""
    # httpやhttpsなどのプロトコル部分を除去
    url = url.replace("http://", "").replace("https://", "")
    # 特殊文字を置換
    url = url.replace("/", "_").replace(".", "-").replace(":", "_").replace("?", "_").replace("&", "_")
    return url
