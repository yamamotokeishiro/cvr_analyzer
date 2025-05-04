import os
import requests
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv
import time
import traceback
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import io
import base64

# 環境変数のロード
load_dotenv()

# OpenAI APIの設定
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("警告: OPENAI_API_KEYが設定されていません。GPT機能は動作しません。")
    api_key = "dummy_key_for_testing"

openai.api_key = api_key

def analyze_website(url):
    """
    ウェブサイトを分析する関数（OpenAI API 1.0.0以降に対応）
    """
    try:
        # ウェブサイトのコンテンツを取得
        website_data = get_website_content(url)

        # OpenAI APIのキーを取得
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # テスト用のデモ分析を返す
            return get_demo_analysis()

        # 改善版：より詳細な分析プロンプトを構築
        prompt = f"""
        # ウェブサイトのCVR導線分析

        以下のウェブサイトを分析し、CVR(コンバージョン率)を向上させるための具体的な問題点と改善案を提示してください。

        ## サイト情報
        URL: {url}
        タイトル: {website_data.get('title', '不明')}

        ## 分析すべき要素
        1. **ファーストビュー**: ユーザーが最初に見る領域は魅力的か、価値提案が明確か
        2. **CTAボタン**: デザイン、配置、テキストは効果的か
        3. **ユーザー導線**: コンバージョンまでの道筋が明確か
        4. **フォーム**: シンプルで使いやすいか
        5. **信頼性要素**: ユーザーの不安を取り除く要素があるか

        ## 分析結果の形式
        各要素について、以下の形式で回答してください：

        ### [要素名]
        **現状**: （現状の説明）
        **問題点**: （問題点の箇条書き）
        **改善案**: （改善案の箇条書き）

        ## 優先的改善点
        分析結果を踏まえて、最も効果が期待できる3つの改善点を優先度順に提示してください。
        """

        # 新しいOpenAI APIインターフェースを使用
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4",  # より高度なモデルを使用
            messages=[
                {"role": "system", "content": "あなたはCVR最適化の専門家です。ウェブサイトを分析し、具体的で実用的な改善提案を行います。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2500
        )

        # 分析結果を取得（新APIでの取得方法）
        analysis_result = response.choices[0].message.content

        return analysis_result

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"分析エラー: {str(e)}")
        print(error_details)
        return f"分析中にエラーが発生しました: {str(e)}"


def get_website_content(url):
    """
    URLからウェブサイトのコンテンツを取得する
    """
    import requests
    from bs4 import BeautifulSoup

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # ウェブサイトにリクエスト
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # エラーがあれば例外を発生

        # BeautifulSoupでHTMLをパース
        soup = BeautifulSoup(response.text, 'html.parser')

        # 基本情報の抽出
        title = soup.title.string if soup.title else "No title"

        # メタ説明の抽出
        meta_description = soup.find('meta', attrs={'name': 'description'})
        description = meta_description['content'] if meta_description and 'content' in meta_description.attrs else ""

        # HTMLの一部を抽出（分析用）
        html_sample = str(soup.prettify())[:5000]  # 最初の5000文字だけ

        # 基本的なデータを返す
        return {
            'title': title,
            'meta_description': description,
            'html': response.text,
            'html_sample': html_sample
        }

    except requests.exceptions.RequestException as e:
        print(f"ウェブサイト取得エラー: {str(e)}")
        return {
            'error': f"ウェブサイトへのアクセスエラー: {str(e)}",
            'title': 'エラー',
            'meta_description': '',
            'html_sample': ''
        }
    except Exception as e:
        print(f"コンテンツ処理エラー: {str(e)}")
        return {
            'error': f"ウェブサイトの処理エラー: {str(e)}",
            'title': 'エラー',
            'meta_description': '',
            'html_sample': ''
        }


def extract_main_content(soup):
    """HTMLから主要なコンテンツを抽出する関数"""
    main_content = ""

    # メインコンテンツ領域の特定
    main_element = soup.find('main') or soup.find(id='content') or soup.find(class_=lambda c: c and ('content' in str(c).lower() or 'main' in str(c).lower()))

    if main_element:
        # メインコンテンツから段落とヘッダーを抽出
        for elem in main_element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            try:
                main_content += elem.get_text() + "\n\n"
            except Exception as e:
                print(f"テキスト抽出エラー: {str(e)}")
    else:
        # メイン要素が見つからない場合はボディ全体から抽出
        for elem in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            try:
                main_content += elem.get_text() + "\n\n"
            except Exception as e:
                print(f"テキスト抽出エラー: {str(e)}")

    # コンテンツが長すぎる場合はトリミング
    if len(main_content) > 4000:
        main_content = main_content[:4000] + "...(省略)"

    return main_content

