import pandas as pd
import random
import os
import json
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import re
from supabase import create_client, Client
from dotenv import load_dotenv

# .envファイルを読み込む（ローカル開発用）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
CORS(app)

# --- Supabase Setup ---
supabase: Client = None
try:
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
        print("Supabase接続に成功しました。")
    else:
        print("警告: Supabase環境変数が設定されていません。")
except Exception as e:
    print(f"Supabase接続エラー: {e}")

# --- Helper Function ---
def clean_text_line(text):
    if not isinstance(text, str):
        return ""
    # ユーザー名や不要な記号を削除する簡易クリーニング
    cleaned = re.sub(r'^\s*([A-Za-z0-9_]+:|@\w+\s*:|\s*[-\*\d\.]+\s*)', '', text)
    return cleaned.strip().strip('「」')

# --- Main Simulator Class (Updated for Pre-generated CSVs) ---
class TimelineManager:
    def __init__(self):
        self.data_store = {
            'warmup': [],
            'weak': {'0-5': [], '5-10': [], '10-15': []},
            'mid': {'0-5': [], '5-10': [], '10-15': []},
            'strong': {'0-5': [], '5-10': [], '10-15': []}
        }
        self.load_all_data()

    def load_csv(self, filename, text_col='text'):
        path = os.path.join(BASE_DIR, filename) # ルート直下にあると想定
        if not os.path.exists(path):
            # Vercel環境などでは data/ フォルダにある場合も考慮
            path_in_data = os.path.join(BASE_DIR, 'data', filename)
            if os.path.exists(path_in_data):
                path = path_in_data
            else:
                print(f"Warning: File not found: {filename}")
                return []
        
        try:
            df = pd.read_csv(path)
            if text_col not in df.columns and 'Sentence' in df.columns:
                df.rename(columns={'Sentence': text_col}, inplace=True)
            
            if text_col in df.columns:
                df = df.dropna(subset=[text_col])
                return df[[text_col]].to_dict(orient='records')
            return []
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return []

    def load_all_data(self):
        # 1. Warmup (0%)
        self.data_store['warmup'] = self.load_csv('wrime-ver1_converted.csv', text_col='Sentence')

        # 2. Weak Condition
        self.data_store['weak']['0-5'] = self.load_csv('stress_timeline_weak_0-5min_p50.csv')
        self.data_store['weak']['5-10'] = self.load_csv('stress_timeline_weak_5-10min_p69_3.csv')
        self.data_store['weak']['10-15'] = self.load_csv('stress_timeline_weak_10-15min_p70.csv')

        # 3. Mid Condition
        self.data_store['mid']['0-5'] = self.load_csv('stress_timeline_mid_0-5min_p30.csv')
        self.data_store['mid']['5-10'] = self.load_csv('stress_timeline_mid_5-10min_p38.csv')
        self.data_store['mid']['10-15'] = self.load_csv('stress_timeline_mid_10-15min_p52_8.csv')

        # 4. Strong Condition
        self.data_store['strong']['0-5'] = self.load_csv('stress_timeline_strong_0-5min_p10.csv')
        self.data_store['strong']['5-10'] = self.load_csv('stress_timeline_strong_5-10min_p16_9.csv')
        self.data_store['strong']['10-15'] = self.load_csv('stress_timeline_strong_10-15min_p27_2.csv')

    def get_posts(self, condition, phase):
        # phase: 'warmup', '0-5', '5-10', '10-15'
        if phase == 'warmup':
            data = self.data_store['warmup']
            # ウォームアップはランダムに50件ほど抽出
            if data:
                return random.sample(data, min(len(data), 50))
            return []
        
        if condition in self.data_store and phase in self.data_store[condition]:
            return self.data_store[condition][phase]
        
        return []

# インスタンス化
manager = TimelineManager()

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    progress = {'weak': False, 'mid': False, 'strong': False}
    
    # Supabase から完了状況を取得
    if supabase:
        try:
            # experiment_logs テーブルから完了済みレコードを取得
            response = supabase.table('experiment_logs')\
                .select('filter_condition')\
                .eq('participant_name', user_id)\
                .eq('status', 'completed')\
                .execute()
            
            for record in response.data:
                cond = record.get('filter_condition')
                if cond in progress:
                    progress[cond] = True
        except Exception as e:
            print(f"Supabase query error: {e}")
            
    return jsonify({'status': 'ok', 'progress': progress})

@app.route('/api/timeline', methods=['GET'])
def get_timeline():
    condition = request.args.get('condition') # weak, mid, strong
    phase = request.args.get('phase')         # warmup, 0-5, 5-10, 10-15
    
    if not phase:
        return jsonify({'error': 'Phase required'}), 400

    posts = manager.get_posts(condition, phase)
    
    # フロントエンドの期待する形式に整形
    timeline = []
    for p in posts:
        timeline.append({
            'text': clean_text_line(p['text']),
            'source': condition, # 簡易的に条件を入れる
            'stress': 0 # 表示上の色分け用（今回はCSV側で制御済みと仮定し、一律0または適当な値でも可）
        })
    
    return jsonify({
        'success': True,
        'timeline': timeline
    })

@app.route('/api/complete', methods=['POST'])
def complete():
    data = request.json
    user_id = data.get('user_id')
    condition = data.get('condition')
    vas_score = data.get('vas_score')
    
    if not user_id or condition not in ['weak', 'mid', 'strong']:
        return jsonify({'error': 'Invalid data'}), 400
        
    if supabase:
        try:
            record = {
                'participant_name': user_id,
                'filter_condition': condition,
                'vas_score': vas_score,
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            }
            supabase.table('experiment_logs').insert(record).execute()
            return jsonify({'status': 'ok'})
        except Exception as e:
            print(f"Supabase insert error: {e}")
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Database not configured'}), 500

# Vercel用
if __name__ == '__main__':
    app.run(debug=True, port=5000)