from flask import Flask, render_template, request, jsonify
import os
import json  # jsonモジュールのインポート
from datetime import datetime
import traceback  # デバッグ用

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

        # サンプルの分析結果（OpenAI APIを使わない）
        result = f"""
        # {url} の分析結果

        ## ファーストビュー
        **現状**: テスト分析です。
        **問題点**:
        - サンプルの問題点1
        - サンプルの問題点2

        **改善案**:
        - サンプルの改善案1
        - サンプルの改善案2

        ## 優先的改善点
        1. 第一優先: サンプルの優先事項1
        2. 第二優先: サンプルの優先事項2
        """

        # HTMLとして結果を返す
        return render_template('result.html', url=url, result=result)

    except Exception as e:
        print(f"アプリケーションエラー: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)})

@app.route('/contact', methods=['POST'])
def contact():
    try:
        # フォームデータの取得
        contact_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'analyzed_url': request.form.get('analyzed_url', 'No URL specified'),
            'company': request.form.get('company', ''),
            'name': request.form.get('name', ''),
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'message': request.form.get('message', ''),
            'interests': request.form.getlist('interests[]')  # チェックボックスの複数選択
        }

        # お問い合わせをファイルに保存
        contacts_dir = os.path.join(os.path.dirname(__file__), 'data', 'contacts')
        os.makedirs(contacts_dir, exist_ok=True)

        filename = f"{contact_data['timestamp'].replace(':', '-').replace(' ', '_')}.json"
        filepath = os.path.join(contacts_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(contact_data, f, ensure_ascii=False, indent=2)

        # サンクスページを表示
        return render_template('thanks.html', name=contact_data['name'])

    except Exception as e:
        print(f"お問い合わせ処理エラー: {str(e)}")
        print(traceback.format_exc())  # 詳細なエラー情報を出力
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