def identify_cta_elements(soup):
    """CTAボタンやフォームなどのコンバージョン要素を特定して分析"""
    cta_candidates = []

    # ボタン要素の検出
    buttons = soup.find_all('button')
    for button in buttons:
        try:
            text = button.get_text(strip=True)
            if is_cta_text(text):
                cta_candidates.append({
                    'type': 'button',
                    'text': text,
                    'position': 'unknown'
                })
        except Exception as e:
            print(f"ボタン解析エラー: {str(e)}")

    # リンクボタンの検出
    links = soup.find_all('a')
    for link in links:
        try:
            text = link.get_text(strip=True)
            if is_cta_text(text) or has_button_class(link):
                cta_candidates.append({
                    'type': 'link',
                    'text': text,
                    'href': link.get('href', ''),
                    'position': 'unknown'
                })
        except Exception as e:
            print(f"リンク解析エラー: {str(e)}")

    return cta_candidates[:10]  # 最大10個のCTA要素を返す

def is_cta_text(text):
    """テキストがCTAらしいかどうかを判定"""
    cta_keywords = [
        '申し込む', '登録', '購入', '無料体験', 'お問い合わせ', '資料請求',
        '今すぐ', 'いますぐ', '始める', 'はじめる', '試す', 'ダウンロード',
        '詳細を見る', 'もっと見る', '続きを読む', '予約'
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in cta_keywords)

def has_button_class(element):
    """要素がボタンらしいクラスを持っているかを判定"""
    button_classes = ['btn', 'button', 'cta']
    classes = element.get('class', [])
    if not classes:
        return False
    classes_str = ' '.join([str(c) for c in classes]).lower()
    return any(btn_class in classes_str for btn_class in button_classes)

def analyze_forms(soup):
    """フォーム要素を分析する関数"""
    forms_data = []

    # すべてのフォームを取得
    forms = soup.find_all('form')

    for idx, form in enumerate(forms):
        try:
            # フォームのアクション（送信先）
            action = form.get('action', '')
            method = form.get('method', 'get').lower()

            # 入力フィールドの数
            input_fields = form.find_all(['input', 'textarea', 'select'])
            field_count = len(input_fields)

            # 必須フィールドの数
            required_fields = len([field for field in input_fields if field.has_attr('required')])

            # 送信ボタンの分析
            submit_buttons = []

            # formタグ内のsubmitボタン
            submit_elements = form.find_all(['button', 'input'], type=['submit', 'button'])
            for button in submit_elements:
                button_text = ""
                if button.name == 'button':
                    button_text = button.get_text(strip=True)
                else:
                    button_text = button.get('value', '')

                if button_text:
                    submit_buttons.append({
                        'text': button_text
                    })

            forms_data.append({
                'form_id': idx + 1,
                'action': action,
                'method': method,
                'field_count': field_count,
                'required_fields': required_fields,
                'submit_buttons': submit_buttons
            })
        except Exception as e:
            print(f"フォーム解析エラー: {str(e)}")

    return forms_data

