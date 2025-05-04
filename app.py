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

        print(f"分析リクエスト: {url}")

        # Webサイト分析の実行
        result = analyze_website(url)

        # 分析結果とスクリーンショット情報を取得
        analysis = result.get('analysis', '')
        screenshots = result.get('screenshots', None)

        # スクリーンショットのパスを変換（静的ファイル用）
        screenshot_paths = {}
        if screenshots:
            if 'desktop_path' in screenshots:
                # パスから静的ファイル参照用に変換
                desktop_path = screenshots['desktop_path'].replace('static/', '')
                screenshot_paths['desktop'] = desktop_path

            if 'mobile_path' in screenshots:
                # パスから静的ファイル参照用に変換
                mobile_path = screenshots['mobile_path'].replace('static/', '')
                screenshot_paths['mobile'] = mobile_path

        print("分析完了、結果をレンダリング")

        # 行の間に適切な空行を追加して読みやすくする
        analysis = analysis.replace('\n# ', '\n\n# ')
        analysis = analysis.replace('\n## ', '\n\n## ')

        # HTMLとして結果を返す
        return render_template('result.html',
                              url=url,
                              result=analysis,
                              screenshot_paths=screenshot_paths)
    except Exception as e:
        print(f"アプリケーションエラー: {str(e)}")
        import traceback
        print(traceback.format_exc())  # スタックトレースを出力
        return jsonify({'error': str(e)})



if __name__ == '__main__':
    app.run(debug=True)
