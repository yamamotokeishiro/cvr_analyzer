from flask import Flask, render_template, request, jsonify
from analyzer import analyze_website
import os
import traceback  # スタックトレース取得用

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
            return jsonify({'error': 'URLが入力されていません'})

        # Webサイト分析の実行
        raw_result = analyze_website(url)

        # 行の間に適切な空行を追加して読みやすくする
        result = raw_result.replace('\n# ', '\n\n# ')
        result = result.replace('\n## ', '\n\n## ')
        result = result.replace('[具体的な問題点]', '\n[具体的な問題点]\n')
        result = result.replace('[具体的な改善案]', '\n[具体的な改善案]\n')

        # HTMLとして結果を返す
        return render_template('result.html', url=url, result=result)
    except Exception as e:
        print(f"アプリケーションエラー: {str(e)}")
        return jsonify({'error': str(e)})



if __name__ == '__main__':
    app.run(debug=True)