def take_screenshot(url):
    """
    ウェブサイトのスクリーンショットを撮影する
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    import os
    import time

    # スクリーンショット保存ディレクトリ
    screenshots_dir = os.path.join(os.path.dirname(__file__), 'static', 'screenshots')
    os.makedirs(screenshots_dir, exist_ok=True)

    # タイムスタンプ付きファイル名
    import hashlib
    from datetime import datetime
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"{url_hash}_{timestamp}.png"
    file_path = os.path.join(screenshots_dir, file_name)

    try:
        # Chrome設定
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1366,768")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        # Chromeドライバーの初期化
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # ページにアクセス
        driver.get(url)

        # ページが完全に読み込まれるまで待機
        time.sleep(3)

        # スクリーンショットを撮影
        driver.save_screenshot(file_path)

        driver.quit()

        return file_name
    except Exception as e:
        print(f"スクリーンショット撮影エラー: {str(e)}")
        return None




def analyze_image_features(image_path):
    """画像の基本的な特徴を分析する関数"""
    try:
        img = Image.open(image_path)
        width, height = img.size

        # 画像を小さなサイズに縮小して色分析を高速化
        small_img = img.resize((100, int(100 * height / width)))
        pixels = list(small_img.getdata())

        # 色分布の分析
        unique_colors = len(set(pixels))
        color_diversity = unique_colors / (small_img.width * small_img.height)

        # 明るさの分析
        if img.mode != 'RGB':
            img = img.convert('RGB')

        brightness_sum = 0
        for r, g, b in img.getdata():
            # 明るさの計算 (0.299*R + 0.587*G + 0.114*B)
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            brightness_sum += brightness

        avg_brightness = brightness_sum / (width * height) / 255.0

        # 結果をまとめる
        return {
            'width': width,
            'height': height,
            'aspect_ratio': width / height,
            'color_diversity': color_diversity,
            'brightness': avg_brightness,
            'is_mobile_friendly': width / height < 1
        }
    except Exception as e:
        print(f"画像分析エラー: {str(e)}")
        return {
            'width': 0,
            'height': 0,
            'aspect_ratio': 0,
            'color_diversity': 0,
            'brightness': 0,
            'is_mobile_friendly': False,
            'error': str(e)
        }

def analyze_with_gpt(website_data, url):
    """GPT-4を使用してコンテンツを分析する関数"""
    try:
        # プロンプトの生成
        prompt = create_optimized_prompt(website_data, url)

        # システムメッセージを強化
        system_message = """
        あなたはCVR（コンバージョン率）最適化の専門家です。
        Webサイトの分析と改善提案を行います。

        分析にあたっては以下の知識を活用してください:
        - ユーザー心理学とヒューリスティクス（社会的証明、希少性、権威性など）
        - 視覚的階層とF型/Z型の視線パターン
        - 効果的なCTAデザインとコピーライティング
        - フォーム最適化とマイクロコンバージョン
        - A/Bテストの標準的な成功事例

        具体的、実用的、かつ実装可能な改善案を提供してください。
        「〜すべきです」という抽象的な提案ではなく、「〜を〜に変更する」という具体的な提案をしてください。

        回答はマークダウン形式で、見出しと段落を適切に使用して構造化してください。
        """

        # GPT-4にプロンプトを送信
        response = openai.ChatCompletion.create(
            model="gpt-4",  # または "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=3000,
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )

        # 回答を取得
        analysis = response.choices[0].message['content']

        # レスポンスのフォーマットを整える
        formatted_analysis = format_analysis(analysis)

        return formatted_analysis

    except Exception as e:
        print(f"GPT分析中にエラーが発生しました: {str(e)}")
        print(traceback.format_exc())
        return get_demo_analysis()

def create_optimized_prompt(website_data, url):
    """視覚的情報を含めた最適化されたプロンプトを生成する関数"""
    # 基本情報
    site_info = website_data['site_info']

    # CTAに関する情報
    cta_text = "CTA要素の分析:\n"
    if website_data['cta_elements']:
        for idx, cta in enumerate(website_data['cta_elements']):
            cta_text += f"{idx+1}. タイプ: {cta['type']}, テキスト: '{cta['text']}'\n"
    else:
        cta_text += "明確なCTA要素が見つかりませんでした。\n"

    # フォームに関する情報
    form_text = "フォーム分析:\n"
    if website_data['forms_analysis']:
        for idx, form in enumerate(website_data['forms_analysis']):
            form_text += f"{idx+1}. フィールド数: {form['field_count']}, 必須項目数: {form['required_fields']}\n"

            # 送信ボタンのテキスト
            if 'submit_buttons' in form and form['submit_buttons']:
                button_texts = []
                for btn in form['submit_buttons']:
                    if isinstance(btn, dict) and 'text' in btn:
                        button_texts.append(btn['text'])
                if button_texts:
                    form_text += f"   送信ボタン: {', '.join(button_texts)}\n"
    else:
        form_text += "フォームが見つかりませんでした。\n"

    # スクリーンショットの視覚的分析情報
    visual_analysis = ""
    if 'screenshot_info' in website_data and website_data['screenshot_info']:
        screenshot_info = website_data['screenshot_info']

        # デスクトップバージョンの分析
        if 'desktop_features' in screenshot_info and screenshot_info['desktop_features']:
            desktop = screenshot_info['desktop_features']
            visual_analysis += "\nデスクトップバージョンの視覚的分析:\n"
            visual_analysis += f"- 解像度: {desktop['width']}x{desktop['height']}ピクセル\n"
            visual_analysis += f"- 明るさ: {desktop['brightness']:.2f}/1.0 (0=暗い, 1=明るい)\n"
            visual_analysis += f"- 色の多様性: {desktop['color_diversity']:.2f}/1.0\n"

            # 明るさに基づく評価
            if desktop['brightness'] < 0.4:
                visual_analysis += "- 全体的に暗めのデザインを採用しています。\n"
            elif desktop['brightness'] > 0.6:
                visual_analysis += "- 全体的に明るいデザインで、開放的な印象です。\n"
            else:
                visual_analysis += "- 明るさのバランスが取れたデザインです。\n"

        # モバイルバージョンの分析
        if 'mobile_features' in screenshot_info and screenshot_info['mobile_features']:
            mobile = screenshot_info['mobile_features']
            visual_analysis += "\nモバイルバージョンの視覚的分析:\n"
            visual_analysis += f"- 解像度: {mobile['width']}x{mobile['height']}ピクセル\n"
            visual_analysis += f"- 明るさ: {mobile['brightness']:.2f}/1.0 (0=暗い, 1=明るい)\n"
            visual_analysis += f"- 色の多様性: {mobile['color_diversity']:.2f}/1.0\n"

            # モバイルフレンドリー判定
            if mobile['is_mobile_friendly']:
                visual_analysis += "- モバイル最適化：適切にデザインされています\n"
            else:
                visual_analysis += "- モバイル最適化：改善の余地があります\n"

    # 最終的なプロンプトの構築
    prompt = f"""
    以下のWebサイトのCVR導線について、専門的かつ詳細に分析し、具体的な改善策を提案してください。

    URL: {url}

    サイト基本情報:
    - タイトル: {site_info['title']}
    - 説明: {site_info['description']}
    - リンク数: {site_info['num_links']}
    - ボタン数: {site_info['num_buttons']}
    - フォーム数: {site_info['num_forms']}
    - 画像数: {site_info['num_images']}
    - 読み込み時間: {site_info['load_time']:.2f}秒

    {cta_text}

    {form_text}

    {visual_analysis}

    Webサイトのコンテンツ（一部）:
    {website_data['main_content'][:1500]}...

    以下の観点から詳細に分析し、具体的な改善施策を提案してください:

    1. ファーストビュー分析
       - 初見のユーザーに対する印象
       - 価値提案の明確さ
       - 視覚的階層構造

    2. CTAボタン分析
       - ボタンの視認性、配置、サイズ
       - テキストの説得力
       - コントラストと目立ちやすさ

    3. ユーザー導線分析
       - ナビゲーションの直感性
       - ステップ数と複雑さ
       - スムーズなユーザーフロー

    4. フォーム分析
       - フィールド数と必須項目
       - 入力補助とガイダンス
       - エラー表示の分かりやすさ

    5. コンテンツ分析
       - 文章の読みやすさ
       - 信頼性を高める要素
       - スキャナビリティ

    6. モバイル対応
       - レスポンシブデザイン
       - タップターゲットサイズ
       - モバイル特有の課題

    回答は以下の形式で、データに基づいた具体的かつ実行可能な改善案を含めてください:

    # CVR導線分析レポート

    ## 1. ファーストビュー分析
    [具体的な問題点]

    [具体的な改善案]

    ## 2. CTAボタン分析
    [具体的な問題点]

    [具体的な改善案]

    ## 3. ユーザー導線分析
    [具体的な問題点]

    [具体的な改善案]

    ## 4. フォーム分析
    [具体的な問題点]

    [具体的な改善案]

    ## 5. コンテンツ分析
    [具体的な問題点]

    [具体的な改善案]

    ## 6. モバイル対応
    [具体的な問題点]

    [具体的な改善案]

    ## 優先施策
    1. [具体的施策1 - 期待効果と実装の難易度を含む]
    2. [具体的施策2 - 期待効果と実装の難易度を含む]
    3. [具体的施策3 - 期待効果と実装の難易度を含む]
    """

    return prompt

def get_demo_analysis():
    """デモの分析結果を返す関数"""
    return """
