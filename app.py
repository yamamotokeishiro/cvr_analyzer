from flask import Flask, render_template, request, jsonify
from analyzer import analyze_website, take_screenshot
import os
import traceback

app = Flask(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # URLの取得
        url = request.form.get('url')
        if not url:
            return jsonify({"error": "URLが入力されていません"})

        # URLのスキーム確認と修正
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # スクリーンショット撮影
        screenshot = take_screenshot(url)

        # ウェブサイト分析
        raw_result = analyze_website(url)

        # 分析結果の構造化
        parsed_sections, priorities = parse_analysis_result(raw_result)

        # HTMLとして結果を返す
        return render_template(
            'result.html',
            url=url,
            result=raw_result,  # 生の結果も保持
            parsed_results=parsed_sections,
            priorities=priorities,
            screenshot=screenshot
        )

    except Exception as e:
        print(f"アプリケーションエラー: {str(e)}")
        return jsonify({"error": str(e)})

def parse_analysis_result(markdown_text):
    """
    マークダウン形式の分析結果をパースして構造化データに変換
    """
    import re

    # セクションを格納する配列
    sections = []

    # 優先的改善点を格納する配列
    priorities = []

    # 現在処理中のセクション
    current_section = None

    # 優先的改善点セクションのフラグ
    in_priorities = False

    # 行ごとに処理
    lines = markdown_text.split('\n')
    for line in lines:
        # セクションヘッダー (### で始まる行)
        if line.startswith('### '):
            if current_section:
                sections.append(current_section)

            current_section = {
                'title': line.replace('### ', '').strip(),
                'status': '',
                'problems': [],
                'suggestions': []
            }
            in_priorities = False

        # 優先的改善点セクション
        elif line.startswith('## 優先的'):
            in_priorities = True
            if current_section:
                sections.append(current_section)
                current_section = None

        # 優先的改善点の項目
        elif in_priorities and re.match(r'^\d+\.\s', line):
            priorities.append(line.split('. ', 1)[1].strip())

        # 現在のセクション内の処理
        elif current_section:
            # 現状
            if '**現状**:' in line:
                current_section['status'] = line.split('**現状**:', 1)[1].strip()

            # 問題点
            elif '**問題点**:' in line:
                # 次の行以降が問題点の項目になる可能性がある
                continue

            # 改善案
            elif '**改善案**:' in line:
                # 次の行以降が改善案の項目になる可能性がある
                continue

            # 箇条書き項目（- で始まる行）
            elif line.strip().startswith('- '):
                item = line.strip().replace('- ', '').strip()

                # 直前の見出しによって振り分け
                if '**問題点**:' in '\n'.join(lines[max(0, lines.index(line)-5):lines.index(line)]):
                    current_section['problems'].append(item)
                elif '**改善案**:' in '\n'.join(lines[max(0, lines.index(line)-5):lines.index(line)]):
                    current_section['suggestions'].append(item)

    # 最後のセクションを追加
    if current_section:
        sections.append(current_section)

    return sections, priorities


if __name__ == '__main__':
    app.run(debug=True)
