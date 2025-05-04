import os
import requests
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv
import time

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
    指定されたURLのWebサイトを分析する総合関数
    """
    try:
        # Webサイトの基本情報取得
        website_data = get_website_content(url)

        # AI分析の実行
        if api_key == "dummy_key_for_testing":
            analysis_result = get_demo_analysis()
        else:
            analysis_result = analyze_with_gpt(website_data, url)

        return analysis_result
    except Exception as e:
        print(f"エラー詳細: {type(e).__name__}, {str(e)}")
        return f"""
# CVR導線分析レポート（エラー発生）

## エラー情報
分析中にエラーが発生しました: {str(e)}

## 一般的なCVR改善ポイント
1. ファーストビューに明確な価値提案を置く
2. CTAボタンの視認性を高める
3. ユーザー導線を単純化する
4. フォームの入力項目を最小限にする
5. 信頼性を高める要素（実績、顧客の声）を追加する
        """

def get_website_content(url):
    """Webサイトのコンテンツと詳細情報を取得する関数"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # ウェブページのHTMLを取得
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        load_time = time.time() - start_time

        # BeautifulSoupでHTMLを解析
        soup = BeautifulSoup(response.content, 'html.parser')

        # 基本情報の抽出
        title = soup.title.string if soup.title else "タイトルなし"
        meta_description = soup.find('meta', attrs={'name': 'description'})
        description = meta_description['content'] if meta_description and meta_description.get('content') else "説明なし"

        # リンク、ボタン、フォームなどの重要要素をカウント
        links = len(soup.find_all('a'))
        buttons = len(soup.find_all('button'))
        forms = len(soup.find_all('form'))
        images = len(soup.find_all('img'))

        # HTML内の主要なテキストコンテンツを抽出
        main_content = extract_main_content(soup)

        # サイト情報の構造化
        site_info = {
            'title': title,
            'description': description,
            'num_links': links,
            'num_buttons': buttons,
            'num_forms': forms,
            'num_images': images,
            'load_time': load_time
        }

        # CTA要素の特定と分析
        cta_elements = identify_cta_elements(soup)

        # フォーム分析
        forms_analysis = analyze_forms(soup)

        # 総合データを返す
        return {
            'main_content': main_content,
            'site_info': site_info,
            'cta_elements': cta_elements,
            'forms_analysis': forms_analysis
        }

    except Exception as e:
        print(f"ウェブサイト取得エラー詳細: {type(e).__name__}, {str(e)}")
        raise Exception(f"ウェブサイトの取得中にエラーが発生しました: {str(e)}")

def extract_main_content(soup):
    """HTMLから主要なコンテンツを抽出する関数"""
    main_content = ""

    # メインコンテンツ領域の特定
    main_element = soup.find('main') or soup.find(id='content') or soup.find(class_=lambda c: c and ('content' in str(c).lower() or 'main' in str(c).lower()))

    if main_element:
        # メインコンテンツから段落とヘッダーを抽出
        for elem in main_element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            main_content += elem.get_text() + "\n\n"
    else:
        # メイン要素が見つからない場合はボディ全体から抽出
        for elem in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            main_content += elem.get_text() + "\n\n"

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
        text = button.get_text(strip=True)
        if is_cta_text(text):
            cta_candidates.append({
                'type': 'button',
                'text': text,
                'position': 'unknown'
            })

    # リンクボタンの検出
    links = soup.find_all('a')
    for link in links:
        text = link.get_text(strip=True)
        if is_cta_text(text) or has_button_class(link):
            cta_candidates.append({
                'type': 'link',
                'text': text,
                'href': link.get('href', ''),
                'position': 'unknown'
            })

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
        for button in form.find_all(['button', 'input'], attrs={'type': ['submit', 'button']}):
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

    return forms_data

def analyze_with_gpt(website_data, url):
    """GPT-4を使用してコンテンツを分析する関数"""
    try:
        # プロンプトの生成
        prompt = create_simple_prompt(website_data, url)

        # システムメッセージを強化
        system_message = """
        あなたはCVR（コンバージョン率）最適化の専門家です。
        Webサイトの分析と改善提案を行います。

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
        return get_demo_analysis()

def create_simple_prompt(website_data, url):
    """シンプルなプロンプトを生成する関数"""
    site_info = website_data['site_info']

    # CTA要素の数
    cta_count = len(website_data['cta_elements'])

    # フォームの数
    form_count = len(website_data['forms_analysis'])

    prompt = f"""
    以下のWebサイトのCVR導線について分析し、改善策を提案してください。

    URL: {url}

    サイト基本情報:
    - タイトル: {site_info['title']}
    - 説明: {site_info['description']}
    - リンク数: {site_info['num_links']}
    - ボタン数: {site_info['num_buttons']}
    - フォーム数: {site_info['num_forms']}
    - 画像数: {site_info['num_images']}
    - 読み込み時間: {site_info['load_time']:.2f}秒
    - 検出したCTA要素数: {cta_count}
    - 検出したフォーム数: {form_count}

    Webサイトのコンテンツ:
    {website_data['main_content'][:1500]}...

    以下の観点から分析し、具体的な改善案を提示してください:
    1. ファーストビュー分析
    2. CTAボタン分析
    3. ユーザー導線分析
    4. フォーム分析
    5. コンテンツ分析

    回答は以下の形式でお願いします:

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