# CVR導線分析レポート（デモ版）

## 1. ファーストビュー分析
[具体的な問題点]
ファーストビューには明確な価値提案が見当たらず、ユーザーがサイトの目的を理解しにくい状態です。また、視覚的階層が不明確で、重要な情報への注目を集めにくくなっています。

[具体的な改善案]
ヒーローセクションに明確な価値提案を追加し、サイトの目的を一目で理解できるようにします。また、視覚的コントラストを強化して重要な要素に注目が集まるようにデザインを変更します。

## 2. CTAボタン分析
[具体的な問題点]
CTAボタンの視認性が低く、色のコントラストも弱いため、ユーザーの行動を促せていません。また、ボタンのテキストが具体的な行動を示していないケースが見られます。

[具体的な改善案]
CTAボタンの色を周囲とのコントラストが高い色に変更し、サイズも15%程度大きくします。また、ボタンテキストを「今すぐ相談する」「無料で資料をダウンロード」など、より具体的な行動を促す文言に変更します。

## 3. ユーザー導線分析
[具体的な問題点]
サイト内のナビゲーション構造が複雑で、ユーザーがコンバージョンに至るまでのステップが多すぎます。また、関連コンテンツへの誘導が不足しており、ユーザーの興味を維持できていません。

[具体的な改善案]
ナビゲーションメニューを整理し、主要なカテゴリに絞ります。コンバージョンまでのステップを3ステップ以内に削減し、各ページに関連コンテンツへのリンクを追加して回遊性を高めます。

## 4. フォーム分析
[具体的な問題点]
お問い合わせフォームの入力項目が多すぎるため、ユーザーの離脱率が高くなっています。また、入力時のガイダンスが不足しており、ユーザーが何を入力すべきか迷う場面があります。

[具体的な改善案]
フォームの入力項目を最低限（名前、メール、お問い合わせ内容）に削減します。各入力欄にプレースホルダーテキストを追加し、入力例を示すことでユーザーの迷いを軽減します。また、プライバシーポリシーの記載を目立たせて信頼性を向上させます。

## 5. コンテンツ分析
[具体的な問題点]
コンテンツが専門的すぎて一般ユーザーには理解しづらい部分があります。また、テキストのブロックが大きく、スキャンしにくい状態になっています。実績や顧客の声などの信頼性を高める要素も不足しています。

[具体的な改善案]
専門用語を減らし、より平易な表現に置き換えます。大きなテキストブロックは箇条書きや小見出しを使って分割し、スキャンしやすくします。顧客の声や実績を示すセクションを追加し、具体的な数字やケーススタディを用いて信頼性を向上させます。

## 優先施策
1. [CTAボタンの最適化] - コントラストの高い色への変更とテキストの具体化により、クリック率が30%程度向上すると予測されます。実装難易度は低く、即効性が高い施策です。

2. [フォーム項目の削減] - 必須項目を3つ程度に絞ることで、フォーム完了率が40-50%向上すると予測されます。実装難易度は中程度で、1-2日程度で対応可能です。

3. [ファーストビューの価値提案強化] - 明確な価値提案を追加することで、滞在時間が25%程度向上し、離脱率が15%程度低下すると予測されます。実装難易度は中程度で、デザイン変更を伴いますが、効果は非常に高いです。
    """

def format_analysis(text):
    """
    LLMからの分析結果を見やすく整形する関数
    """
    # 見出しの前に適切な空行を追加
    text = text.replace('\n# ', '\n\n# ')
    text = text.replace('\n## ', '\n\n## ')

    # [問題点]と[改善案]の間に空行を追加
    text = text.replace('[具体的な問題点]', '[具体的な問題点]\n')
    text = text.replace('[具体的な改善案]', '\n[具体的な改善案]\n')

    # 優先施策のリスト項目の前後に空行を追加
    text = text.replace('\n1. ', '\n\n1. ')
    text = text.replace('\n2. ', '\n\n2. ')
    text = text.replace('\n3. ', '\n\n3. ')

    return text